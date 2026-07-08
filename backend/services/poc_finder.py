"""
PoC (Proof-of-Concept) reference finder.
Sources: GitHub search API, ExploitDB via NVD references.
"""
from typing import Dict, List
import httpx

_GITHUB_SEARCH = "https://api.github.com/search/repositories"


def _github_pocs(cve_id: str) -> List[Dict]:
    """Search GitHub for PoC repos for a CVE."""
    try:
        with httpx.Client(timeout=10, headers={"Accept": "application/vnd.github+json"}) as client:
            r = client.get(_GITHUB_SEARCH, params={
                "q": f"{cve_id} poc exploit",
                "sort": "stars",
                "order": "desc",
                "per_page": 3,
            })
            if r.status_code != 200:
                return []
            items = r.json().get("items", [])
    except Exception:
        return []

    return [
        {
            "source":      "github",
            "url":         item["html_url"],
            "name":        item["full_name"],
            "description": (item.get("description") or "")[:120],
            "stars":       item.get("stargazers_count", 0),
        }
        for item in items
        if not item.get("private", True)
    ]


def _exploitdb_refs(nvd_references: List[str]) -> List[Dict]:
    """Extract ExploitDB links already present in NVD references."""
    return [
        {
            "source": "exploit-db",
            "url":    url,
            "name":   "ExploitDB Entry",
            "stars":  0,
        }
        for url in nvd_references
        if "exploit-db.com" in url or "exploitdb.com" in url
    ]


def find_pocs(cve_id: str, nvd_references: List[str] | None = None) -> List[Dict]:
    """
    Find PoC references for a CVE.
    Returns list of {source, url, name, description, stars}.
    """
    pocs: List[Dict] = []

    # ExploitDB links from NVD (no extra request needed)
    if nvd_references:
        pocs.extend(_exploitdb_refs(nvd_references))

    # GitHub search
    pocs.extend(_github_pocs(cve_id))

    # Deduplicate by URL
    seen = set()
    unique = []
    for p in pocs:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)

    return unique[:5]


def find_pocs_batch(cve_map: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
    """
    cve_map: {cve_id: [nvd_reference_urls]}
    Returns {cve_id: [poc_dicts]}
    Rate-limits: GitHub search allows 10 req/min unauthenticated.
    """
    import time
    results: Dict[str, List[Dict]] = {}
    for i, (cve_id, refs) in enumerate(cve_map.items()):
        results[cve_id] = find_pocs(cve_id, refs)
        if i < len(cve_map) - 1:
            time.sleep(6.5)  # stay under 10/min GitHub rate limit
    return results
