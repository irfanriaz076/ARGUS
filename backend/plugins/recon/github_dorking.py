"""
GitHub OSINT dorking plugin.
Searches GitHub's code search API for exposed credentials, API keys,
and sensitive configuration tied to the target domain.
Rate-limited: 10 req/min unauthenticated, 30 req/min with GITHUB_TOKEN.
"""
import asyncio
from typing import Callable

import httpx

from backend.config import settings
from backend.plugins.base_plugin import BasePlugin, PluginResult

# (query_suffix, severity, description_template)
DORK_TEMPLATES = [
    ('password',                "high",     "Password exposure"),
    ('api_key OR apikey',       "critical", "API key exposure"),
    ('secret OR secret_key',    "critical", "Secret/key exposure"),
    ('access_token',            "critical", "Access token exposure"),
    ('private_key OR pem',      "critical", "Private key exposure"),
    ('credentials OR username', "high",     "Credential exposure"),
    ('database_url OR db_pass', "critical", "Database credential exposure"),
    ('smtp_password',           "high",     "SMTP credential exposure"),
]


class GitHubDorkingPlugin(BasePlugin):
    name = "github_dorking"
    stage = "recon"
    supported_target_types = ["domain"]

    async def run(self, target: str, target_type: str, publish: Callable) -> PluginResult:
        token   = settings.GITHUB_TOKEN
        delay_s = 2.2 if token else 7.0
        headers = {
            "Accept":     "application/vnd.github.v3+json",
            "User-Agent": "ARGUS-PTaaS/1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        publish(f"[github_dorking] Searching GitHub for credentials related to '{target}'")

        findings = []
        seen_repos: set[str] = set()
        raw_lines = []

        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            for suffix, severity, desc_prefix in DORK_TEMPLATES:
                query = f'"{target}" {suffix}'
                try:
                    r = await client.get(
                        "https://api.github.com/search/code",
                        params={"q": query, "per_page": 5, "sort": "indexed"},
                    )
                except Exception as e:
                    publish(f"[github_dorking] Request error: {e}")
                    await asyncio.sleep(delay_s)
                    continue

                if r.status_code == 403:
                    publish(f"[github_dorking] Rate-limited — pausing 60s")
                    await asyncio.sleep(60)
                    continue
                if r.status_code != 200:
                    await asyncio.sleep(delay_s)
                    continue

                data   = r.json()
                items  = data.get("items", [])
                total  = data.get("total_count", 0)
                raw_lines.append(f"Query '{query}' → {total} result(s)")

                for item in items:
                    repo_name = item.get("repository", {}).get("full_name", "unknown")
                    file_name = item.get("name", "")
                    file_path = item.get("path", "")
                    html_url  = item.get("html_url", "")
                    repo_desc = item.get("repository", {}).get("description") or ""
                    repo_url  = item.get("repository", {}).get("html_url", "")

                    key = f"{repo_name}:{file_path}"
                    if key in seen_repos:
                        continue
                    seen_repos.add(key)

                    publish(f"[github_dorking] {severity.upper()} — {desc_prefix} in {repo_name}/{file_path}")

                    findings.append({
                        "title":       f"GitHub: {desc_prefix} in {repo_name}",
                        "severity":    severity,
                        "description": (
                            f"{desc_prefix} found in public GitHub repository '{repo_name}'. "
                            f"File: {file_path}. Search query: '{query}'. "
                            f"Total matches on GitHub: {total}."
                        ),
                        "evidence": {
                            "repository":  repo_name,
                            "repo_url":    repo_url,
                            "file":        file_name,
                            "file_path":   file_path,
                            "file_url":    html_url,
                            "query":       query,
                            "total_count": total,
                            "repo_desc":   repo_desc[:200],
                            "proof":       f"Public GitHub file '{file_path}' in '{repo_name}' matches '{query}'",
                            "source":      "github_dorking",
                        },
                        "mitre_technique": "T1213.003",
                    })

                await asyncio.sleep(delay_s)

        publish(f"[github_dorking] {len(findings)} credential exposure(s) for '{target}'")
        return PluginResult(raw_output="\n".join(raw_lines), findings=findings)
