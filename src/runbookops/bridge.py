"""Allowlisted HTTP envelopes shared by the local bridge and AgentCore runtime."""

import re


def allowed_request(method: str, path: str) -> bool:
    identifier = r"[A-Za-z0-9_-]{1,100}"
    proposal = rf"(?:{identifier}|proposal:gada-[a-f0-9]{{12}}:[a-f0-9]{{10}})"
    routes = {
        "GET": rf"/(?:me|harness(?:/mcp)?|knowledge(?:/{identifier})?|incidents/{identifier}(?:/trace)?)",
        "POST": rf"/(?:investigations|knowledge/search|incidents/{identifier}/resume|proposals/{proposal}/decision)",
    }
    return bool(re.fullmatch(routes.get(method, r"(?!)"), path))
