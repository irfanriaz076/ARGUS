"""
Certificate Transparency subdomain enumeration via crt.sh.
Finds subdomains that never appear in active DNS but were issued TLS certificates —
useful for discovering forgotten/shadow infra the client may not know exists.
"""
import asyncio
from typing import Callable

import httpx

from backend.plugins.base_plugin import BasePlugin, PluginResult


def _root_domain(domain: str) -> str:
    parts = domain.rstrip(".").split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else domain


class CrtShEnumPlugin(BasePlugin):
    name = "crtsh_enum"
    stage = "recon"
    supported_target_types = ["domain"]

    async def run(self, target: str, target_type: str, publish: Callable) -> PluginResult:
        root = _root_domain(target)
        publish(f"[crtsh] Querying certificate transparency for *.{root}")

        raw_text = ""
        entries = []
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                r = await client.get(
                    "https://crt.sh/",
                    params={"q": f"%.{root}", "output": "json", "deduplicate": "Y"},
                    headers={"User-Agent": "ARGUS-PTaaS/1.0"},
                )
                raw_text = r.text
                if r.status_code == 200:
                    entries = r.json()
        except Exception as e:
            publish(f"[crtsh] Request failed: {e}")
            return PluginResult(raw_output=str(e), findings=[])

        seen: set[str] = set()
        findings = []
        for entry in entries:
            for name in entry.get("name_value", "").split("\n"):
                name = name.strip().lower().lstrip("*.")
                if not name or name in seen:
                    continue
                if not name.endswith(root):
                    continue
                seen.add(name)

                issued_to   = entry.get("common_name", name)
                issuer      = entry.get("issuer_name", "")
                logged_at   = entry.get("entry_timestamp", "")

                findings.append({
                    "title": f"Subdomain: {name}",
                    "severity": "info",
                    "description": (
                        f"Subdomain '{name}' discovered via TLS certificate transparency logs (crt.sh). "
                        f"Certificate issued to: {issued_to}. Issuer: {issuer}."
                    ),
                    "evidence": {
                        "subdomain":   name,
                        "root_domain": root,
                        "cert_cn":     issued_to,
                        "issuer":      issuer,
                        "logged_at":   logged_at,
                        "source":      "crtsh",
                    },
                    "mitre_technique": "T1596",
                })

        publish(f"[crtsh] {len(findings)} unique subdomain(s) from cert logs for {root}")
        return PluginResult(raw_output=raw_text[:4000], findings=findings)
