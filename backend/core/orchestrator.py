import ipaddress
import json
import asyncio
from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

import redis as sync_redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.config import settings
from backend.database.models import Engagement, Finding, Scan, Target
from backend.plugins.base_plugin import PluginRegistry


class KillChainOrchestrator:
    STAGES = ["recon", "enumeration", "vulnerability", "exploitation", "post_exploitation"]

    def __init__(self):
        self.registry = PluginRegistry()
        self.redis = sync_redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

    def broadcast(self, engagement_id: str, message: str, msg_type: str = "log"):
        self.redis.publish(
            f"engagement:{engagement_id}",
            json.dumps({"type": msg_type, "data": message, "timestamp": datetime.utcnow().isoformat()}),
        )

    async def run_engagement(self, engagement_id: str):
        await self._run_engagement_inner(engagement_id)

    async def _run_engagement_inner(self, engagement_id: str):
        """
        Each step below opens its own short-lived engine/session rather than
        sharing one across the whole engagement lifetime. A single long-lived
        session here was found to serve stale reads — it silently failed to
        see rows committed by other connections (the Celery scan tasks'
        sessions, and _expand_targets' own session), even well after those
        commits had landed. Every step here is independent anyway (each one
        only needs a fresh, correct view of the DB at the moment it runs), so
        short-lived sessions are both correct and consistent with how the
        rest of this codebase (scheduler.py) already talks to the DB.
        """
        engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=1, max_overflow=0)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with Session() as db:
                result = await db.execute(
                    select(Engagement).where(Engagement.id == UUID(engagement_id))
                )
                engagement = result.scalar_one_or_none()
                if not engagement:
                    return

                self.broadcast(engagement_id, f"[ARGUS] Starting engagement: {engagement.name}")

                # Seed initial targets from scope if none exist
                existing = await db.execute(
                    select(Target).where(Target.engagement_id == engagement.id)
                )
                if not existing.scalars().all():
                    for entry in (engagement.scope or []):
                        entry = entry.strip()
                        if not entry:
                            continue
                        t_type = "cidr" if "/" in entry else "ip" if self._is_ip(entry) else "domain"
                        db.add(Target(
                            engagement_id=engagement.id,
                            value=entry,
                            type=t_type,
                            added_by="scope",
                        ))
                    await db.commit()
                    self.broadcast(engagement_id, f"[ARGUS] Seeded {len(engagement.scope or [])} target(s) from scope")
        finally:
            await engine.dispose()

        for stage in self.STAGES:
            self.broadcast(engagement_id, f"[ARGUS] ─── Stage: {stage.upper()} ───")
            await self._run_stage(engagement_id, stage)

            if stage == "recon":
                await self._expand_targets(engagement_id)

        engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=1, max_overflow=0)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with Session() as db:
                result = await db.execute(
                    select(Engagement).where(Engagement.id == UUID(engagement_id))
                )
                engagement = result.scalar_one_or_none()
                if engagement:
                    engagement.status = "complete"
                    await db.commit()
        finally:
            await engine.dispose()

        self.broadcast(engagement_id, "[ARGUS] All stages complete — running CVE enrichment…")

        try:
            from backend.core.scheduler import run_enrichment_task
            run_enrichment_task.delay(engagement_id)
        except Exception as e:
            self.broadcast(engagement_id, f"[ARGUS] Enrichment skipped: {e}")

        self.broadcast(engagement_id, "[ARGUS] Engagement complete.", "complete")

    async def _run_stage(self, engagement_id: str, stage: str):
        engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=1, max_overflow=0)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with Session() as db:
                eng_result = await db.execute(
                    select(Engagement).where(Engagement.id == UUID(engagement_id))
                )
                engagement = eng_result.scalar_one_or_none()
                if not engagement:
                    return

                result = await db.execute(
                    select(Target).where(Target.engagement_id == engagement.id)
                )
                targets = result.scalars().all()

                plugins = self.registry.get_plugins_for_stage(stage)
                if not plugins:
                    self.broadcast(engagement_id, f"[ARGUS] No plugins registered for {stage}")
                    return

                tasks = []
                blocked = 0
                for target in targets:
                    # ── Scope hard-block ───────────────────────────────────
                    # url-type targets store the full URL (e.g. http://host:3000);
                    # scope entries are bare hostnames/IPs, so check against the
                    # parsed hostname for those, not the raw URL string.
                    scope_value = urlparse(target.value).hostname if target.type == "url" else target.value
                    scope_value = scope_value or target.value
                    if engagement.scope and not self._in_scope(scope_value, engagement.scope):
                        self.broadcast(
                            engagement_id,
                            f"[SCOPE BLOCK] {target.value} rejected — not in engagement scope",
                        )
                        blocked += 1
                        continue

                    for plugin in plugins:
                        if plugin.supports_target(target.type):
                            scan = Scan(
                                target_id=target.id,
                                engagement_id=engagement.id,
                                plugin_name=plugin.name,
                                stage=stage,
                                status="queued",
                            )
                            db.add(scan)
                            await db.flush()

                            from backend.core.scheduler import run_scan_task
                            task = run_scan_task.delay(
                                str(scan.id), plugin.name, target.value, engagement_id, target.type
                            )
                            tasks.append(task)

                await db.commit()
        finally:
            await engine.dispose()

        if blocked:
            self.broadcast(engagement_id, f"[ARGUS] {blocked} out-of-scope target(s) blocked")
        self.broadcast(engagement_id, f"[ARGUS] Queued {len(tasks)} task(s) for {stage}")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._wait_for_tasks, tasks)

    def _wait_for_tasks(self, tasks):
        """
        run_engagement_task is itself a Celery task, so calling .get() on the
        run_scan_task results it just queued trips Celery's "never call
        result.get() within a task" deadlock guard — it raised RuntimeError
        instantly for every single task, every time, which the old bare
        `except Exception: pass` silently swallowed. Net effect: this never
        actually waited for anything, so every "stage" fired concurrently
        instead of sequentially, and _expand_targets always ran against
        scans that had only just been queued, not completed.
        disable_sync_subtasks=False is Celery's documented escape hatch for
        exactly this pattern (a single orchestrator task blocking on its own
        subtasks); acceptable here since only one engagement's orchestrator
        task is expected to hold a worker slot at a time.
        """
        for task in tasks:
            try:
                task.get(timeout=600, disable_sync_subtasks=False)
            except Exception as e:
                print(f"[orchestrator] scan task {task.id} did not complete cleanly: {e}", flush=True)

    async def _expand_targets(self, engagement_id: str):
        """
        Runs on a brand-new engine/session rather than the long-lived one used
        for stage-queuing. The findings this reads were committed by completely
        separate Celery-task connections moments earlier — reusing the
        orchestrator's long-lived session here observed a stale snapshot that
        never saw those commits (0 rows visible despite the data existing),
        so this step gets its own short-lived connection, matching how every
        other cross-task DB access in this codebase already works (see
        scheduler.py's _make_engine() usage for graph updates/enrichment).
        """
        engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=1, max_overflow=0)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with Session() as db:
                result = await db.execute(select(Engagement).where(Engagement.id == UUID(engagement_id)))
                engagement = result.scalar_one_or_none()
                if not engagement:
                    return
                await self._expand_subdomains(db, engagement)
                await self._expand_live_services(db, engagement)
        finally:
            await engine.dispose()

    async def _expand_subdomains(self, db: AsyncSession, engagement: Engagement):
        result = await db.execute(
            select(Finding).where(
                Finding.engagement_id == engagement.id,
                Finding.title.like("Subdomain:%"),
            )
        )
        findings = result.scalars().all()

        new_count = 0
        for finding in findings:
            subdomain = finding.evidence.get("subdomain")
            if not subdomain:
                continue
            if not self._in_scope(subdomain, engagement.scope):
                continue

            existing = await db.execute(
                select(Target).where(
                    Target.engagement_id == engagement.id,
                    Target.value == subdomain,
                )
            )
            if existing.scalar_one_or_none():
                continue

            target = Target(
                engagement_id=engagement.id,
                value=subdomain,
                type="domain",
                added_by="orchestrator",
            )
            db.add(target)
            new_count += 1

        if new_count:
            await db.commit()
            self.broadcast(
                str(engagement.id),
                f"[ARGUS] Expanded attack surface: +{new_count} subdomain(s) added",
            )

    async def _expand_live_services(self, db: AsyncSession, engagement: Engagement):
        """
        httpx_probe discovers the *actual* scheme+port a target serves HTTP(S) on
        (e.g. juice-shop -> http://juice-shop:3000). Without this, every downstream
        HTTP-based plugin (ffuf, sqlmap, nikto, dalfox, header/CORS checks, etc.)
        only ever sees the bare domain/ip target and assumes port 80 — silently
        missing anything on a non-standard port. Promote each discovered live
        service to its own `url` target so those stages test the real endpoint.
        """
        result = await db.execute(
            select(Finding).where(
                Finding.engagement_id == engagement.id,
                Finding.title.like("Live Web Service:%"),
            )
        )
        findings = result.scalars().all()

        new_count = 0
        for finding in findings:
            url = (finding.evidence or {}).get("url")
            if not url:
                continue

            hostname = urlparse(url).hostname or ""
            if not self._in_scope(hostname, engagement.scope):
                continue

            existing = await db.execute(
                select(Target).where(
                    Target.engagement_id == engagement.id,
                    Target.value == url,
                )
            )
            if existing.scalar_one_or_none():
                continue

            target = Target(
                engagement_id=engagement.id,
                value=url,
                type="url",
                added_by="orchestrator",
            )
            db.add(target)
            new_count += 1

        if new_count:
            await db.commit()
            self.broadcast(
                str(engagement.id),
                f"[ARGUS] Expanded attack surface: +{new_count} live service URL(s) added",
            )

    def _is_ip(self, value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    def _in_scope(self, target: str, scope: list) -> bool:
        """
        Returns True if target is covered by any scope entry.
        Handles: exact match, *.wildcard domains, IP addresses, CIDR ranges.
        Empty scope = everything allowed.
        """
        if not scope:
            return True

        target = target.lower().strip()

        # Try to parse as IP address for CIDR checks
        target_ip = None
        try:
            target_ip = ipaddress.ip_address(target)
        except ValueError:
            pass

        for entry in scope:
            entry = entry.strip().lower()

            # Wildcard subdomain: *.example.com
            if entry.startswith("*."):
                parent = entry[2:]
                if target.endswith(f".{parent}") or target == parent:
                    return True

            # CIDR range: 10.0.0.0/8
            elif "/" in entry and target_ip is not None:
                try:
                    if target_ip in ipaddress.ip_network(entry, strict=False):
                        return True
                except ValueError:
                    pass

            # Exact match (domain or IP)
            elif target == entry:
                return True

        return False
