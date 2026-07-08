"""
FIRST.org EPSS (Exploit Prediction Scoring System) client.
No API key required. Supports batch CVE lookup.
https://www.first.org/epss/api
"""
from typing import Dict, List, Optional
import httpx

_EPSS_BASE = "https://api.first.org/data/v1/epss"


def fetch_epss_batch(cve_ids: List[str]) -> Dict[str, Dict]:
    """
    Fetch EPSS scores for a list of CVE IDs.
    Returns {cve_id: {"score": float, "percentile": float, "date": str}}
    """
    if not cve_ids:
        return {}

    unique = list(dict.fromkeys(c.upper() for c in cve_ids if c))

    # API supports comma-separated CVEs
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(_EPSS_BASE, params={"cve": ",".join(unique)})
            r.raise_for_status()
            data = r.json()
    except Exception:
        return {}

    results: Dict[str, Dict] = {}
    for entry in data.get("data", []):
        cve = entry.get("cve", "").upper()
        try:
            results[cve] = {
                "score":      round(float(entry["epss"]), 4),
                "percentile": round(float(entry["percentile"]), 4),
                "date":       entry.get("date", ""),
            }
        except (KeyError, ValueError):
            continue

    return results
