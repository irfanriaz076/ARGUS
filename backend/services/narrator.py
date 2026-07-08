"""
LLM attack-narrative generation.

Turns the correlated findings + attack paths + graph into a red-team engagement
story. Provider-agnostic: talks to any OpenAI-compatible /chat/completions
endpoint (GitHub Models, OpenAI, Azure, local Ollama, etc.) configured via env.

No SDK dependency — a single httpx call keeps this portable and easy to swap.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import httpx

from backend.config import settings


class NarratorError(RuntimeError):
    """Raised when the narrative cannot be produced (config or upstream error)."""


_SYSTEM_PROMPT = (
    "You are a senior offensive-security operator writing the analysis section of a "
    "penetration-test report. You are given structured results from an automated "
    "recon-to-exploitation pipeline. Write a precise, factual, professional narrative. "
    "Do not invent findings that are not in the data. Do not add caveats about being an AI. "
    "Respond with ONLY a single JSON object, no markdown fences, matching the requested schema."
)

_SCHEMA_HINT = {
    "executive_summary": "2-4 sentence plain-language summary for a non-technical stakeholder",
    "risk_rating": "one of: Critical, High, Medium, Low",
    "attack_chain": [
        {
            "step": 1,
            "title": "short phase title, e.g. Initial Foothold",
            "asset": "the host/endpoint/service involved",
            "technique": "MITRE ATT&CK id if applicable, else empty string",
            "detail": "1-2 sentences on what an attacker does at this step",
        }
    ],
    "key_findings": [
        {"title": "finding title", "severity": "critical|high|medium|low", "impact": "why it matters"}
    ],
    "recommendations": ["actionable remediation step", "..."],
    "narrative": "a flowing 1-2 paragraph story of the end-to-end compromise",
}


def is_configured() -> bool:
    return bool(settings.LLM_API_KEY)


def _build_user_prompt(context: Dict[str, Any]) -> str:
    return (
        "Engagement context and results are below as JSON. Produce the report JSON.\n\n"
        f"=== ENGAGEMENT ===\n{json.dumps(context['engagement'], indent=2)}\n\n"
        f"=== RISK / CORRELATION ===\n{json.dumps(context['correlation'], indent=2)}\n\n"
        f"=== RANKED ATTACK PATHS (most exploitable first) ===\n"
        f"{json.dumps(context['attack_paths'], indent=2)}\n\n"
        f"=== TOP FINDINGS ===\n{json.dumps(context['findings'], indent=2)}\n\n"
        f"=== GRAPH SUMMARY ===\n{json.dumps(context['graph_summary'], indent=2)}\n\n"
        "Return JSON with exactly these keys: "
        f"{json.dumps(list(_SCHEMA_HINT.keys()))}. "
        "Use the attack paths to structure attack_chain in attacker order "
        "(external entry → pivots → crown jewel). "
        "For each attack_chain step's 'technique' field, use ONLY a MITRE ATT&CK id "
        "that appears in the findings data above — do not invent technique ids."
    )


def _extract_json(text: str) -> Dict[str, Any]:
    """Best-effort parse: handle raw JSON or JSON wrapped in ``` fences."""
    text = (text or "").strip()
    if text.startswith("```"):
        # drop the first fence line and any trailing fence
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text.strip("`")
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


async def generate_narrative(context: Dict[str, Any]) -> Dict[str, Any]:
    """Call the configured LLM and return the parsed report dict."""
    if not is_configured():
        raise NarratorError(
            "No LLM API key configured. Set LLM_API_KEY (and optionally "
            "LLM_BASE_URL / LLM_MODEL) in your .env — see .env.example."
        )

    url = settings.LLM_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.LLM_MODEL,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(context)},
        ],
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as e:
        raise NarratorError(f"LLM request failed: {e}") from e

    if resp.status_code == 401:
        raise NarratorError("LLM rejected the API key (401). Check LLM_API_KEY.")
    if resp.status_code == 429:
        raise NarratorError("LLM rate limit reached (429). Try again shortly.")
    if resp.status_code >= 400:
        # Some endpoints reject response_format; retry once without it.
        if "response_format" in payload:
            payload.pop("response_format")
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
            except httpx.HTTPError as e:
                raise NarratorError(f"LLM request failed: {e}") from e
        if resp.status_code >= 400:
            raise NarratorError(f"LLM error {resp.status_code}: {resp.text[:300]}")

    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        raise NarratorError(f"Unexpected LLM response shape: {e}") from e

    try:
        report = _extract_json(content)
    except json.JSONDecodeError:
        # Fall back to a minimal report carrying the raw prose.
        report = {
            "executive_summary": content[:600],
            "risk_rating": "",
            "attack_chain": [],
            "key_findings": [],
            "recommendations": [],
            "narrative": content,
        }

    report["model"] = settings.LLM_MODEL
    return report


def build_context(engagement, findings: List, correlation: Dict, attack_paths: Dict,
                  graph_summary: Dict) -> Dict[str, Any]:
    """Assemble the compact JSON context handed to the model."""
    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    top = sorted(findings, key=lambda f: sev_order.get(f.severity, 5))[:20]

    return {
        "engagement": {
            "name": engagement.name,
            "scope": list(engagement.scope or []),
            "status": engagement.status,
        },
        "correlation": {
            "risk_score": correlation.get("risk_score"),
            "severity_counts": correlation.get("severity_counts"),
            "unique_findings": correlation.get("unique_findings"),
            "target_count": correlation.get("target_count"),
        },
        "attack_paths": [
            {
                "score": p["score"],
                "severity": p["severity"],
                "entry": p["entry"]["label"],
                "target": p["target"]["label"],
                "target_reason": p["target"]["reason"],
                "route": p["rationale"],
            }
            for p in attack_paths.get("paths", [])
        ],
        "findings": [
            {
                "title": f.title,
                "severity": f.severity,
                "cve": f.cve_id or "",
                "cvss": float(f.cvss_score) if f.cvss_score else None,
                "mitre": f.mitre_technique or "",
                "mitre_name": (f.evidence or {}).get("mitre", {}).get("name", ""),
            }
            for f in top
        ],
        "graph_summary": graph_summary,
    }
