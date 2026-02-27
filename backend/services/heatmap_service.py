from datetime import date
from datetime import timedelta

import httpx

from backend.clients.github_client import fetch_authenticated_user
from backend.clients.github_client import fetch_contribution_days


class InvalidGitHubTokenError(Exception):
    """Raised when GitHub rejects the provided token."""


class GitHubAPIError(Exception):
    """Raised when GitHub requests fail for non-auth reasons."""


def contribution_level(count: int) -> int:
    """Map daily contribution count to a heatmap level in range 0..4."""

    if count <= 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 9:
        return 3
    return 4


def build_weeks_payload(
    contribution_days: list[dict[str, str | int]],
) -> tuple[list[dict[str, object]], int]:
    """Group contribution days into week buckets and compute total count."""

    grouped_weeks: dict[date, list[dict[str, int | str]]] = {}
    total = 0

    for item in contribution_days:
        raw_day = item.get("date")
        raw_count = item.get("count")
        if not isinstance(raw_day, str) or not isinstance(raw_count, int):
            continue

        try:
            parsed_day = date.fromisoformat(raw_day)
        except ValueError:
            continue

        weekday = (parsed_day.weekday() + 1) % 7
        week_start = parsed_day - timedelta(days=weekday)
        grouped_weeks.setdefault(week_start, []).append(
            {
                "date": parsed_day.isoformat(),
                "weekday": weekday,
                "count": raw_count,
                "level": contribution_level(raw_count),
            }
        )
        total += raw_count

    weeks: list[dict[str, object]] = []
    for week_start in sorted(grouped_weeks):
        days = sorted(grouped_weeks[week_start], key=lambda day: int(day["weekday"]))
        weeks.append({"week_start": week_start.isoformat(), "days": days})

    return weeks, total


def get_authenticated_user_heatmap_data(
    token: str,
    graphql_url: str,
) -> dict[str, object]:
    """Build a heatmap payload for the GitHub user linked to token."""

    try:
        github_user = fetch_authenticated_user(token)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            raise InvalidGitHubTokenError from exc
        raise GitHubAPIError from exc
    except Exception as exc:
        raise GitHubAPIError from exc

    raw_username = github_user.get("login")
    if not isinstance(raw_username, str) or not raw_username:
        raise GitHubAPIError("GitHub user response is invalid")
    username = raw_username.lower()

    try:
        contribution_days = fetch_contribution_days(
            username=username,
            token=token,
            graphql_url=graphql_url,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            raise InvalidGitHubTokenError from exc
        raise GitHubAPIError from exc
    except Exception as exc:
        raise GitHubAPIError from exc

    weeks, total = build_weeks_payload(contribution_days)
    return {
        "username": username,
        "total": total,
        "weeks": weeks,
    }
