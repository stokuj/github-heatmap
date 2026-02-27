from collections.abc import Mapping
from datetime import date
from datetime import timedelta
from typing import Any

import httpx


def fetch_authenticated_user(token: str) -> dict[str, str | int]:
    """Fetch basic profile data for the token owner from GitHub REST API."""

    response = httpx.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-heatmap-demo",
        },
        timeout=15.0,
    )
    response.raise_for_status()

    payload: Any = response.json()
    if not isinstance(payload, Mapping):
        raise ValueError("GitHub user response is invalid")

    raw_id = payload.get("id")
    raw_login = payload.get("login")
    if not isinstance(raw_id, int) or not isinstance(raw_login, str) or not raw_login:
        raise ValueError("GitHub user response is missing required fields")

    return {"id": raw_id, "login": raw_login}


def fetch_contribution_days(
    username: str,
    token: str,
    graphql_url: str
) -> list[dict[str, str | int]]:
    """Fetch one-year contribution days for a user from GitHub GraphQL API."""

    if not token:
        raise ValueError("GITHUB_TOKEN is required for GraphQL requests")

    to_day = date.today()
    from_day = to_day - timedelta(days=364)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    variables = {
        "login": username,
        "from": f"{from_day.isoformat()}T00:00:00Z",
        "to": f"{to_day.isoformat()}T23:59:59Z",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "github-heatmap-demo",
    }

    response = httpx.post(
        graphql_url,
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=20.0,
    )
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, Mapping):
        raise ValueError("GitHub GraphQL response is invalid")

    if payload.get("errors"):
        raise ValueError("GitHub GraphQL returned errors")

    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise ValueError("GitHub GraphQL data is missing")

    user = data.get("user")
    if not isinstance(user, Mapping):
        raise ValueError("GitHub user not found")

    collection = user.get("contributionsCollection")
    if not isinstance(collection, Mapping):
        raise ValueError("GitHub contributionsCollection is missing")

    calendar = collection.get("contributionCalendar")
    if not isinstance(calendar, Mapping):
        raise ValueError("GitHub contributionCalendar is missing")

    weeks = calendar.get("weeks")
    if not isinstance(weeks, list):
        raise ValueError("GitHub contribution weeks are missing")

    days: list[dict[str, str | int]] = []
    for week in weeks:
        if not isinstance(week, Mapping):
            continue
        contribution_days = week.get("contributionDays")
        if not isinstance(contribution_days, list):
            continue
        for item in contribution_days:
            if not isinstance(item, Mapping):
                continue
            raw_date = item.get("date")
            raw_count = item.get("contributionCount")
            if isinstance(raw_date, str) and isinstance(raw_count, int):
                days.append({"date": raw_date, "count": raw_count})

    return days
