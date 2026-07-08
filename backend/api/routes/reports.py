from collections import Counter
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.correlator import run_correlator
from backend.core.graph_builder import build_engagement_graph
from backend.database.models import Engagement, Finding, Target
from backend.database.neo4j_db import get_driver
from backend.database.postgres import get_db
from backend.services import narrator
from backend.services.attack_path import compute_attack_paths

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/narrative/status")
async def narrative_status():
    """Report whether the LLM narrative feature is configured."""
    return {"configured": narrator.is_configured(), "model": narrator.settings.LLM_MODEL}


@router.post("/{engagement_id}/narrative")
async def generate_narrative(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate an LLM attack-narrative from the engagement's findings + graph."""
    if not narrator.is_configured():
        raise HTTPException(
            status_code=400,
            detail="LLM not configured. Set LLM_API_KEY in .env (see .env.example).",
        )

    eng_res = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = eng_res.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    findings_res = await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id)
    )
    findings = list(findings_res.scalars().all())
    if not findings:
        raise HTTPException(status_code=400, detail="No findings yet — run a scan first.")

    correlation = await run_correlator(engagement_id, db)

    # Attack paths + graph summary from Neo4j (best-effort — narrative still works without).
    attack_paths = {"paths": []}
    graph_summary = {}
    try:
        await build_engagement_graph(engagement_id, db)
        driver = get_driver()
        from backend.api.routes.graph import _collect_nodes_links
        async with driver.session() as session:
            nodes, links = await _collect_nodes_links(session, str(engagement_id))
        attack_paths = compute_attack_paths(nodes, links)
        graph_summary = dict(Counter(n["type"] for n in nodes))
    except Exception:
        pass  # graph is optional context

    context = narrator.build_context(
        engagement, findings, correlation, attack_paths, graph_summary
    )
    try:
        report = await narrator.generate_narrative(context)
    except narrator.NarratorError as e:
        raise HTTPException(status_code=502, detail=str(e))

    report["risk_score"] = correlation.get("risk_score")
    report["attack_paths"] = attack_paths.get("paths", [])
    return report


@router.get("/{engagement_id}/pdf")
async def download_pdf(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    # Fetch all data
    eng_res = await db.execute(
        select(Engagement).where(Engagement.id == engagement_id)
    )
    engagement = eng_res.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    findings_res = await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id)
    )
    findings = findings_res.scalars().all()

    targets_res = await db.execute(
        select(Target).where(Target.engagement_id == engagement_id)
    )
    targets = targets_res.scalars().all()

    # Attack paths (local, cheap) — best-effort.
    attack_paths: list = []
    nodes: list = []
    try:
        await build_engagement_graph(engagement_id, db)
        driver = get_driver()
        from backend.api.routes.graph import _collect_nodes_links
        async with driver.session() as session:
            nodes, links = await _collect_nodes_links(session, str(engagement_id))
        attack_paths = compute_attack_paths(nodes, links).get("paths", [])
    except Exception:
        pass

    # AI narrative — only if an LLM key is configured; best-effort, omitted on failure.
    narrative = None
    if narrator.is_configured() and findings:
        try:
            correlation = await run_correlator(engagement_id, db)
            graph_summary = dict(Counter(n["type"] for n in nodes)) if nodes else {}
            context = narrator.build_context(
                engagement, list(findings), correlation,
                {"paths": attack_paths}, graph_summary,
            )
            narrative = await narrator.generate_narrative(context)
        except Exception:
            narrative = None

    from backend.services.pdf_reporter import generate_pdf
    try:
        pdf_bytes = generate_pdf(
            engagement, list(findings), list(targets),
            attack_paths=attack_paths, narrative=narrative,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    safe_name = engagement.name.replace(" ", "_").replace("/", "-")[:40]
    filename = f"ARGUS_{safe_name}_{str(engagement_id)[:8]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
