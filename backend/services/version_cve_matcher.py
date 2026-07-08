"""
Match nmap service versions to known CVEs via NVD keyword search.
Creates new CVE findings from version strings like "Apache httpd 2.4.7".
"""
import re
import time
from typing import Any, Dict, List, Optional

import httpx

from backend.config import settings

_NVD_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_VERSION_RE = re.compile(r'(\d+\.\d+[\.\d]*)')

# service name keyword → (vendor label, product label for search)
_PRODUCT_MAP = {
    "apache":      "Apache HTTP Server",
    "httpd":       "Apache HTTP Server",
    "nginx":       "nginx",
    "openssh":     "OpenSSH",
    "openssl":     "OpenSSL",
    "mysql":       "MySQL",
    "mariadb":     "MariaDB",
    "postgresql":  "PostgreSQL",
    "redis":       "Redis",
    "tomcat":      "Apache Tomcat",
    "iis":         "Microsoft IIS",
    "php":         "PHP",
    "vsftpd":      "vsftpd",
    "proftpd":     "ProFTPD",
    "samba":       "Samba",
    "sendmail":    "Sendmail",
    "postfix":     "Postfix",
    "exim":        "Exim",
    "dovecot":     "Dovecot",
    "bind":        "ISC BIND",
    "lighttpd":    "lighttpd",
    "wordpress":   "WordPress",
    "drupal":      "Drupal",
    "joomla":      "Joomla",
    "jenkins":     "Jenkins",
    "gitlab":      "GitLab",
    "grafana":     "Grafana",
    "elasticsearch": "Elasticsearch",
    "kibana":      "Kibana",
    "mongodb":     "MongoDB",
    "memcached":   "Memcached",
    "rabbitmq":    "RabbitMQ",
    "busybox":     "BusyBox",
}

MITRE_MAP = {
    "apache": "T1190", "nginx": "T1190", "openssh": "T1110",
    "openssl": "T1190", "php": "T1190", "wordpress": "T1190",
    "mysql": "T1190", "postgresql": "T1190", "redis": "T1190",
    "tomcat": "T1190", "iis": "T1190",
}


def _clean_version(version_str: str) -> Optional[str]:
    m = _VERSION_RE.search(version_str)
    return m.group(1) if m else None


def _identify_product(service: str, version_str: str) -> Optional[str]:
    combined = f"{service} {version_str}".lower()
    for keyword, label in _PRODUCT_MAP.items():
        if keyword in combined:
            return label
    return None


def _search_nvd_keyword(product_label: str, version: str) -> List[Dict[str, Any]]:
    headers = {"apiKey": settings.NVD_API_KEY} if settings.NVD_API_KEY else {}
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(_NVD_BASE, params={
                "keywordSearch": f"{product_label} {version}",
                "resultsPerPage": 8,
                "noRejected": "",
            }, headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return []

    results = []
    for vuln in data.get("vulnerabilities", []):
        cve_obj = vuln.get("cve", {})
        cve_id = cve_obj.get("id", "")
        if not cve_id:
            continue

        desc = next(
            (d["value"] for d in cve_obj.get("descriptions", []) if d.get("lang") == "en"),
            "",
        )

        score, vector, sev = None, "", "medium"
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            entries = cve_obj.get("metrics", {}).get(key, [])
            primary = next((e for e in entries if e.get("type") == "Primary"),
                           entries[0] if entries else None)
            if primary:
                cd = primary.get("cvssData", {})
                score  = cd.get("baseScore")
                vector = cd.get("vectorString", "")
                sev    = cd.get("baseSeverity", "MEDIUM").lower()
                break

        if score and score < 4.0:
            continue  # skip low/info

        results.append({
            "cve_id":      cve_id,
            "description": desc[:600],
            "cvss_score":  float(score) if score else None,
            "cvss_vector": vector,
            "severity":    sev,
            "published":   cve_obj.get("published", "")[:10],
        })

    return results


def match_findings_to_cves(
    findings: List[Any],
    existing_cve_ids: set,
) -> List[Dict[str, Any]]:
    """
    Given a list of open-port Finding ORM objects, search NVD for CVEs
    matching each discovered service version. Returns new finding dicts
    ready to be inserted.
    """
    new_findings: List[Dict[str, Any]] = []
    seen: set = set(existing_cve_ids)
    delay = 0.7 if settings.NVD_API_KEY else 6.5

    for finding in findings:
        ev = finding.evidence or {}
        service = ev.get("service", "")
        version = ev.get("version", "")
        if not service or not version:
            continue

        product_label = _identify_product(service, version)
        if not product_label:
            continue

        clean_ver = _clean_version(version)
        if not clean_ver:
            continue

        cves = _search_nvd_keyword(product_label, clean_ver)
        time.sleep(delay)

        for cve in cves[:4]:
            if cve["cve_id"] in seen:
                continue
            seen.add(cve["cve_id"])

            mitre = next(
                (v for k, v in MITRE_MAP.items() if k in service.lower()),
                "T1190",
            )

            new_findings.append({
                "title":           f"{cve['cve_id']} — {product_label} {clean_ver}",
                "severity":        cve["severity"],
                "cvss_score":      cve["cvss_score"],
                "cve_id":          cve["cve_id"],
                "description":     cve["description"],
                "mitre_technique": mitre,
                "evidence": {
                    "ip":              ev.get("ip", ""),
                    "port":            ev.get("port", ""),
                    "service":         service,
                    "version":         version,
                    "matched_version": clean_ver,
                    "product":         product_label,
                    "cvss_vector":     cve["cvss_vector"],
                    "published":       cve["published"],
                    "source":          "version_cve_match",
                },
            })

    return new_findings
