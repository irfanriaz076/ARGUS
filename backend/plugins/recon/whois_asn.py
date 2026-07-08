"""
WHOIS + ASN + IP geolocation passive OSINT plugin.
- Domain: whois registration data (registrar, dates, nameservers, org)
- IP: BGPView.io for ASN/prefix, ipinfo.io for geo/org
No API keys required for BGPView or ipinfo free tier.
"""
import asyncio
import re
import shutil
from typing import Callable

import httpx

from backend.plugins.base_plugin import BasePlugin, PluginResult

_WHOIS_FIELDS = {
    "registrar":          re.compile(r"Registrar:\s*(.+)", re.I),
    "creation_date":      re.compile(r"Creation Date:\s*(.+)", re.I),
    "expiry_date":        re.compile(r"(?:Registrar Registration Expiration Date|Registry Expiry Date):\s*(.+)", re.I),
    "updated_date":       re.compile(r"Updated Date:\s*(.+)", re.I),
    "registrant_org":     re.compile(r"Registrant Organization:\s*(.+)", re.I),
    "registrant_country": re.compile(r"Registrant Country:\s*(.+)", re.I),
    "name_servers":       re.compile(r"Name Server:\s*(.+)", re.I),
    "dnssec":             re.compile(r"DNSSEC:\s*(.+)", re.I),
    "status":             re.compile(r"Domain Status:\s*(.+)", re.I),
}


def _parse_whois(raw: str) -> dict:
    result = {}
    for field, pattern in _WHOIS_FIELDS.items():
        matches = pattern.findall(raw)
        if matches:
            # Multi-value fields
            if field in ("name_servers", "status"):
                result[field] = [m.strip().lower() for m in matches]
            else:
                result[field] = matches[0].strip()
    return result


