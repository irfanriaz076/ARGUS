import json
from typing import Any, Dict, List


def parse_subfinder_output(raw: str, root_domain: str) -> List[Dict[str, Any]]:
    findings = []
    seen: set[str] = set()

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        host = ""
        source = "unknown"

        if line.startswith("{"):
            try:
                data = json.loads(line)
                host = data.get("host", "")
                source = data.get("source", "unknown")
            except json.JSONDecodeError:
                host = line
        else:
            host = line

        host = host.strip().lower()
        if not host or host in seen or host == root_domain:
            continue
        seen.add(host)

        findings.append({
            "title": f"Subdomain: {host}",
            "severity": "info",
            "description": f"Subdomain of {root_domain} discovered via passive DNS enumeration ({source})",
            "evidence": {
                "subdomain": host,
                "root_domain": root_domain,
                "source": source,
            },
            "mitre_technique": "T1590",
        })

    return findings
