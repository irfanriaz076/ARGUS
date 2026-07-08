import asyncio
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PluginResult:
    raw_output: str = ""
    findings: List[Dict[str, Any]] = field(default_factory=list)


class BasePlugin(ABC):
    name: str = ""
    stage: str = ""
    supported_target_types: List[str] = []

    def supports_target(self, target_type: str) -> bool:
        return target_type in self.supported_target_types

    @abstractmethod
    async def run(self, target: str, target_type: str, publish: Callable) -> PluginResult:
        pass

    async def execute_command(
        self, cmd: List[str], publish: Callable
    ) -> str:
        publish(f"[{self.name}] Running: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        output_lines = []
        async for line in process.stdout:
            decoded = line.decode(errors="replace").rstrip()
            output_lines.append(decoded)
            publish(decoded)

        await process.wait()
        return "\n".join(output_lines)


class PluginRegistry:
    _plugins: Dict[str, BasePlugin] = {}

    def __init__(self):
        self._load_plugins()

    def _load_plugins(self):
        from backend.plugins.enumeration.nmap_scanner import NmapScanner
        from backend.plugins.enumeration.ffuf_fuzzer import FfufFuzzerPlugin
        from backend.plugins.recon.subfinder import SubfinderPlugin
        from backend.plugins.recon.httpx_probe import HttpxProbePlugin
        from backend.plugins.recon.gowitness_screenshot import GoWitnessPlugin
        from backend.plugins.vulnerability.nuclei_scanner import NucleiScannerPlugin
        from backend.plugins.exploitation.nikto_scanner import NiktoScannerPlugin
        from backend.plugins.exploitation.sqlmap_scanner import SQLMapScannerPlugin
        from backend.plugins.exploitation.git_exposure import GitExposurePlugin
        from backend.plugins.exploitation.dalfox_scanner import DalfoxScannerPlugin
        from backend.plugins.exploitation.wpscan_lite import WPScanLitePlugin
        from backend.plugins.recon.crtsh_enum import CrtShEnumPlugin
        from backend.plugins.recon.shodan_lookup import ShodanLookupPlugin
        from backend.plugins.recon.github_dorking import GitHubDorkingPlugin
        from backend.plugins.recon.whois_asn import WhoisAsnPlugin
        from backend.plugins.post_exploitation.testssl_scanner import TestSSLScannerPlugin
        from backend.plugins.post_exploitation.hydra_brute import HydraBrutePlugin
        from backend.plugins.post_exploitation.sensitive_files import SensitiveFilesPlugin
        from backend.plugins.post_exploitation.header_analyzer import HeaderAnalyzerPlugin
        from backend.plugins.post_exploitation.cors_tester import CorsTesterPlugin

        for plugin_cls in [
            SubfinderPlugin,
            HttpxProbePlugin,
            GoWitnessPlugin,
            CrtShEnumPlugin,
            ShodanLookupPlugin,
            GitHubDorkingPlugin,
            WhoisAsnPlugin,
            NmapScanner,
            FfufFuzzerPlugin,
            NucleiScannerPlugin,
            NiktoScannerPlugin,
            SQLMapScannerPlugin,
            GitExposurePlugin,
            DalfoxScannerPlugin,
            WPScanLitePlugin,
            TestSSLScannerPlugin,
            HydraBrutePlugin,
            SensitiveFilesPlugin,
            HeaderAnalyzerPlugin,
            CorsTesterPlugin,
        ]:
            plugin = plugin_cls()
            self._plugins[plugin.name] = plugin

    def get(self, name: str) -> Optional[BasePlugin]:
        return self._plugins.get(name)

    def get_plugins_for_stage(self, stage: str) -> List[BasePlugin]:
        return [p for p in self._plugins.values() if p.stage == stage]

    def all(self) -> List[BasePlugin]:
        return list(self._plugins.values())
