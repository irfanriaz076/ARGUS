import re
from typing import Any, Dict, List

# SQLMap output markers
_INJECTABLE_RE  = re.compile(r"parameter\s+'(.+?)'\s+is\s+'(.+?)'\s+injectable", re.I)
_CRITICAL_RE    = re.compile(r"\[CRITICAL\].*?parameter\s+'(.+?)'\s+might be injectable", re.I)
_DBMS_RE        = re.compile(r"database management system is\s+(.+?)[\r\n]", re.I)
_BACKEND_RE     = re.compile(r"back-end DBMS:\s*(.+?)[\r\n]", re.I)
_PAYLOAD_RE     = re.compile(r"Payload:\s*(.+?)[\r\n]", re.I)
_URL_RE         = re.compile(r"testing URL\s+'(.+?)'", re.I)
_DUMP_RE        = re.compile(r"fetched data logged to text files under '(.+?)'", re.I)
_TABLE_RE       = re.compile(r"\[\*\]\s+(.+?)$", re.M)


def parse_sqlmap_output(raw: str, target: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    if not raw:
        return findings

    # Confirmed injections (high confidence)
    for m in _INJECTABLE_RE.finditer(raw):
        param    = m.group(1)
        technique = m.group(2)
        dbms     = ""
        for dm in (_DBMS_RE, _BACKEND_RE):
            dm_m = dm.search(raw)
            if dm_m:
                dbms = dm_m.group(1).strip()
                break

        payloads = _PAYLOAD_RE.findall(raw)
        payload  = payloads[0] if payloads else ""

        findings.append({
            "title":       f"SQL Injection — parameter '{param}' on {target}",
            "severity":    "critical",
            "cvss_score":  9.8,
            "description": (
                f"Confirmed SQL injection in parameter '{param}' using {technique}. "
                f"Backend DBMS: {dbms or 'unknown'}."
            ),
            "evidence": {
                "url":        target,
                "parameter":  param,
                "technique":  technique,
                "dbms":       dbms,
                "payload":    payload,
                "proof":      f"Parameter '{param}' is injectable via '{technique}'",
                "source":     "sqlmap",
            },
            "mitre_technique": "T1190",
        })

    # Possible injections (lower confidence, heuristic)
    if not findings:
        for m in _CRITICAL_RE.finditer(raw):
            param = m.group(1)
            findings.append({
                "title":       f"Possible SQL Injection — parameter '{param}' on {target}",
                "severity":    "high",
                "cvss_score":  8.1,
                "description": f"Heuristic test indicates parameter '{param}' may be injectable. Manual verification needed.",
                "evidence": {
                    "url":       target,
                    "parameter": param,
                    "proof":     f"Heuristic flag on '{param}' — basic test positive",
                    "source":    "sqlmap",
                },
                "mitre_technique": "T1190",
            })

    return findings
