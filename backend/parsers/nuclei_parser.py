import json
from typing import Any, Dict, List

SEVERITY_MAP = {
    "critical": "critical",
    "high":     "high",
    "medium":   "medium",
    "low":      "low",
    "info":     "info",
    "unknown":  "info",
}

TAG_TO_MITRE = {
    "rce":              "T1190",
    "sqli":             "T1190",
    "xss":              "T1059.007",
    "ssrf":             "T1190",
    "lfi":              "T1083",
    "rfi":              "T1190",
    "open-redirect":    "T1190",
    "default-login":    "T1078",
    "default-password": "T1078",
    "exposure":         "T1552",
    "misconfiguration": "T1210",
    "cve":              "T1190",
    "panel":            "T1190",
    "takeover":         "T1584",
    "injection":        "T1190",
    "deserialization":  "T1190",
    "traversal":        "T1083",
}


def parse_nuclei_output(raw: str, target: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    for line in raw.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        info        = data.get("info", {})
        template_id = data.get("template-id", "")
        name        = info.get("name", template_id)
        description = info.get("description", "")
        severity    = SEVERITY_MAP.get(info.get("severity", "info").lower(), "info")
        matched_at  = data.get("matched-at", target)
        tags: list  = info.get("tags", [])
        references  = info.get("reference", [])

        mitre = None
        for tag in tags:
            mitre = TAG_TO_MITRE.get(tag.lower())
            if mitre:
                break
        if not mitre:
            mitre = "T1190"

        cve_id = next(
            (t.upper() for t in tags if t.upper().startswith("CVE-")),
            None
        )

        cvss = info.get("classification", {}).get("cvss-score")

        findings.append({
            "title": name,
            "severity": severity,
            "cvss_score": float(cvss) if cvss else None,
            "description": description or f"Nuclei template {template_id} matched at {matched_at}",
            "evidence": {
                "template_id":  template_id,
                "matched_at":   matched_at,
                "url":          data.get("url", ""),
                "ip":           data.get("ip", ""),
                "type":         data.get("type", ""),
                "tags":         tags,
                "references":   references,
                "curl_command": data.get("curl-command", ""),
            },
            "cve_id":          cve_id,
            "mitre_technique": mitre,
        })

    return findings
