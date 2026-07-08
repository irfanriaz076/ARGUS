import json
from typing import Any, Dict, List

SEVERITY_BY_OSVDB = {
    "0": "info",
}

KEYWORD_SEVERITY = {
    "remote code": "critical",
    "rce":         "critical",
    "sql inject":  "critical",
    "command exec":"critical",
    "directory traversal": "high",
    "file include": "high",
    "xss":         "high",
    "cross-site":  "high",
    "csrf":        "medium",
    "information disclosure": "medium",
    "default":     "medium",
    "backup":      "medium",
    "config":      "medium",
    "admin":       "medium",
    "phpinfo":     "medium",
    "debug":       "medium",
    "test":        "low",
    "header":      "low",
    "cookie":      "low",
    "clickjack":   "low",
}

TAG_MITRE = {
    "xss":       "T1059.007",
    "sql":       "T1190",
    "rce":       "T1190",
    "default":   "T1078",
    "config":    "T1552",
    "admin":     "T1190",
    "traversal": "T1083",
    "backup":    "T1552",
    "phpinfo":   "T1082",
}


def _infer_severity(msg: str) -> str:
    ml = msg.lower()
    for kw, sev in KEYWORD_SEVERITY.items():
        if kw in ml:
            return sev
    return "info"


def _infer_mitre(msg: str) -> str:
    ml = msg.lower()
    for kw, mitre in TAG_MITRE.items():
        if kw in ml:
            return mitre
    return "T1082"


def parse_nikto_output(raw: str, target: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    # Nikto outputs one JSON object per line (or a single JSON object)
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        host = data.get("host", target)
        port = data.get("port", "80")
        ip   = data.get("ip", "")

        for vuln in data.get("vulnerabilities", []):
            msg    = vuln.get("msg", "")
            url    = vuln.get("url", "/")
            method = vuln.get("method", "GET")
            vid    = vuln.get("id", "")
            osvdb  = vuln.get("OSVDB", "0")

            if not msg:
                continue

            sev   = _infer_severity(msg)
            mitre = _infer_mitre(msg)

            findings.append({
                "title": f"Nikto: {msg[:120]}",
                "severity": sev,
                "description": msg,
                "evidence": {
                    "ip":     ip,
                    "host":   host,
                    "port":   port,
                    "url":    url,
                    "method": method,
                    "nikto_id": vid,
                    "osvdb":  osvdb,
                    "proof":  f"{method} {url} → {msg}",
                    "source": "nikto",
                },
                "mitre_technique": mitre,
            })

    return findings
