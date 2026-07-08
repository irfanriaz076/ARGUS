"""
Shodan host intelligence plugin.
- IP target: full host report (ports, banners, CVEs, ISP, geo)
- Domain target: finds all IPs associated with the hostname
Requires SHODAN_API_KEY env var; gracefully skips if absent.
"""
import asyncio
import socket
from typing import Callable

from backend.config import settings
from backend.plugins.base_plugin import BasePlugin, PluginResult

SEVERITY_MAP = {
    "critical": "critical",
    "high":     "high",
    "medium":   "medium",
    "low":      "low",
}


def _resolve_ip(domain: str) -> str | None:
    try:
        return socket.gethostbyname(domain)
    except Exception:
        return None


def _cvss_to_severity(score: float | None) -> str:
    if not score:
        return "info"
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    return "low"


class ShodanLookupPlugin(BasePlugin):
    name = "shodan_lookup"
    stage = "recon"
    supported_target_types = ["domain", "ip"]

    async def run(self, target: str, target_type: str, publish: Callable) -> PluginResult:
        if not settings.SHODAN_API_KEY:
            publish("[shodan] SHODAN_API_KEY not configured — skipping")
            return PluginResult(raw_output="no api key", findings=[])

        try:
            import shodan as shodan_lib
        except ImportError:
            publish("[shodan] shodan package not installed")
            return PluginResult(raw_output="shodan not installed", findings=[])

        api = shodan_lib.Shodan(settings.SHODAN_API_KEY)
        loop = asyncio.get_event_loop()
        findings = []
        raw_parts = []

        # Resolve domain → IP
        if target_type == "domain":
            ip = await loop.run_in_executor(None, _resolve_ip, target)
            if not ip:
                publish(f"[shodan] Could not resolve {target}")
                return PluginResult(raw_output="dns fail", findings=[])
            publish(f"[shodan] {target} resolves to {ip}")
        else:
            ip = target

        # ── Host lookup ─────────────────────────────────────────────────
        try:
            host = await loop.run_in_executor(None, api.host, ip)
        except shodan_lib.APIError as e:
            publish(f"[shodan] API error: {e}")
            return PluginResult(raw_output=str(e), findings=[])

        raw_parts.append(f"Shodan host report for {ip}")
        org      = host.get("org", "unknown")
        isp      = host.get("isp", "unknown")
        country  = host.get("country_name", "unknown")
        city     = host.get("city", "")
        asn      = host.get("asn", "")
        hostnames = host.get("hostnames", [])
        tags      = host.get("tags", [])
        os_info   = host.get("os", "")
        last_update = host.get("last_update", "")

        publish(f"[shodan] Host: {ip} | Org: {org} | Country: {country} | ASN: {asn}")

        # Infrastructure finding
        open_ports = [str(d.get("port", "")) for d in host.get("data", [])]
        findings.append({
            "title": f"Shodan Host Profile: {ip} ({org})",
            "severity": "info",
            "description": (
                f"Shodan host report for {ip}. "
                f"Organisation: {org} ({isp}). Location: {city}, {country}. "
                f"ASN: {asn}. Open ports: {', '.join(open_ports) or 'none detected'}. "
                f"OS: {os_info or 'unknown'}. Hostnames: {', '.join(hostnames[:5]) or 'none'}."
            ),
            "evidence": {
                "ip":          ip,
                "org":         org,
                "isp":         isp,
                "country":     country,
                "city":        city,
                "asn":         asn,
                "open_ports":  open_ports,
                "hostnames":   hostnames,
                "os":          os_info,
                "tags":        tags,
                "last_update": last_update,
                "source":      "shodan",
            },
            "mitre_technique": "T1596.005",
        })

        # Per-port service banners
        for svc in host.get("data", []):
            port     = svc.get("port")
            proto    = svc.get("transport", "tcp")
            product  = svc.get("product", "")
            version  = svc.get("version", "")
            banner   = svc.get("data", "")[:300]
            cpe_list = svc.get("cpe", [])

            if not port:
                continue

            findings.append({
                "title": f"Shodan Service: {ip}:{port}/{proto} — {product or 'unknown'} {version}".strip(),
                "severity": "info",
                "description": f"Service banner captured by Shodan on port {port}/{proto}.",
                "evidence": {
                    "ip":      ip,
                    "port":    port,
                    "proto":   proto,
                    "product": product,
                    "version": version,
                    "banner":  banner,
                    "cpe":     cpe_list,
                    "source":  "shodan",
                },
                "mitre_technique": "T1596.005",
            })

        # Known CVEs from Shodan
        for cve_id, cve_data in host.get("vulns", {}).items():
            cvss  = cve_data.get("cvss", 0.0)
            sev   = _cvss_to_severity(cvss)
            refs  = cve_data.get("references", [])
            findings.append({
                "title":       f"Shodan CVE: {cve_id} on {ip}",
                "severity":    sev,
                "cvss_score":  float(cvss) if cvss else None,
                "cve_id":      cve_id,
                "description": cve_data.get("summary", f"Shodan reports {cve_id} on {ip}."),
                "evidence": {
                    "ip":         ip,
                    "references": refs,
                    "cvss":       cvss,
                    "source":     "shodan",
                },
                "mitre_technique": "T1190",
            })

        publish(f"[shodan] {len(findings)} finding(s) for {ip}")
        return PluginResult(raw_output="\n".join(raw_parts), findings=findings)
