import os
from typing import Callable

from backend.config import settings
from backend.parsers.httpx_parser import parse_httpx_output
from backend.plugins.base_plugin import BasePlugin, PluginResult

# httpx only probes 80/443 by default. Many real services (this project's own
# Docker-based test targets included) run on non-standard ports, so for bare
# domain/ip targets we feed httpx an explicit candidate list instead — this is
# what lets recon actually discover e.g. an app on :3000 instead of silently
# finding nothing and leaving every downstream plugin blind to it.
COMMON_PORTS = [80, 443, 3000, 3001, 8000, 8080, 8443, 8888, 5000, 9000, 4200]


class HttpxProbePlugin(BasePlugin):
    name = "httpx_probe"
    stage = "recon"
    supported_target_types = ["domain", "ip", "url"]

    async def run(self, target: str, target_type: str, publish: Callable) -> PluginResult:
        list_path = None
        if target_type in ("domain", "ip") and not target.startswith("http"):
            os.makedirs(settings.TMP_DIR, exist_ok=True)
            safe = target.replace("/", "_").replace(":", "_")
            list_path = os.path.join(settings.TMP_DIR, f"httpx_targets_{safe}.txt")
            with open(list_path, "w") as f:
                f.write("\n".join(f"{target}:{p}" for p in COMMON_PORTS))
            target_arg = ["-l", list_path]
        else:
            target_arg = ["-u", target]

        cmd = [
            "pd-httpx",
            *target_arg,
            "-silent",
            "-json",
            "-title",
            "-tech-detect",
            "-status-code",
            "-content-length",
            "-web-server",
            "-timeout", "15",
            "-retries", "2",
        ]

        try:
            raw = await self.execute_command(cmd, publish)
        finally:
            if list_path and os.path.exists(list_path):
                try:
                    os.remove(list_path)
                except OSError:
                    pass

        findings = parse_httpx_output(raw, target)
        publish(f"[httpx] {len(findings)} live service(s) detected for {target}")
        return PluginResult(raw_output=raw, findings=findings)
