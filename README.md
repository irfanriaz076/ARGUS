# ARGUS
### Autonomous Reconnaissance & Guided Unified Scanner

> Not a tool wrapper. An orchestration engine with a brain.

ARGUS is a self-contained security orchestration platform that runs a full recon-to-exploitation kill chain — discovers subdomains, probes live hosts, fingerprints services, fuzzes directories, hunts CVEs — then maps everything into a live attack-surface graph and generates a professional PDF report.

---

## Features

- **Kill Chain Orchestration** — recon → enumeration → vulnerability, fully automated
- **5 Integrated Tools** — subfinder, httpx, nmap, ffuf, nuclei
- **Live Terminal Streaming** — WebSocket-powered real-time tool output in the browser
- **Attack Surface Graph** — D3.js force-directed Neo4j graph with severity heat-map, zoom, node drill-down
- **CVE Enrichment** — NVD API v2 auto-populates CVSS scores, vectors, and patch links after each scan
- **PDF Reports** — one-click professional pentest report with exec summary, findings, MITRE ATT&CK table
- **Scope Enforcement** — hard-block prevents scanning out-of-scope targets (wildcard, exact, CIDR)
- **Target Auto-Expansion** — subdomains discovered by subfinder are automatically added and scanned
- **Cyberpunk UI** — 3D HoloCards, neon palette, particle field, HUD corners, glitch effects

---

## Quick Start

```bash
git clone https://github.com/Hamza-Shaukat078/ARGUS.git
cd argus
cp .env.example .env
docker compose -f docker/docker-compose.yml up --build
```

Open **http://localhost:5173**

Neo4j browser at **http://localhost:7474** (neo4j / argus_neo4j_pass)

---

## Usage

1. **Create an Engagement** — give it a name and scope (`*.example.com`, `10.0.0.0/24`)
2. **Add Targets** — domains, IPs, CIDRs, URLs
3. **Launch Scan** — ARGUS queues the full kill chain automatically
4. **Watch Live** — terminal streams tool output in real-time
5. **Explore Graph** — GRAPH tab shows the full attack surface in Neo4j/D3
6. **Review Findings** — sorted by severity, enriched with NVD CVE data and patch links
7. **Export PDF** — one-click report generation when engagement is complete

---

## Architecture

```
Browser (React + D3)
    │  WebSocket (live streaming)
    │  REST API
    ▼
FastAPI Backend
    │  Celery Tasks
    ▼
Redis (broker + pub/sub)     PostgreSQL (findings/scans)     Neo4j (attack graph)
    │
    ▼
Worker (Celery)
    └── PluginRegistry
            ├── subfinder    (recon)
            ├── httpx        (recon)
            ├── nmap         (enumeration)
            ├── ffuf         (enumeration)
            └── nuclei       (vulnerability)
```

---

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI, asyncpg, SQLAlchemy async |
| Task Queue | Celery + Redis |
| Graph DB | Neo4j 5 (APOC) |
| Relational DB | PostgreSQL 15 |
| Security Tools | subfinder, httpx, nmap, ffuf, nuclei |
| Frontend | React 18, Vite, Tailwind CSS, Framer Motion, D3 v7 |
| Infrastructure | Docker Compose, multi-stage Go build |

---

## Configuration

Copy `.env.example` to `.env` and set:

```env
DATABASE_URL=postgresql+asyncpg://argus:argus@postgres:5432/argus
REDIS_URL=redis://redis:6379/0
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=argus_neo4j_pass
NVD_API_KEY=           # optional — increases NVD rate limit 10x
SECRET_KEY=change-me-in-production
```

---

## Plugin System

Adding a new tool takes ~30 lines:

```python
# backend/plugins/recon/my_tool.py
from backend.plugins.base_plugin import BasePlugin, PluginResult

class MyToolPlugin(BasePlugin):
    name = "my_tool"
    stage = "recon"                          # recon | enumeration | vulnerability
    supported_target_types = ["domain"]

    async def run(self, target, target_type, publish) -> PluginResult:
        cmd = ["my-tool", "-d", target, "-json"]
        raw = await self.execute_command(cmd, publish)
        findings = parse_my_tool_output(raw, target)
        return PluginResult(raw_output=raw, findings=findings)
```

Register in `backend/plugins/base_plugin.py` → `PluginRegistry._load_plugins()`.

---

## Project Structure

```
argus/
├── backend/
│   ├── api/routes/          # FastAPI routers (engagements, graph, reports, ...)
│   ├── core/
│   │   ├── orchestrator.py  # Kill chain engine + scope enforcement
│   │   ├── scheduler.py     # Celery tasks
│   │   ├── graph_builder.py # Postgres findings -> Neo4j graph
│   │   └── correlator.py    # Deduplication + risk scoring
│   ├── plugins/
│   │   ├── recon/           # subfinder, httpx_probe
│   │   ├── enumeration/     # nmap_scanner, ffuf_fuzzer
│   │   └── vulnerability/   # nuclei_scanner
│   ├── parsers/             # Per-tool output parsers
│   ├── services/
│   │   ├── nvd_client.py    # NVD API v2 client
│   │   ├── enrichment.py    # CVE enrichment service
│   │   └── pdf_reporter.py  # ReportLab PDF generation
│   └── database/
│       ├── models.py        # SQLAlchemy ORM (Engagement/Target/Scan/Finding)
│       ├── postgres.py      # Async engine + session
│       └── neo4j_db.py      # Neo4j async driver
├── frontend/
│   └── src/
│       ├── components/      # HoloCard, AttackGraph, FindingCard, TerminalStream, ...
│       └── pages/           # Dashboard, Engagements, EngagementDetail, Findings
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile.backend   # Multi-stage: Go tools + Python 3.11
└── README.md
```

---

## Phases

| Phase | Status | Description |
|---|---|---|
| 1 | Complete | Core API, nmap plugin, WebSocket streaming, cyberpunk UI |
| 2 | Complete | subfinder, httpx, ffuf, nuclei plugins |
| 3 | Complete | Neo4j attack graph, D3 visualisation, correlator |
| 4 | Complete | CVE enrichment, PDF reports, scope hard-block |

---

## License

MIT
