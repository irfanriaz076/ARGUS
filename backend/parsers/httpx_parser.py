import json
from typing import Any, Dict, List

INTERESTING_TECH = {
    "wordpress", "joomla", "drupal", "magento", "shopify",
    "jenkins", "grafana", "kibana", "gitlab", "portainer",
    "django", "laravel", "rails", "strapi", "ghost",
    "apache tomcat", "weblogic", "jboss",
}


def parse_httpx_output(raw: str, target: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    for line in raw.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        url          = data.get("url", "")
        status       = data.get("status_code", 0)
        title        = data.get("title", "")
        technologies = data.get("tech", [])
        webserver    = data.get("webserver", "")
        content_len  = data.get("content_length", 0)
        ip           = data.get("host", "")

        if not url:
            continue

        findings.append({
            "title": f"Live Web Service: {url} [{status}]",
            "severity": "info",
            "description": (
                f"HTTP {status} — {title or 'No title'}"
                + (f" (via {webserver})" if webserver else "")
            ),
            "evidence": {
                "url": url,
                "status_code": status,
                "title": title,
                "technologies": technologies,
                "webserver": webserver,
                "content_length": content_len,
                "ip": ip,
            },
            "mitre_technique": "T1046",
        })

        for tech in technologies:
            tech_lower = tech.lower()
            if any(kw in tech_lower for kw in INTERESTING_TECH):
                findings.append({
                    "title": f"Technology Detected: {tech}",
                    "severity": "medium",
                    "description": f"{tech} running at {url} — verify patch level and default credentials",
                    "evidence": {"technology": tech, "url": url, "status_code": status},
                    "mitre_technique": "T1518",
                })

    return findings
