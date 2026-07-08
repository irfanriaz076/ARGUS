"""
Post-scan intelligence layer.
- Deduplicates findings across plugins for the same engagement
- Computes a 0-100 risk score for the engagement
- Returns structured attack-path summaries
"""

from typing import Any, Dict, List, Tuple
from uuid import UUID

from sqlalchemy import select

from backend.database.models import Finding, Scan, Target

SEV_WEIGHT = {"critical": 10, "high": 5, "medium": 2, "low": 1, "info": 0}
SEV_CAP    = {"critical": 40, "high": 25, "medium": 20, "low": 10, "info": 0}


def compute_risk_score(findings: List[Finding]) -> int:
    """
    Weighted severity sum, capped per bucket, normalised to 0-100.
    Max theoretical raw score: 40+25+20+10 = 95 → maps to ~100.
    """
    buckets: Dict[str, int] = {}
    for f in findings:
        w = SEV_WEIGHT.get(f.severity, 0)
        buckets[f.severity] = buckets.get(f.severity, 0) + w

    raw = sum(min(v, SEV_CAP.get(sev, 0)) for sev, v in buckets.items())
    return min(100, int(raw * 100 / 95))


def deduplicate(findings: List[Finding]) -> Tuple[List[Finding], int]:
    """
    Returns (unique_findings, duplicate_count).
    Two findings are duplicates when they share the same title and target_id.
    """
    seen: set = set()
    unique: List[Finding] = []
    dupes = 0
    for f in findings:
        key = (f.title.lower().strip(), str(f.target_id))
        if key in seen:
            dupes += 1
        else:
            seen.add(key)
            unique.append(f)
    return unique, dupes


async def run_correlator(engagement_id: str | UUID, db) -> Dict[str, Any]:
    """
    Run correlation pass on all findings for an engagement.
    Returns a summary dict with risk_score, finding stats, and top attack paths.
    """
    eid = engagement_id

    findings_res = await db.execute(
        select(Finding).where(Finding.engagement_id == eid)
    )
    findings: List[Finding] = findings_res.scalars().all()

    targets_res = await db.execute(
        select(Target).where(Target.engagement_id == eid)
    )
    targets: List[Target] = targets_res.scalars().all()
    target_map = {str(t.id): t.value for t in targets}

    unique_findings, dupes = deduplicate(findings)
    risk = compute_risk_score(unique_findings)

    sev_counts: Dict[str, int] = {}
    for f in unique_findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

    # Build top attack paths: targets with critical/high findings
    target_vuln: Dict[str, List[str]] = {}
    for f in unique_findings:
        if f.severity in ("critical", "high"):
            tid = str(f.target_id)
            tval = target_map.get(tid, "unknown")
            target_vuln.setdefault(tval, []).append(f.title)

    attack_paths = [
        {"target": tgt, "high_value_findings": findings[:5]}
        for tgt, findings in sorted(
            target_vuln.items(), key=lambda x: len(x[1]), reverse=True
        )[:5]
    ]

    return {
        "risk_score":     risk,
        "total_findings": len(findings),
        "unique_findings":len(unique_findings),
        "duplicates":     dupes,
        "severity_counts": sev_counts,
        "attack_paths":   attack_paths,
        "target_count":   len(targets),
    }
