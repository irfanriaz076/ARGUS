"""
NVD (National Vulnerability Database) API v2 client.
Docs: https://nvd.nist.gov/developers/vulnerabilities

Rate limits (no key): 5 requests / 30 s  → 1 request per 6 s to be safe.
Rate limits (with key): 50 requests / 30 s
"""

import time
from typing import Any, Dict, Optional

import httpx

from backend.config import settings

_NVD_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_DELAY_NO_KEY = 6.5   # seconds between requests without an API key
_DELAY_WITH_KEY = 0.7


def _request_delay() -> float:
    return _DELAY_WITH_KEY if settings.NVD_API_KEY else _DELAY_NO_KEY


def fetch_cve(cve_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single CVE from NVD and return a normalised dict:
    {
        cvss_score: float,
        cvss_vector: str,
        severity: str,
        description: str,
        references: [str],
        patch_urls: [str],
        published: str,
    }
    Returns None on any error.
    """
    headers = {}
    if settings.NVD_API_KEY:
        headers["apiKey"] = settings.NVD_API_KEY

    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(_NVD_BASE, params={"cveId": cve_id}, headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return None

    vulns = data.get("vulnerabilities", [])
    if not vulns:
        return None

    cve = vulns[0].get("cve", {})

    # Description (English preferred)
    desc = next(
        (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"),
        "",
    )

    # CVSS — prefer v3.1 → v3.0 → v2.0
    score, vector, severity = None, "", ""
    metrics = cve.get("metrics", {})
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key, [])
        primary = next((e for e in entries if e.get("type") == "Primary"), entries[0] if entries else None)
        if primary:
            cd = primary.get("cvssData", {})
            score    = cd.get("baseScore")
            vector   = cd.get("vectorString", "")
            severity = cd.get("baseSeverity", primary.get("baseSeverity", "")).upper()
            break

    # References
    refs = [r["url"] for r in cve.get("references", []) if r.get("url")]
    patches = [
        r["url"] for r in cve.get("references", [])
        if r.get("url") and any(t in r.get("tags", []) for t in ("Patch", "Fix"))
    ]

    return {
        "cvss_score":  float(score) if score else None,
        "cvss_vector": vector,
        "severity":    severity,
        "description": desc,
        "references":  refs[:8],
        "patch_urls":  patches[:4],
        "published":   cve.get("published", "")[:10],
    }


def fetch_cves_batch(cve_ids: list[str]) -> Dict[str, Optional[Dict]]:
    """
    Fetch multiple CVEs with rate-limited sequential calls.
    Returns {cve_id: enrichment_dict | None}
    """
    results: Dict[str, Optional[Dict]] = {}
    unique = list(dict.fromkeys(c.upper() for c in cve_ids if c))
    delay = _request_delay()

    for i, cid in enumerate(unique):
        results[cid] = fetch_cve(cid)
        if i < len(unique) - 1:
            time.sleep(delay)

    return results
