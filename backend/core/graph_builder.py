"""
Translates scan findings into a Neo4j attack-surface graph.
Each plugin maps to a distinct set of node types and relationships.

Graph schema
------------
(:Engagement)
  -[:HAS_TARGET]->  (:Domain | :IPAddress)
(:Domain)
  -[:HAS_SUBDOMAIN]->  (:Domain)
  -[:HAS_ENDPOINT]->   (:Endpoint)
  -[:RESOLVES_TO]->    (:IPAddress)
(:IPAddress)
  -[:HAS_PORT]->       (:Port)
  -[:HAS_ENDPOINT]->   (:Endpoint)
(:Port)
  -[:HAS_VULNERABILITY]-> (:Vulnerability)
(:Endpoint)
  -[:HAS_VULNERABILITY]-> (:Vulnerability)
  -[:USES]->              (:Technology)
"""

from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select

from neo4j import AsyncGraphDatabase

from backend.config import settings
from backend.database.models import Finding, Scan, Target


async def build_engagement_graph(engagement_id: str | UUID, db) -> None:
    eid = str(engagement_id)

    # ── Fetch data from Postgres ──────────────────────────────────
    targets_res = await db.execute(select(Target).where(Target.engagement_id == engagement_id))
    targets: List[Target] = targets_res.scalars().all()

    scans_res = await db.execute(select(Scan).where(Scan.engagement_id == engagement_id))
    scans: List[Scan] = scans_res.scalars().all()

    findings_res = await db.execute(select(Finding).where(Finding.engagement_id == engagement_id))
    findings: List[Finding] = findings_res.scalars().all()

    scan_map = {str(s.id): s for s in scans}
    target_map = {str(t.id): t for t in targets}

    # ── Write to Neo4j ────────────────────────────────────────────
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    try:
      await driver.verify_connectivity()
    except Exception:
      await driver.close()
      raise

    try:
      async with driver.session() as session:
        # Engagement anchor node
        await session.run(
            "MERGE (e:Engagement {id: $id})",
            id=eid,
        )

        # Initial target nodes
        for t in targets:
            if t.type == "domain":
                await session.run(
                    """
                    MERGE (d:Domain {name: $name})
                    WITH d
                    MATCH (e:Engagement {id: $eid})
                    MERGE (e)-[:HAS_TARGET]->(d)
                    """,
                    name=t.value, eid=eid,
                )
            elif t.type in ("ip", "cidr"):
                await session.run(
                    """
                    MERGE (ip:IPAddress {address: $addr})
                    WITH ip
                    MATCH (e:Engagement {id: $eid})
                    MERGE (e)-[:HAS_TARGET]->(ip)
                    """,
                    addr=t.value, eid=eid,
                )
            elif t.type == "url":
                await session.run(
                    """
                    MERGE (ep:Endpoint {url: $url})
                    WITH ep
                    MATCH (e:Engagement {id: $eid})
                    MERGE (e)-[:HAS_TARGET]->(ep)
                    """,
                    url=t.value, eid=eid,
                )

        # Process findings
        for finding in findings:
            scan = scan_map.get(str(finding.scan_id))
            target = target_map.get(str(finding.target_id))
            if not scan:
                continue

            plugin = scan.plugin_name
            ev: Dict[str, Any] = finding.evidence or {}
            target_val = target.value if target else ""
            target_type = target.type if target else "domain"

            await _handle_finding(session, plugin, finding, ev, target_val, target_type)
    finally:
        await driver.close()


async def _handle_finding(session, plugin: str, finding, ev: dict, target: str, target_type: str):
    title = finding.title or ""

    if plugin == "subfinder":
        subdomain = ev.get("subdomain", "")
        root = ev.get("root_domain", target)
        if subdomain:
            await session.run(
                """
                MERGE (root:Domain {name: $root})
                MERGE (sub:Domain  {name: $sub})
                MERGE (root)-[:HAS_SUBDOMAIN]->(sub)
                """,
                root=root, sub=subdomain,
            )

    elif plugin == "nmap_scanner":
        port_str = str(ev.get("port", ""))
        proto    = ev.get("protocol", "tcp")
        service  = ev.get("service", "")
        version  = ev.get("version", "")
        host     = ev.get("host", target)

        if port_str and port_str.isdigit():
            # Resolve host type
            if target_type in ("domain",):
                await session.run(
                    """
                    MERGE (d:Domain {name: $name})
                    MERGE (ip:IPAddress {address: $host})
                    MERGE (d)-[:RESOLVES_TO]->(ip)
                    MERGE (ip)-[:HAS_PORT]->(p:Port {address: $host, number: $port, protocol: $proto})
                    SET p.service = $service, p.version = $version
                    """,
                    name=target, host=host,
                    port=int(port_str), proto=proto,
                    service=service, version=version,
                )
            else:
                await session.run(
                    """
                    MERGE (ip:IPAddress {address: $host})
                    MERGE (ip)-[:HAS_PORT]->(p:Port {address: $host, number: $port, protocol: $proto})
                    SET p.service = $service, p.version = $version
                    """,
                    host=host or target,
                    port=int(port_str), proto=proto,
                    service=service, version=version,
                )

    elif plugin == "httpx_probe":
        url = ev.get("url", "")
        if url and "Live Web Service" in title:
            techs = ev.get("technologies", [])
            await session.run(
                """
                MERGE (ep:Endpoint {url: $url})
                SET ep.status_code = $status,
                    ep.title       = $title_val,
                    ep.webserver   = $ws
                WITH ep
                MERGE (d:Domain {name: $target})
                MERGE (d)-[:HAS_ENDPOINT]->(ep)
                """,
                url=url, status=ev.get("status_code", 0),
                title_val=ev.get("title", ""), ws=ev.get("webserver", ""),
                target=target,
            )
            for tech in techs:
                await session.run(
                    """
                    MERGE (t:Technology {name: $name})
                    MERGE (ep:Endpoint {url: $url})
                    MERGE (ep)-[:USES]->(t)
                    """,
                    name=tech, url=url,
                )

    elif plugin == "nuclei_scanner":
        matched_at = ev.get("matched_at", "") or ev.get("url", "") or target
        vid = f"vuln:{finding.title}:{matched_at}"
        await session.run(
            """
            MERGE (v:Vulnerability {vid: $vid})
            SET v.title      = $title,
                v.severity   = $severity,
                v.cve_id     = $cve,
                v.cvss_score = $cvss,
                v.mitre      = $mitre,
                v.template   = $tmpl
            WITH v
            MERGE (ep:Endpoint {url: $url})
            MERGE (ep)-[:HAS_VULNERABILITY]->(v)
            """,
            vid=vid,
            title=finding.title,
            severity=finding.severity,
            cve=finding.cve_id or "",
            cvss=float(finding.cvss_score) if finding.cvss_score else 0.0,
            mitre=finding.mitre_technique or "",
            tmpl=ev.get("template_id", ""),
            url=matched_at,
        )

    elif plugin == "ffuf_fuzzer":
        url  = ev.get("url", "")
        path = ev.get("path", "")
        if url:
            sensitive = ev.get("sensitive", False)
            await session.run(
                """
                MERGE (ep:Endpoint {url: $url})
                SET ep.path        = $path,
                    ep.status_code = $status,
                    ep.sensitive   = $sensitive
                WITH ep
                MERGE (d:Domain {name: $target})
                MERGE (d)-[:HAS_ENDPOINT]->(ep)
                """,
                url=url, path=path,
                status=ev.get("status_code", 0),
                sensitive=sensitive,
                target=target,
            )
