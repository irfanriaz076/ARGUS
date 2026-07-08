from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas import (
    EngagementCreate, EngagementResponse, EngagementUpdate, RunEngagementRequest,
)
from backend.database.models import Engagement, Finding, Scan, Target
from backend.database.postgres import get_db

router = APIRouter(prefix="/api/engagements", tags=["engagements"])


@router.get("", response_model=List[EngagementResponse])
async def list_engagements(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Engagement).order_by(Engagement.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=EngagementResponse, status_code=status.HTTP_201_CREATED)
async def create_engagement(payload: EngagementCreate, db: AsyncSession = Depends(get_db)):
    engagement = Engagement(**payload.model_dump())
    db.add(engagement)
    await db.commit()
    await db.refresh(engagement)
    return engagement


@router.get("/{engagement_id}", response_model=EngagementResponse)
async def get_engagement(engagement_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return engagement


@router.patch("/{engagement_id}", response_model=EngagementResponse)
async def update_engagement(
    engagement_id: UUID,
    payload: EngagementUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(engagement, field, value)

    await db.commit()
    await db.refresh(engagement)
    return engagement


@router.delete("/{engagement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_engagement(engagement_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    await db.delete(engagement)
    await db.commit()


@router.get("/{engagement_id}/kill-chain")
async def get_kill_chain(engagement_id: UUID, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    scans_q = await db.execute(
        select(Scan).where(Scan.engagement_id == engagement_id).order_by(Scan.started_at)
    )
    scans = scans_q.scalars().all()

    findings_q = await db.execute(
        select(Finding).where(Finding.engagement_id == engagement_id)
    )
    findings = findings_q.scalars().all()

    targets_q = await db.execute(
        select(Target).where(Target.engagement_id == engagement_id)
    )
    targets = targets_q.scalars().all()

    findings_by_scan: Dict[str, list] = {}
    for f in findings:
        key = str(f.scan_id) if f.scan_id else "__none__"
        findings_by_scan.setdefault(key, []).append(f)

    STAGE_ORDER = ["recon", "enumeration", "vulnerability", "exploitation", "post_exploitation"]
    STAGE_LABEL = {
        "recon":            "RECON",
        "enumeration":      "ENUM",
        "vulnerability":    "VULN",
        "exploitation":     "EXPLOIT",
        "post_exploitation":"POST-EXPLOIT",
    }

    stages = []
    prev_discoveries = None

    for stage_id in STAGE_ORDER:
        stage_scans = [s for s in scans if s.stage == stage_id]

        tools = []
        for scan in stage_scans:
            scan_findings = findings_by_scan.get(str(scan.id), [])
            duration = None
            if scan.started_at and scan.completed_at:
                duration = round((scan.completed_at - scan.started_at).total_seconds(), 1)

            tools.append({
                "scan_id": str(scan.id),
                "name": scan.plugin_name,
                "status": scan.status,
                "started_at": scan.started_at.isoformat() if scan.started_at else None,
                "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
                "duration_s": duration,
                "finding_count": len(scan_findings),
                "findings": [
                    {"id": str(f.id), "title": f.title, "severity": f.severity}
                    for f in sorted(scan_findings,
                        key=lambda x: {"critical":0,"high":1,"medium":2,"low":3,"info":4}.get(x.severity,5))[:8]
                ],
            })

        stage_finding_ids = {str(f.id) for s in stage_scans
                             for f in findings_by_scan.get(str(s.id), [])}
        stage_findings = [f for f in findings if str(f.id) in stage_finding_ids]

        if not stage_scans:
            stage_status = "idle"
        elif all(s.status == "complete" for s in stage_scans):
            stage_status = "done"
        elif any(s.status in ("running", "queued") for s in stage_scans):
            stage_status = "active"
        elif any(s.status == "failed" for s in stage_scans):
            stage_status = "failed"
        else:
            stage_status = "idle"

        # Compute what this stage discovered to feed the next
        discoveries = []
        if stage_id == "recon":
            subs    = [f for f in stage_findings if f.title.startswith("Subdomain:")]
            live    = [f for f in stage_findings if f.title.startswith("Live Web")]
            certs   = [f for f in stage_findings if f.evidence and f.evidence.get("source") == "crtsh"]
            shodan  = [f for f in stage_findings if f.evidence and f.evidence.get("source") == "shodan"]
            github  = [f for f in stage_findings if f.evidence and f.evidence.get("source") == "github_dorking"]
            whois_f = [f for f in stage_findings if f.evidence and f.evidence.get("source") == "whois"]
            if subs:    discoveries.append(f"{len(subs)} subdomain(s) discovered")
            if certs:   discoveries.append(f"{len(certs)} cert transparency hit(s)")
            if live:    discoveries.append(f"{len(live)} live service(s) probed")
            if shodan:  discoveries.append(f"{len(shodan)} Shodan host(s) profiled")
            if github:  discoveries.append(f"{len(github)} GitHub exposure(s) found")
            if whois_f: discoveries.append(f"{len(whois_f)} WHOIS/ASN record(s)")
            auto_targets = [t for t in targets if t.added_by in ("orchestrator", "scope")]
            if auto_targets: discoveries.append(f"{len(auto_targets)} target(s) seeded")
        elif stage_id == "enumeration":
            ports = [f for f in stage_findings if f.title.startswith("Open Port")]
            paths = [f for f in stage_findings if "path" in f.title.lower() or "directory" in f.title.lower()]
            nse   = [f for f in stage_findings if "NSE" in f.title]
            if ports: discoveries.append(f"{len(ports)} open port(s) mapped")
            if nse:   discoveries.append(f"{len(nse)} service banner(s) captured")
            if paths: discoveries.append(f"{len(paths)} hidden path(s) found")
        elif stage_id == "vulnerability":
            cves  = [f for f in stage_findings if f.cve_id]
            crits = [f for f in stage_findings if f.severity == "critical"]
            highs = [f for f in stage_findings if f.severity == "high"]
            if cves:  discoveries.append(f"{len(cves)} CVE(s) identified")
            if crits: discoveries.append(f"{len(crits)} critical finding(s)")
            if highs: discoveries.append(f"{len(highs)} high finding(s)")
        elif stage_id == "exploitation":
            sqli  = [f for f in stage_findings if "SQL Injection" in f.title or "sqlmap" in str(f.evidence)]
            git_e = [f for f in stage_findings if ".git" in f.title or "git_exposure" in str(f.evidence)]
            nikto = [f for f in stage_findings if "Nikto:" in f.title]
            crits = [f for f in stage_findings if f.severity == "critical"]
            if sqli:  discoveries.append(f"{len(sqli)} SQL injection(s) exploited")
            if git_e: discoveries.append(f"{len(git_e)} source code exposure(s)")
            if nikto: discoveries.append(f"{len(nikto)} web misconfiguration(s)")
            if crits: discoveries.append(f"{len(crits)} critical finding(s) proven")
        elif stage_id == "post_exploitation":
            tls_f   = [f for f in stage_findings if f.evidence and f.evidence.get("source") == "testssl"]
            cred_f  = [f for f in stage_findings if f.evidence and f.evidence.get("source") == "hydra"]
            file_f  = [f for f in stage_findings if f.evidence and f.evidence.get("source") == "sensitive_files"]
            head_f  = [f for f in stage_findings if f.evidence and f.evidence.get("source") == "header_analyzer"]
            cors_f  = [f for f in stage_findings if f.evidence and f.evidence.get("source") == "cors_tester"]
            crits   = [f for f in stage_findings if f.severity == "critical"]
            if tls_f:  discoveries.append(f"{len(tls_f)} TLS vulnerability(ies)")
            if cred_f: discoveries.append(f"{len(cred_f)} valid credential(s)")
            if file_f: discoveries.append(f"{len(file_f)} sensitive file(s) exposed")
            if head_f: discoveries.append(f"{len(head_f)} header misconfiguration(s)")
            if cors_f: discoveries.append(f"{len(cors_f)} CORS misconfiguration(s)")
            if crits:  discoveries.append(f"{len(crits)} critical post-exploit finding(s)")

        stages.append({
            "id": stage_id,
            "label": STAGE_LABEL[stage_id],
            "status": stage_status,
            "tools": tools,
            "finding_count": len(stage_findings),
            "discoveries": discoveries,
            "fed_from": prev_discoveries,
        })
        prev_discoveries = discoveries if discoveries else None

    sev_counts = {}
    for f in findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

    return {
        "stages": stages,
        "total_findings": len(findings),
        "total_targets": len(targets),
        "severity_counts": sev_counts,
    }


@router.post("/{engagement_id}/start")
async def start_engagement(
    engagement_id: UUID,
    payload: Optional[RunEngagementRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.status == "running":
        raise HTTPException(status_code=400, detail="Engagement already running")

    from backend.core.scheduler import run_engagement_task
    run_engagement_task.delay(str(engagement_id))

    engagement.status = "running"
    await db.commit()
    return {"message": "Engagement started", "engagement_id": str(engagement_id)}


@router.post("/{engagement_id}/rerun")
async def rerun_engagement(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Re-runs the full kill chain against this engagement's existing targets.
    Clears prior scans/findings first for a clean re-test — otherwise every
    rerun would just pile duplicate scan rows and findings on top of the last
    run's, inflating counts for anything that's unchanged between runs.
    Targets (original + any auto-discovered) are kept, so recon starts from
    the same attack surface already mapped.
    """
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    engagement = result.scalar_one_or_none()
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found")
    if engagement.status == "running":
        raise HTTPException(status_code=400, detail="Engagement already running")

    await db.execute(delete(Finding).where(Finding.engagement_id == engagement_id))
    await db.execute(delete(Scan).where(Scan.engagement_id == engagement_id))
    await db.commit()

    from backend.core.scheduler import run_engagement_task
    run_engagement_task.delay(str(engagement_id))

    engagement.status = "running"
    await db.commit()
    return {"message": "Engagement rerun started", "engagement_id": str(engagement_id)}
