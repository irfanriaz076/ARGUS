"""
Notification service — sends alerts to Slack and/or generic webhooks
when critical/high findings are created during a scan.
"""
import asyncio
import logging
import os
from typing import Any, Dict, List

import httpx

log = logging.getLogger("argus.notifier")


def _webhook_url() -> str:
    return os.environ.get("WEBHOOK_URL", "") or os.environ.get("SLACK_WEBHOOK_URL", "")


def _slack_url() -> str:
    return os.environ.get("SLACK_WEBHOOK_URL", "")


def _should_notify(severity: str) -> bool:
    if severity == "critical":
        return os.environ.get("NOTIFY_ON_CRITICAL", "true").lower() == "true"
    if severity == "high":
        return os.environ.get("NOTIFY_ON_HIGH", "false").lower() == "true"
    return False


SEV_EMOJI = {
    "critical": "🔴",
    "high":     "🟠",
    "medium":   "🟡",
    "low":      "🟢",
    "info":     "⚪",
}


async def _post(url: str, payload: Dict[str, Any]) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            return r.status_code in (200, 204)
    except Exception as e:
        log.warning("Notification failed: %s", e)
        return False


async def notify_findings(
    engagement_id: str,
    engagement_name: str,
    findings: List[Dict[str, Any]],
):
    """Called after each scan completes. findings is a list of finding dicts."""
    alertable = [f for f in findings if _should_notify(f.get("severity", ""))]
    if not alertable:
        return

    slack_url   = _slack_url()
    generic_url = _webhook_url()

    for finding in alertable:
        sev   = finding.get("severity", "unknown")
        emoji = SEV_EMOJI.get(sev, "⚠️")
        title = finding.get("title", "Unknown finding")
        cve   = finding.get("cve_id")
        cvss  = finding.get("cvss_score")

        # ── Slack ─────────────────────────────────────────────────────
        if slack_url:
            slack_payload = {
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"{emoji} ARGUS Alert — {sev.upper()}"}
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Finding:*\n{title}"},
                            {"type": "mrkdwn", "text": f"*Engagement:*\n{engagement_name}"},
                            {"type": "mrkdwn", "text": f"*Severity:*\n{sev.upper()}"},
                            {"type": "mrkdwn", "text": f"*CVE:*\n{cve or 'N/A'}"},
                            {"type": "mrkdwn", "text": f"*CVSS:*\n{cvss or 'N/A'}"},
                            {"type": "mrkdwn", "text": f"*Engagement ID:*\n`{engagement_id}`"},
                        ]
                    }
                ]
            }
            await _post(slack_url, slack_payload)

        # ── Generic webhook ───────────────────────────────────────────
        if generic_url and generic_url != slack_url:
            await _post(generic_url, {
                "event":           "argus.finding",
                "engagement_id":   engagement_id,
                "engagement_name": engagement_name,
                "severity":        sev,
                "title":           title,
                "cve_id":          cve,
                "cvss_score":      cvss,
            })


def notify_findings_sync(
    engagement_id: str,
    engagement_name: str,
    findings: List[Dict[str, Any]],
):
    """Sync wrapper for Celery task context."""
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(notify_findings(engagement_id, engagement_name, findings))
        loop.close()
    except Exception as e:
        log.warning("notify_findings_sync error: %s", e)
