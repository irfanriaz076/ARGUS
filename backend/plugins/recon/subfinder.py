from typing import Callable

from backend.parsers.subfinder_parser import parse_subfinder_output
from backend.plugins.base_plugin import BasePlugin, PluginResult


class SubfinderPlugin(BasePlugin):
    name = "subfinder"
    stage = "recon"
    supported_target_types = ["domain"]

    async def run(self, target: str, target_type: str, publish: Callable) -> PluginResult:
        cmd = [
            "subfinder",
            "-d", target,
            "-all",
            "-silent",
            "-json",
            "-timeout", "30",
        ]

        raw = await self.execute_command(cmd, publish)
        findings = parse_subfinder_output(raw, target)
        publish(f"[subfinder] {len(findings)} subdomain(s) found for {target}")
        return PluginResult(raw_output=raw, findings=findings)
