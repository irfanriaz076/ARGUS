"""
Attack-path analysis over the engagement graph.

Given the node/link graph already produced for the D3 view, this module:
  1. Scores every node for "crown-jewel" value (how valuable it is to reach).
  2. Weights every edge by traversal difficulty (easier = cheaper).
  3. Runs a multi-source Dijkstra from the external entry points and returns
     the lowest-cost (= most exploitable) path to each crown jewel, ranked.

No external graph library — a small heapq Dijkstra keeps this dependency-free
and makes the algorithm auditable, which is the point of the feature.
"""

from __future__ import annotations

import heapq
from typing import Any, Dict, List, Optional, Tuple

# ── Edge traversal cost (lower = easier for an attacker to cross) ────────────
_EDGE_COST = {
    "HAS_TARGET":        0.3,
    "RESOLVES_TO":       0.5,
    "HAS_ENDPOINT":      0.7,
    "HAS_PORT":          0.8,
    "HAS_SUBDOMAIN":     0.9,
    "USES":              1.0,
}
# A vulnerability is a *cheap* pivot — the worse the sev, the easier the hop.
_VULN_COST = {"critical": 0.15, "high": 0.35, "medium": 0.6, "low": 0.85, "info": 1.0}

# ── Crown-jewel valuation ────────────────────────────────────────────────────
_VULN_VALUE = {"critical": 100, "high": 78, "medium": 45, "low": 20, "info": 5}
_DB_SERVICES = ("mysql", "postgres", "postgresql", "mssql", "mongo", "mongodb",
                "redis", "elastic", "elasticsearch", "oracle", "cassandra", "memcached")
_ADMIN_SERVICES = ("ssh", "rdp", "vnc", "telnet", "ftp", "smb", "winrm", "ldap")
_JUICY_TECH = ("jenkins", "gitlab", "phpmyadmin", "grafana", "kibana", "tomcat",
               "wordpress", "jira", "confluence", "sonarqube", "adminer", "portainer")
_JUICY_PATH = ("admin", "login", "dashboard", "phpmyadmin", "jenkins", ".git",
               "config", "backup", ".env", "wp-admin", "console", "manager")

JEWEL_THRESHOLD = 45  # value at/above which a node is treated as a crown jewel

MAX_COST = 6.0        # cost beyond which a path is considered "hard"


def _lower(v: Any) -> str:
    return str(v or "").lower()


def jewel_value(node: Dict) -> Tuple[int, str]:
    """Return (value, reason) describing how valuable reaching this node is."""
    ntype = node.get("type")
    data = node.get("data") or {}

    if ntype == "Vulnerability":
        sev = _lower(data.get("severity")) or "info"
        cve = data.get("cve_id")
        reason = f"{sev} vulnerability" + (f" ({cve})" if cve else "")
        return _VULN_VALUE.get(sev, 5), reason

    if ntype == "Port":
        svc = _lower(data.get("service"))
        num = data.get("number", "?")
        if any(s in svc for s in _DB_SERVICES):
            return 85, f"exposed database service ({svc or num})"
        if any(s in svc for s in _ADMIN_SERVICES):
            return 62, f"remote-admin service ({svc or num})"
        return 28, f"open port {num}"

    if ntype == "Endpoint":
        if data.get("sensitive"):
            return 72, "sensitive endpoint"
        blob = _lower(data.get("path")) + " " + _lower(data.get("url")) + " " + _lower(data.get("title"))
        if any(p in blob for p in _JUICY_PATH):
            return 66, "administrative / sensitive path"
        return 15, "web endpoint"

    if ntype == "Technology":
        name = _lower(data.get("name"))
        if any(t in name for t in _JUICY_TECH):
            return 60, f"high-value technology ({data.get('name')})"
        return 8, "technology"

    return 0, ""


def _edge_cost(link: Dict, dst: Dict) -> float:
    rel = link.get("type")
    if rel == "HAS_VULNERABILITY":
        sev = _lower((dst.get("data") or {}).get("severity")) or "info"
        return _VULN_COST.get(sev, 1.0)
    return _EDGE_COST.get(rel, 1.0)


