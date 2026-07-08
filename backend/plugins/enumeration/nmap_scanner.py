import os
from typing import Any, Callable, Dict, List

from backend.config import settings
from backend.parsers.nmap_parser import parse_nmap_xml
from backend.plugins.base_plugin import BasePlugin, PluginResult


class NmapScanner(BasePlugin):
    name = "nmap_scanner"
    stage = "enumeration"
    supported_target_types = ["ip", "domain", "cidr"]

    async def run(self, target: str, target_type: str, publish: Callable) -> PluginResult:
        os.makedirs(settings.TMP_DIR, exist_ok=True)
        safe_target = target.replace("/", "_").replace(":", "_")
        xml_path = os.path.join(settings.TMP_DIR, f"nmap_{safe_target}.xml")

        cmd = [
            "nmap",
            "-sV",
            "-sC",
            "-T4",
            "--open",
            "-oX", xml_path,
            target,
        ]

        raw_output = await self.execute_command(cmd, publish)

        findings = []
        if os.path.exists(xml_path):
            findings = parse_nmap_xml(xml_path, target)
            try:
                os.remove(xml_path)
            except OSError:
                pass

        return PluginResult(raw_output=raw_output, findings=findings)
