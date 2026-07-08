import json
from typing import Any, Dict, List

SENSITIVE_PATHS = {
    "admin", "administrator", "login", "wp-admin", "phpmyadmin",
    "backup", "config", ".env", ".git", "console", "jenkins",
    "actuator", "debug", "test", "dev", "secret", "secrets",
    "private", "shell", "panel", "portal", "manage", "manager",
    "api/swagger", "swagger", "graphql", "dashboard",
}

STATUS_SEVERITY = {
    200: "medium",
    401: "low",
    403: "low",
    301: "info",
    302: "info",
}


def parse_ffuf_output(json_content: str, base_url: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    try:
        data = json.loads(json_content)
        results = data.get("results", [])
    except (json.JSONDecodeError, ValueError):
        return findings

    for result in results:
        url     = result.get("url", "")
        status  = result.get("status", 0)
        path    = result.get("input", {}).get("FUZZ", "")
        length  = result.get("length", 0)
        words   = result.get("words", 0)
        lines   = result.get("lines", 0)

        if not url:
            continue

        is_sensitive = path.lower().strip("/") in SENSITIVE_PATHS
        severity = "high" if (is_sensitive and status == 200) else STATUS_SEVERITY.get(status, "info")

        findings.append({
            "title": f"Endpoint Discovered: /{path} [{status}]",
            "severity": severity,
            "description": (
                f"HTTP {status} at {url} ({length} bytes, {words} words)"
                + (" — SENSITIVE PATH" if is_sensitive else "")
            ),
            "evidence": {
                "url":            url,
                "path":           path,
                "status_code":    status,
                "content_length": length,
                "words":          words,
                "lines":          lines,
                "sensitive":      is_sensitive,
            },
            "mitre_technique": "T1083",
        })

    return findings
