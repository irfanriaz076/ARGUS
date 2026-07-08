"""
Phase 1 CVE Proof Engine.

Steps (all run after engagement completes):
  1. Version-to-CVE matching  — nmap port findings → new CVE findings
  2. NVD enrichment           — fetch full NVD data for all CVE findings
  3. EPSS scoring             — exploit probability for all CVE findings
  4. PoC discovery            — GitHub + ExploitDB PoC links per CVE
"""
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select

from backend.database.models import Finding, Scan, Target
from backend.services.nvd_client import fetch_cves_batch
from backend.services.epss_client import fetch_epss_batch
from backend.services.poc_finder import find_pocs_batch
from backend.services.version_cve_matcher import match_findings_to_cves


async def enrich_engagement(engagement_id: str | UUID, db) -> Dict[str, Any]:
    eid = UUID(str(engagement_id))

    # ── Step 1: Version-to-CVE matching ──────────────────────────────────
    port_findings_q = await db.execute(
        select(Finding).where(
            Finding.engagement_id == eid,
            Finding.title.like("Open Port%"),
        )
    )
    port_findings: List[Finding] = port_findings_q.scalars().all()

    existing_cves_q = await db.execute(
        select(Finding.cve_id).where(
            Finding.engagement_id == eid,
            Finding.cve_id.isnot(None),
        )
    )
    existing_cve_ids = {row[0] for row in existing_cves_q.all() if row[0]}

    new_cve_findings = match_findings_to_cves(port_findings, existing_cve_ids)

    # Attach new CVE findings to the same target as their parent port finding
    target_map = {str(f.id): f.target_id for f in port_findings}
    for nf in new_cve_findings:
        parent_ip = nf["evidence"].get("ip")
        target_id = next(
            (f.target_id for f in port_findings if (f.evidence or {}).get("ip") == parent_ip),
            port_findings[0].target_id if port_findings else None,
        )
        if not target_id:
            continue
        finding = Finding(
            engagement_id=eid,
            target_id=target_id,
            **nf,
        )
        db.add(finding)

    if new_cve_findings:
        await db.commit()

    # ── Step 2: NVD enrichment ─────────────────────────────────────────────
    all_findings_q = await db.execute(
        select(Finding).where(
            Finding.engagement_id == eid,
            Finding.cve_id.isnot(None),
        )
    )
    cve_findings: List[Finding] = all_findings_q.scalars().all()

    cve_ids = list({f.cve_id for f in cve_findings if f.cve_id})
    nvd_data = fetch_cves_batch(cve_ids)

    enriched = failed = 0
    for finding in cve_findings:
        nvd = nvd_data.get((finding.cve_id or "").upper())
        if not nvd:
            failed += 1
            continue
        if nvd.get("cvss_score") is not None:
            finding.cvss_score = nvd["cvss_score"]
        ev = dict(finding.evidence or {})
        ev["nvd"] = {
            "cvss_score":  nvd.get("cvss_score"),
            "cvss_vector": nvd.get("cvss_vector", ""),
            "severity":    nvd.get("severity", ""),
            "description": nvd.get("description", ""),
            "references":  nvd.get("references", []),
            "patch_urls":  nvd.get("patch_urls", []),
            "published":   nvd.get("published", ""),
        }
        finding.evidence = ev
        enriched += 1

    await db.commit()

    # ── Step 3: EPSS scores ────────────────────────────────────────────────
    epss_data = fetch_epss_batch(cve_ids)
    for finding in cve_findings:
        epss = epss_data.get((finding.cve_id or "").upper())
        if epss:
            ev = dict(finding.evidence or {})
            ev["epss"] = epss
            finding.evidence = ev

    await db.commit()

    # ── Step 4: PoC discovery ──────────────────────────────────────────────
    cve_refs_map: Dict[str, List[str]] = {}
    for finding in cve_findings:
        cid = finding.cve_id
        if cid:
            refs = (finding.evidence or {}).get("nvd", {}).get("references", [])
            cve_refs_map[cid] = refs

    if cve_refs_map:
        poc_data = find_pocs_batch(cve_refs_map)
        for finding in cve_findings:
            pocs = poc_data.get(finding.cve_id or "", [])
            if pocs:
                ev = dict(finding.evidence or {})
                ev["poc"] = pocs
                finding.evidence = ev

    await db.commit()

    # ── Step 5: MITRE ATT&CK tagging (all findings) ────────────────────────
    from backend.services import mitre

    scans_q = await db.execute(select(Scan).where(Scan.engagement_id == eid))
    scan_plugin = {str(s.id): s.plugin_name for s in scans_q.scalars().all()}

    all_findings_q = await db.execute(select(Finding).where(Finding.engagement_id == eid))
    tagged = 0
    for f in all_findings_q.scalars().all():
        plugin = scan_plugin.get(str(f.scan_id))
        if mitre.annotate_orm(f, plugin):
            tagged += 1
    await db.commit()

    return {
        "version_matched": len(new_cve_findings),
        "enriched":        enriched,
        "failed":          failed,
        "epss_fetched":    len(epss_data),
        "poc_found":       sum(1 for f in cve_findings if (f.evidence or {}).get("poc")),
        "mitre_tagged":    tagged,
    }
