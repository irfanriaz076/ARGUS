"""
gowitness screenshot plugin.
Takes a screenshot of a live web service and saves it to /tmp/argus/screenshots/.
"""
import os
from typing import Callable

from backend.config import settings
from backend.plugins.base_plugin import BasePlugin, PluginResult

SCREENSHOT_DIR = "/tmp/argus/screenshots"


class GoWitnessPlugin(BasePlugin):
    name = "gowitness_screenshot"
    stage = "recon"
    supported_target_types = ["domain", "ip", "url"]

    async def run(self, target: str, target_type: str, publish: Callable) -> PluginResult:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)

        urls = (
            [f"http://{target}", f"https://{target}"]
            if target_type in ("domain", "ip") and not target.startswith("http")
            else [target]
        )

        findings = []
        for url in urls:
            safe = url.replace("://", "_").replace("/", "_").replace(":", "_")
            out_path = os.path.join(SCREENSHOT_DIR, f"{safe}.png")

            cmd = [
                "gowitness",
                "single",
                "--url", url,
                "--screenshot-path", out_path,
                "--timeout", "15",
                "--disable-db",
                "--chrome-path", "/usr/bin/chromium",
            ]

            raw = await self.execute_command(cmd, publish)

            if os.path.exists(out_path):
                publish(f"[gowitness] Screenshot saved: {out_path}")
                findings.append({
                    "title": f"Screenshot: {url}",
                    "severity": "info",
                    "description": f"Visual screenshot captured for {url}",
                    "evidence": {
                        "url": url,
                        "screenshot_path": out_path,
                        "screenshot_url": f"/api/screenshots/{safe}.png",
                    },
                    "mitre_technique": "T1593",
                })
            else:
                publish(f"[gowitness] No screenshot for {url}")

        return PluginResult(raw_output="", findings=findings)
