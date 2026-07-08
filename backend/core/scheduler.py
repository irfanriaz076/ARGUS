import asyncio
import json
from datetime import datetime

import redis as sync_redis
from celery import Celery

from backend.config import settings

celery_app = Celery(
    "argus",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="run_engagement_task", bind=True, max_retries=0)
def run_engagement_task(self, engagement_id: str):
    from backend.core.orchestrator import KillChainOrchestrator
    orchestrator = KillChainOrchestrator()
    asyncio.run(orchestrator.run_engagement(engagement_id))


@celery_app.task(name="run_enrichment_task", bind=True, max_retries=1)
def run_enrichment_task(self, engagement_id: str):
    asyncio.run(_execute_enrichment(engagement_id))


async def _execute_enrichment(engagement_id: str):
    from uuid import UUID
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from backend.services.enrichment import enrich_engagement

    # Fresh engine per task — avoids asyncpg fork-safety issues with prefork workers
    engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=1, max_overflow=0)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with Session() as db:
            summary = await enrich_engagement(UUID(engagement_id), db)
    finally:
        await engine.dispose()

    rc = sync_redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    rc.publish(
        f"engagement:{engagement_id}",
        json.dumps({
            "type": "log",
            "data": (
                f"[CVE ENGINE] {summary['version_matched']} version-matched · "
                f"{summary['enriched']} NVD-enriched · "
                f"{summary['epss_fetched']} EPSS scored · "
                f"{summary['poc_found']} PoC(s) found"
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }),
    )


@celery_app.task(name="run_scan_task", bind=True, max_retries=2)
def run_scan_task(
    self,
    scan_id: str,
    plugin_name: str,
    target: str,
    engagement_id: str,
    target_type: str,
):
    asyncio.run(_execute_scan(scan_id, plugin_name, target, engagement_id, target_type))


def _make_engine():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=1, max_overflow=0)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _execute_scan(
    scan_id: str,
    plugin_name: str,
    target: str,
    engagement_id: str,
    target_type: str,
):
    from uuid import UUID
    from sqlalchemy import select
    from backend.database.models import Engagement, Finding, Scan, Setting
    from backend.plugins.base_plugin import PluginRegistry

    redis_client = sync_redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    registry = PluginRegistry()
    plugin = registry.get(plugin_name)

    if not plugin:
        return

    engine, Session = _make_engine()
    try:
        # Load DB settings into os.environ so plugins pick them up
        async with Session() as db:
            sres = await db.execute(select(Setting))
            import os
            for s in sres.scalars().all():
                if s.value and not os.environ.get(s.key.upper()):
                    os.environ[s.key.upper()] = s.value

        async with Session() as db:
            result = await db.execute(select(Scan).where(Scan.id == UUID(scan_id)))
            scan = result.scalar_one_or_none()
            if not scan:
                return
            scan.status = "running"
            scan.started_at = datetime.utcnow()
            await db.commit()

        def publish(line: str):
            redis_client.publish(
                f"engagement:{engagement_id}",
                json.dumps({
                    "type": "output",
                    "plugin": plugin_name,
                    "target": target,
                    "data": line,
                    "timestamp": datetime.utcnow().isoformat(),
                }),
            )

        try:
            plugin_result = await plugin.run(target, target_type, publish)

            saved_findings = []
            async with Session() as db:
                result = await db.execute(select(Scan).where(Scan.id == UUID(scan_id)))
                scan = result.scalar_one_or_none()
                if scan:
                    scan.status = "complete"
                    scan.raw_output = plugin_result.raw_output
                    scan.completed_at = datetime.utcnow()
                    await db.commit()

                from backend.services import mitre
                for finding_data in plugin_result.findings:
                    mitre.annotate_dict(plugin_name, finding_data)
                    finding = Finding(
                        engagement_id=UUID(engagement_id),
                        target_id=scan.target_id,
                        scan_id=UUID(scan_id),
                        **finding_data,
                    )
                    db.add(finding)
                    saved_findings.append(finding_data)
                await db.commit()

            # Notifications for critical/high findings
            if saved_findings:
                try:
                    eng_name = engagement_id
                    async with Session() as db:
                        eres = await db.execute(
                            select(Engagement).where(Engagement.id == UUID(engagement_id))
                        )
                        eng = eres.scalar_one_or_none()
                        if eng:
                            eng_name = eng.name
                    from backend.services.notifier import notify_findings
                    await notify_findings(engagement_id, eng_name, saved_findings)
                except Exception as ne:
                    publish(f"[notify] skipped: {ne}")

            # Graph update — best-effort
            try:
                from backend.core.graph_builder import build_engagement_graph
                graph_engine, GraphSession = _make_engine()
                try:
                    async with GraphSession() as graph_db:
                        await build_engagement_graph(engagement_id, graph_db)
                finally:
                    await graph_engine.dispose()
            except Exception as graph_err:
                publish(f"[graph] update skipped: {graph_err}")

        except Exception as e:
            async with Session() as db:
                result = await db.execute(select(Scan).where(Scan.id == UUID(scan_id)))
                scan = result.scalar_one_or_none()
                if scan:
                    scan.status = "failed"
                    scan.raw_output = str(e)
                    scan.completed_at = datetime.utcnow()
                    await db.commit()
            publish(f"[ERROR] {plugin_name} failed: {e}")

    finally:
        await engine.dispose()
