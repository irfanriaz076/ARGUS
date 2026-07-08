import json
from typing import Any, Dict, List

_SEVERITY_MAP = {
    "CRITICAL": "critical",
    "HIGH":     "high",
    "MEDIUM":   "medium",
    "LOW":      "low",
    "WARN":     "low",
    "WARNING":  "low",
    "INFO":     "info",
    "OK":       "info",
    "DEBUG":    "info",
}

_SKIP_IDS = {
    "service", "hostname", "engine_problem", "banner_server", "banner_application",
    "cert_numbers", "tls_timestamp", "HTTP_status_code",
}

_CVE_MITRE = {
    "CVE-2014-0160": ("T1190", 9.8, "Heartbleed — OpenSSL memory leak exposes private keys and plaintext"),
    "CVE-2014-3566": ("T1600", 3.4, "POODLE — SSL 3.0 CBC padding oracle"),
    "CVE-2015-4000": ("T1557", 3.7, "Logjam — DHE key exchange downgrade to export-grade"),
    "CVE-2016-0800": ("T1600", 5.9, "DROWN — SSLv2 decryption attack on RSA keys"),
    "CVE-2019-1559": ("T1600", 5.9, "GOLDENDOODLE — TLS CBC padding oracle"),
}


def parse_testssl_output(raw: str, target: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return findings

    entries = data if isinstance(data, list) else data.get("scanResult", [{}])[0].get("findings", [])

    for entry in entries:
        fid      = entry.get("id", "")
        severity = entry.get("severity", "INFO")
        finding  = entry.get("finding", "")
        cve_str  = entry.get("cve", "")
        cwe      = entry.get("cwe", "")

        if fid in _SKIP_IDS:
            continue
        if severity in ("OK", "INFO", "DEBUG") and not cve_str:
            continue
        if "not vulnerable" in finding.lower() or finding.strip() == "":
            continue

        sev = _SEVERITY_MAP.get(severity.upper(), "info")

        # Promote to critical if VULNERABLE
        if "VULNERABLE" in finding.upper() and sev not in ("critical", "high"):
            sev = "high"

        # CVE mapping
        cve_id = cve_str.split()[0] if cve_str else None
        known  = _CVE_MITRE.get(cve_id, ("T1600", None, ""))
        mitre  = known[0]
        cvss   = known[1]
        kn_desc = known[2]

        findings.append({
            "title":       f"TLS: {fid.replace('_', ' ').title()} — {finding[:80]}",
            "severity":    sev,
            "cvss_score":  cvss,
            "cve_id":      cve_id,
            "description": kn_desc or (
                f"TLS/SSL issue on {target}: [{fid}] {finding}. "
                f"CWE: {cwe}."
            ),
            "evidence": {
                "check_id": fid,
                "finding":  finding,
                "severity": severity,
                "cve":      cve_str,
                "cwe":      cwe,
                "source":   "testssl",
                "proof":    f"testssl check '{fid}': {finding}",
            },
            "mitre_technique": mitre,
        })

    return findings
