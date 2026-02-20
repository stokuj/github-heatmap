from collections.abc import Mapping
from typing import Any

import httpx


def fetch_user_events(
    username: str,
    token: str | None,
    api_base_url: str,
) -> list[dict[str, Any]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-heatmap-demo",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"{api_base_url.rstrip('/')}/users/{username}/events"
    response = httpx.get(url, headers=headers, timeout=15.0)
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, list):
        raise ValueError("GitHub API response is not a list")

    valid_events: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, Mapping):
            valid_events.append(dict(item))
    return valid_events
