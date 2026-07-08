import json
import re
from typing import Any, Dict, List

_FOUND_RE = re.compile(
    r"\[.*?POC.*?\]\s+(.*?)(?:\s+=>|\s+\[)", re.I
)


def parse_dalfox_output(raw: str, target: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for line in raw.splitlines():
        line = line.strip()

        # JSON mode output
        if line.startswith("{"):
            try:
                obj = json.loads(line)
                poc_url  = obj.get("poc", obj.get("url", ""))
                param    = obj.get("param", "")
                payload  = obj.get("payload", "")
                evidence = obj.get("evidence", "")
                key = f"{param}:{payload[:40]}"
                if key in seen:
                    continue
                seen.add(key)
                findings.append(_make_finding(target, poc_url, param, payload, evidence))
            except json.JSONDecodeError:
                pass
            continue

        # Text output — look for [POC] lines
        if "[POC]" in line or "[G]" in line or "[V]" in line:
            m = _FOUND_RE.search(line)
            poc_url = m.group(1).strip() if m else ""
            # Extract param from URL query
            param = ""
            pm = re.search(r"[?&](\w+)=", poc_url)
            if pm:
                param = pm.group(1)
            key = poc_url[:80]
            if key in seen:
                continue
            seen.add(key)
            findings.append(_make_finding(target, poc_url, param, "", line))

    return findings


def _make_finding(
    target: str,
    poc_url: str,
    param: str,
    payload: str,
    evidence: str,
) -> Dict[str, Any]:
    return {
        "title":       f"XSS — parameter '{param or 'unknown'}' on {target}",
        "severity":    "high",
        "cvss_score":  6.1,
        "description": (
            f"Reflected Cross-Site Scripting confirmed in parameter '{param or 'unknown'}'. "
            f"An attacker can inject malicious scripts into the page context of other users."
        ),
        "evidence": {
            "url":     target,
            "poc_url": poc_url,
            "param":   param,
            "payload": payload,
            "proof":   poc_url or evidence[:300],
            "source":  "dalfox",
        },
        "mitre_technique": "T1059.007",
    }
