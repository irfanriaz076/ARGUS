from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.correlator import run_correlator
from backend.core.graph_builder import build_engagement_graph
from backend.database.neo4j_db import get_driver
from backend.database.postgres import get_db
from backend.services.attack_path import compute_attack_paths

router = APIRouter(prefix="/api/graph", tags=["graph"])


def _node_label(labels: List[str], props: Dict) -> str:
    node_type = labels[0] if labels else "Node"
    if node_type == "Engagement":
        return props.get("id", "Engagement")[:8]
    if node_type == "Domain":
        return props.get("name", "domain")
    if node_type == "IPAddress":
        return props.get("address", "ip")
    if node_type == "Port":
        return f"{props.get('number','?')}/{props.get('protocol','tcp')}"
    if node_type == "Endpoint":
        url = props.get("url", "")
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.path or url
        except Exception:
            return url[-40:] if len(url) > 40 else url
    if node_type == "Vulnerability":
        title = props.get("title", "")
        return title[:35] + "…" if len(title) > 35 else title
    if node_type == "Technology":
        return props.get("name", "tech")
    return props.get("name", props.get("address", "node"))


async def _collect_nodes_links(session, eid: str) -> tuple[List[Dict], List[Dict]]:
    """Query the engagement subgraph from Neo4j into (nodes, links) lists."""
    nodes: List[Dict] = []
    links: List[Dict] = []

    # ── Nodes ─────────────────────────────────────────────────
    nodes_result = await session.run(
        """
        MATCH (e:Engagement {id: $eid})
        CALL {
            WITH e RETURN e AS node
            UNION ALL
            WITH e MATCH (e)-[*1..5]->(n) RETURN n AS node
        }
        WITH DISTINCT node
        WHERE node IS NOT NULL
        RETURN elementId(node) AS nid,
               labels(node)    AS lbls,
               properties(node) AS props
        LIMIT 500
        """,
        eid=eid,
    )
    seen_ids: set = set()
    async for record in nodes_result:
        nid   = record["nid"]
        lbls  = record["lbls"]
        props = record["props"]
        if nid in seen_ids:
            continue
        seen_ids.add(nid)
        node_type = lbls[0] if lbls else "Node"
        nodes.append({
            "id":       nid,
            "type":     node_type,
            "label":    _node_label(lbls, props),
            "severity": props.get("severity"),
            "data":     props,
        })

    # ── Edges ─────────────────────────────────────────────────
    edges_result = await session.run(
        """
        MATCH (e:Engagement {id: $eid})
        MATCH (e)-[*0..5]->(a)-[r]->(b)
        RETURN DISTINCT
            elementId(a) AS source,
            elementId(b) AS target,
            type(r)      AS rel_type
        LIMIT 1000
        """,
        eid=eid,
    )
    seen_edges: set = set()
    async for record in edges_result:
        src = record["source"]
        tgt = record["target"]
        rel = record["rel_type"]
        key = (src, tgt, rel)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        if src in seen_ids and tgt in seen_ids:
            links.append({"source": src, "target": tgt, "type": rel})

    return nodes, links


@router.get("/{engagement_id}")
async def get_graph(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    eid = str(engagement_id)

    # Refresh graph from Postgres findings
    try:
        await build_engagement_graph(engagement_id, db)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Graph build failed: {e}")

    correlation = await run_correlator(engagement_id, db)

    try:
        driver = get_driver()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Neo4j unavailable")

    async with driver.session() as session:
        nodes, links = await _collect_nodes_links(session, eid)

    return {
        "nodes":       nodes,
        "links":       links,
        "correlation": correlation,
    }


@router.get("/{engagement_id}/attack-paths")
async def get_attack_paths(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Rank the most exploitable paths from external entry points to crown jewels."""
    eid = str(engagement_id)

    try:
        await build_engagement_graph(engagement_id, db)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Graph build failed: {e}")

    try:
        driver = get_driver()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Neo4j unavailable")

    async with driver.session() as session:
        nodes, links = await _collect_nodes_links(session, eid)

    return compute_attack_paths(nodes, links)


@router.post("/{engagement_id}/rebuild")
async def rebuild_graph(
    engagement_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    try:
        await build_engagement_graph(engagement_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "rebuilt", "engagement_id": str(engagement_id)}
