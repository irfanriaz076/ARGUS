"""
MITRE ATT&CK tagging for findings.

Maps each finding to a real ATT&CK technique (id + name + tactic) using, in
priority order: strong title/description/tag keywords, the presence of a CVE,
then a per-plugin default. This grounds the technique IDs that show on finding
cards and that the LLM narrative references — instead of every finding being a
generic "T1190".
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# ── ATT&CK technique catalog (subset relevant to external web/infra testing) ──
TECHNIQUES: Dict[str, Dict[str, str]] = {
    "T1595":     {"name": "Active Scanning",                         "tactic": "Reconnaissance"},
    "T1595.002": {"name": "Vulnerability Scanning",                  "tactic": "Reconnaissance"},
    "T1590":     {"name": "Gather Victim Network Information",       "tactic": "Reconnaissance"},
    "T1596":     {"name": "Search Open Technical Databases",         "tactic": "Reconnaissance"},
    "T1593.003": {"name": "Search Open Websites/Domains: Code Repos","tactic": "Reconnaissance"},
    "T1046":     {"name": "Network Service Discovery",               "tactic": "Discovery"},
    "T1083":     {"name": "File and Directory Discovery",            "tactic": "Discovery"},
    "T1190":     {"name": "Exploit Public-Facing Application",       "tactic": "Initial Access"},
    "T1078":     {"name": "Valid Accounts",                          "tactic": "Initial Access"},
    "T1210":     {"name": "Exploitation of Remote Services",         "tactic": "Lateral Movement"},
    "T1059.007": {"name": "JavaScript (Cross-Site Scripting)",       "tactic": "Execution"},
    "T1552":     {"name": "Unsecured Credentials",                   "tactic": "Credential Access"},
    "T1552.001": {"name": "Unsecured Credentials: Credentials In Files", "tactic": "Credential Access"},
    "T1110":     {"name": "Brute Force",                             "tactic": "Credential Access"},
    "T1584":     {"name": "Compromise Infrastructure",              "tactic": "Resource Development"},
    "T1557":     {"name": "Adversary-in-the-Middle",                "tactic": "Collection"},
    "T1213.003": {"name": "Data from Code Repositories",            "tactic": "Collection"},
    "T1071.001": {"name": "Application Layer Protocol: Web",        "tactic": "Command and Control"},
}

# ── Per-plugin default technique ─────────────────────────────────────────────
PLUGIN_DEFAULT: Dict[str, str] = {
    "subfinder":            "T1590",
    "crtsh_enum":           "T1590",
    "whois_asn":            "T1590",
    "shodan_lookup":        "T1596",
    "github_dorking":       "T1593.003",
    "httpx_probe":          "T1595",
    "gowitness_screenshot": "T1595",
    "nmap_scanner":         "T1046",
    "ffuf_fuzzer":          "T1083",
    "nuclei_scanner":       "T1190",
    "git_exposure":         "T1213.003",
    "sensitive_files":      "T1552.001",
    "sqlmap_scanner":       "T1190",
    "dalfox_scanner":       "T1059.007",
    "nikto_scanner":        "T1190",
    "wpscan_lite":          "T1190",
    "hydra_brute":          "T1110",
    "cors_tester":          "T1190",
    "header_analyzer":      "T1595.002",
    "testssl_scanner":      "T1557",
}

# ── Keyword rules (strongest signal first) ───────────────────────────────────
# Each entry: (substring to look for in the finding text, technique id)
KEYWORD_RULES: List[Tuple[str, str]] = [
    ("sql injection", "T1190"), ("sqli", "T1190"),
    ("cross-site scripting", "T1059.007"), ("xss", "T1059.007"),
    ("remote code execution", "T1190"), ("rce", "T1190"),
    ("command injection", "T1190"), ("deserial", "T1190"),
    ("subdomain takeover", "T1584"), ("takeover", "T1584"),
    ("path traversal", "T1083"), ("directory traversal", "T1083"),
    ("local file inclusion", "T1083"), ("lfi", "T1083"),
    ("brute force", "T1110"),
    ("default password", "T1078"), ("default login", "T1078"),
    ("default credential", "T1078"), ("weak password", "T1078"),
    (".git", "T1213.003"), ("source code exposure", "T1213.003"),
    ("api key", "T1552.001"), ("secret", "T1552.001"),
    (".env", "T1552.001"), ("private key", "T1552.001"),
    ("credentials in", "T1552.001"),
    ("ssl", "T1557"), ("tls", "T1557"), ("cipher", "T1557"), ("certificate", "T1557"),
    ("open port", "T1046"),
    ("subdomain:", "T1590"),
    ("cors", "T1190"),
    ("security header", "T1595.002"), ("missing header", "T1595.002"),
]

# Short tokens that must match on word boundaries — otherwise "rce" matches
# "sou[rce]" / "b[r]ute fo[rce]", "ssl" matches unrelated strings, etc.
_AMBIGUOUS = {"rce", "xss", "sqli", "lfi", "ssl", "tls", "cors"}
_WORD_RE = {kw: re.compile(rf"\b{re.escape(kw)}\b") for kw in _AMBIGUOUS}


def classify(
    title: str = "",
    description: str = "",
    tags: Optional[List[str]] = None,
    cve: Optional[str] = None,
    plugin: Optional[str] = None,
) -> Tuple[str, str, str]:
    """Return (technique_id, name, tactic) for a finding."""
    text = " ".join([
        (title or "").lower(),
        (description or "").lower(),
        " ".join(t.lower() for t in (tags or [])),
    ])

    tid = None
    for needle, technique in KEYWORD_RULES:
        matched = _WORD_RE[needle].search(text) if needle in _AMBIGUOUS else (needle in text)
        if matched:
            tid = technique
            break

    if tid is None and cve:
        tid = "T1190"  # a CVE on a public asset ⇒ exploit public-facing app
    if tid is None:
        tid = PLUGIN_DEFAULT.get(plugin or "", "T1190")

    meta = TECHNIQUES.get(tid, {"name": "Exploit Public-Facing Application", "tactic": "Initial Access"})
    return tid, meta["name"], meta["tactic"]


def _mitre_block(tid: str, name: str, tactic: str) -> Dict[str, str]:
    return {"id": tid, "name": name, "tactic": tactic}


def annotate_dict(plugin: str, fd: Dict[str, Any]) -> Dict[str, Any]:
    """Tag a finding-data dict (as produced by parsers) in place, before insert."""
    ev = fd.get("evidence") or {}
    tid, name, tactic = classify(
        title=fd.get("title", ""),
        description=fd.get("description", ""),
        tags=ev.get("tags"),
        cve=fd.get("cve_id"),
        plugin=plugin,
    )
    fd["mitre_technique"] = tid
    ev = dict(ev)
    ev["mitre"] = _mitre_block(tid, name, tactic)
    fd["evidence"] = ev
    return fd


def annotate_orm(finding, plugin: Optional[str] = None) -> bool:
    """Tag a persisted Finding ORM object. Returns True if it was changed."""
    ev = dict(finding.evidence or {})
    if finding.mitre_technique and isinstance(ev.get("mitre"), dict):
        return False  # already tagged with metadata
    tid, name, tactic = classify(
        title=finding.title or "",
        description=finding.description or "",
        tags=ev.get("tags"),
        cve=finding.cve_id,
        plugin=plugin,
    )
    finding.mitre_technique = tid
    ev["mitre"] = _mitre_block(tid, name, tactic)
    finding.evidence = ev  # reassign so SQLAlchemy tracks the JSON change
    return True