class WhoisAsnPlugin(BasePlugin):
    name = "whois_asn"
    stage = "recon"
    supported_target_types = ["domain", "ip"]

    async def run(self, target: str, target_type: str, publish: Callable) -> PluginResult:
        findings = []
        raw_parts = []

        if target_type == "domain":
            findings += await self._domain_whois(target, publish, raw_parts)
        else:
            findings += await self._ip_intel(target, publish, raw_parts)

        publish(f"[whois_asn] {len(findings)} finding(s) for {target}")
        return PluginResult(raw_output="\n".join(raw_parts), findings=findings)

    # ── Domain WHOIS ────────────────────────────────────────────────────
    async def _domain_whois(self, domain: str, publish: Callable, raw_parts: list) -> list:
        findings = []

        # Prefer system whois command
        whois_raw = ""
        if shutil.which("whois"):
            loop = asyncio.get_event_loop()
            proc = await asyncio.create_subprocess_exec(
                "whois", domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
            whois_raw = stdout.decode(errors="replace")
        else:
            # Fallback: RDAP API (no system tool needed)
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.get(f"https://rdap.org/domain/{domain}")
                    whois_raw = r.text
            except Exception:
                pass

        raw_parts.append(whois_raw[:3000])
        parsed = _parse_whois(whois_raw)
        if not parsed:
            publish(f"[whois_asn] No WHOIS data for {domain}")
            return findings

        publish(f"[whois_asn] WHOIS: {domain} registered via {parsed.get('registrar', 'unknown')}")

        # Security flag: check expiry proximity
        severity = "info"
        desc_extra = ""
        expiry = parsed.get("expiry_date", "")
        if expiry:
            try:
                from datetime import datetime, timezone
                exp_dt = datetime.fromisoformat(expiry.split("T")[0])
                days_left = (exp_dt - datetime.now()).days
                if days_left < 30:
                    severity = "high"
                    desc_extra = f" WARNING: domain expires in {days_left} days!"
                elif days_left < 90:
                    severity = "medium"
                    desc_extra = f" Note: domain expires in {days_left} days."
            except Exception:
                pass

        findings.append({
            "title":    f"WHOIS: {domain} — {parsed.get('registrant_org', 'unknown registrant')}",
            "severity": severity,
            "description": (
                f"Domain '{domain}' registered via {parsed.get('registrar', 'unknown')}. "
                f"Created: {parsed.get('creation_date', 'unknown')}. "
                f"Expires: {expiry or 'unknown'}. "
                f"Registrant: {parsed.get('registrant_org', 'unknown')} ({parsed.get('registrant_country', '')}).{desc_extra}"
            ),
            "evidence": {
                "domain":             domain,
                "registrar":          parsed.get("registrar"),
                "creation_date":      parsed.get("creation_date"),
                "expiry_date":        expiry,
                "registrant_org":     parsed.get("registrant_org"),
                "registrant_country": parsed.get("registrant_country"),
                "name_servers":       parsed.get("name_servers", []),
                "dnssec":             parsed.get("dnssec"),
                "status":             parsed.get("status", []),
                "source":             "whois",
            },
            "mitre_technique": "T1590.001",
        })

        return findings

    # ── IP ASN + geo ─────────────────────────────────────────────────────
    async def _ip_intel(self, ip: str, publish: Callable, raw_parts: list) -> list:
        findings = []

        async with httpx.AsyncClient(timeout=12) as client:
            # BGPView: ASN + prefix
            asn_data, geo_data = {}, {}
            try:
                r1 = await client.get(
                    f"https://api.bgpview.io/ip/{ip}",
                    headers={"User-Agent": "ARGUS-PTaaS/1.0"},
                )
                if r1.status_code == 200:
                    asn_data = r1.json().get("data", {})
                    raw_parts.append(r1.text[:1000])
            except Exception:
                pass

            # ipinfo: geo + org
            try:
                r2 = await client.get(
                    f"https://ipinfo.io/{ip}/json",
                    headers={"User-Agent": "ARGUS-PTaaS/1.0"},
                )
                if r2.status_code == 200:
                    geo_data = r2.json()
                    raw_parts.append(r2.text[:500])
            except Exception:
                pass

        prefixes = asn_data.get("prefixes", [])
        asns     = [p.get("asn", {}) for p in prefixes]
        asn_nums = list({a.get("asn") for a in asns if a.get("asn")})
        asn_orgs = list({a.get("description", "") for a in asns if a.get("description")})
        netblocks = [p.get("prefix", "") for p in prefixes]

        org     = geo_data.get("org", "") or ", ".join(asn_orgs[:2])
        country = geo_data.get("country", asn_data.get("country_code", ""))
        city    = geo_data.get("city", "")
        region  = geo_data.get("region", "")
        hostname = geo_data.get("hostname", "")

        publish(f"[whois_asn] IP {ip}: ASN {asn_nums} | Org: {org} | {city}, {country}")

        # Check if hosting/cloud provider (common for exposed infra)
        cloud_keywords = ["amazon", "aws", "google", "azure", "digitalocean", "vultr", "linode", "cloudflare", "hetzner"]
        is_cloud = any(kw in org.lower() for kw in cloud_keywords)

        findings.append({
            "title":    f"IP Intel: {ip} — {org or 'unknown'} ({country})",
            "severity": "info",
            "description": (
                f"IP {ip} belongs to {org or 'unknown'} in {city or region or ''}, {country}. "
                f"ASN: {', '.join(str(a) for a in asn_nums) or 'unknown'}. "
                f"Netblocks: {', '.join(netblocks[:3]) or 'unknown'}. "
                f"Hostname: {hostname or 'none'}. "
                f"{'Cloud/hosting provider detected.' if is_cloud else ''}"
            ),
            "evidence": {
                "ip":        ip,
                "org":       org,
                "country":   country,
                "city":      city,
                "region":    region,
                "hostname":  hostname,
                "asn":       asn_nums,
                "netblocks": netblocks[:5],
                "is_cloud":  is_cloud,
                "source":    "whois_asn",
            },
            "mitre_technique": "T1590.005",
        })

        return findings
