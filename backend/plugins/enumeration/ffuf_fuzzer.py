import os
from typing import Callable

from backend.config import settings
from backend.parsers.ffuf_parser import parse_ffuf_output
from backend.plugins.base_plugin import BasePlugin, PluginResult

WORDLIST_CANDIDATES = [
    "/usr/share/seclists/Discovery/Web-Content/common.txt",
    "/usr/share/wordlists/dirb/common.txt",
    "/app/backend/wordlists/common.txt",
    os.path.join(os.path.dirname(__file__), "../../wordlists/common.txt"),
]


class FfufFuzzerPlugin(BasePlugin):
    name = "ffuf_fuzzer"
    stage = "enumeration"
    supported_target_types = ["domain", "ip", "url"]

    def _wordlist(self) -> str | None:
        for path in WORDLIST_CANDIDATES:
            resolved = os.path.realpath(path)
            if os.path.exists(resolved):
                return resolved
        return None

    async def run(self, target: str, target_type: str, publish: Callable) -> PluginResult:
        wordlist = self._wordlist()
        if not wordlist:
            publish("[ffuf] No wordlist found — skipping directory fuzzing")
            return PluginResult(raw_output="wordlist not found", findings=[])

        if target_type in ("domain", "ip") and not target.startswith("http"):
            base_url = f"http://{target}"
        else:
            base_url = target.rstrip("/")

        os.makedirs(settings.TMP_DIR, exist_ok=True)
        safe = target.replace("/", "_").replace(":", "_").replace(".", "_")
        out_path = os.path.join(settings.TMP_DIR, f"ffuf_{safe}.json")

        cmd = [
            "ffuf",
            "-u", f"{base_url}/FUZZ",
            "-w", wordlist,
            "-mc", "200,301,302,401,403",
            "-o", out_path,
            "-of", "json",
            "-t", "40",
            "-timeout", "10",
            "-silent",
        ]

        raw_stdout = await self.execute_command(cmd, publish)

        findings = []
        if os.path.exists(out_path):
            with open(out_path) as f:
                json_content = f.read()
            findings = parse_ffuf_output(json_content, base_url)
            try:
                os.remove(out_path)
            except OSError:
                pass

        publish(f"[ffuf] {len(findings)} endpoint(s) discovered on {base_url}")
        return PluginResult(raw_output=raw_stdout, findings=findings)