def _band(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _brief(node: Dict) -> Dict:
    return {"id": node["id"], "type": node["type"], "label": node.get("label", "")}


def _hop_annotation(node: Dict) -> str:
    """A short human tag for a node used when rendering the path story."""
    data = node.get("data") or {}
    label = node.get("label", "")
    if node["type"] == "Port":
        svc = data.get("service")
        return f"{label} ({svc})" if svc else label
    if node["type"] == "Vulnerability":
        cve = data.get("cve_id")
        return f"{label} [{cve}]" if cve else label
    return label


def compute_attack_paths(
    nodes: List[Dict],
    links: List[Dict],
    max_paths: int = 6,
) -> Dict[str, Any]:
    """Analyse the graph and return ranked attack paths + crown jewels."""
    node_map: Dict[str, Dict] = {n["id"]: n for n in nodes}

    # Directed adjacency: src -> [(dst_id, cost, rel)]
    adj: Dict[str, List[Tuple[str, float, str]]] = {n["id"]: [] for n in nodes}
    for l in links:
        s, t = l.get("source"), l.get("target")
        if s in node_map and t in node_map:
            adj[s].append((t, _edge_cost(l, node_map[t]), l.get("type", "")))

    # Entry points = engagement's direct targets; fall back to all domains/IPs.
    engagement_ids = {n["id"] for n in nodes if n["type"] == "Engagement"}
    entries = [
        l["target"] for l in links
        if l.get("type") == "HAS_TARGET" and l.get("source") in engagement_ids
        and l.get("target") in node_map
    ]
    if not entries:
        entries = [n["id"] for n in nodes if n["type"] in ("Domain", "IPAddress")]
    entries = list(dict.fromkeys(entries))  # de-dup, keep order

    # Crown jewels
    jewels: List[Dict] = []
    for n in nodes:
        val, reason = jewel_value(n)
        if val >= JEWEL_THRESHOLD:
            jewels.append({**_brief(n), "value": val, "reason": reason})

    if not entries or not jewels:
        return {
            "paths": [],
            "crown_jewels": jewels,
            "entries": entries,
            "summary": {"jewel_count": len(jewels), "reachable_count": 0, "max_score": 0},
        }

    # Multi-source Dijkstra via a virtual super-source (id = None).
    dist: Dict[Optional[str], float] = {None: 0.0}
    prev: Dict[str, Optional[str]] = {}
    heap: List[Tuple[float, Optional[str]]] = [(0.0, None)]
    entry_set = set(entries)

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, float("inf")):
            continue
        edges = (
            [(e, 0.0, "ENTRY") for e in entries] if u is None
            else adj.get(u, [])
        )
        for v, cost, _rel in edges:
            nd = d + cost
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))

    def reconstruct(target_id: str) -> List[str]:
        path: List[str] = []
        cur: Optional[str] = target_id
        while cur is not None:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        return path

    # Best path per jewel
    paths: List[Dict] = []
    for jew in jewels:
        jid = jew["id"]
        if jid not in dist:
            continue  # unreachable from any entry
        total_cost = dist[jid]
        node_ids = reconstruct(jid)
        if len(node_ids) < 2:
            continue
        exploitability = max(0.0, 1.0 - total_cost / MAX_COST)
        score = round(jew["value"] * (0.55 + 0.45 * exploitability))
        hops = [node_map[i] for i in node_ids]
        link_keys = [[node_ids[i], node_ids[i + 1]] for i in range(len(node_ids) - 1)]
        rationale = " → ".join(_hop_annotation(h) for h in hops)

        paths.append({
            "id": f"path-{len(paths)}",
            "score": score,
            "severity": _band(score),
            "jewel_value": jew["value"],
            "exploitability": round(exploitability, 2),
            "cost": round(total_cost, 2),
            "entry": _brief(hops[0]),
            "target": {**_brief(hops[-1]), "reason": jew["reason"]},
            "hops": [_brief(h) for h in hops],
            "node_ids": node_ids,
            "link_keys": link_keys,
            "rationale": rationale,
        })

    paths.sort(key=lambda p: p["score"], reverse=True)
    paths = paths[:max_paths]
    # Re-id after sort/truncate so ids are stable for the frontend
    for i, p in enumerate(paths):
        p["id"] = f"path-{i}"

    return {
        "paths": paths,
        "crown_jewels": sorted(jewels, key=lambda j: j["value"], reverse=True),
        "entries": entries,
        "summary": {
            "jewel_count": len(jewels),
            "reachable_count": len(paths),
            "max_score": paths[0]["score"] if paths else 0,
        },
    }
