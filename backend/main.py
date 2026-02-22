from datetime import date
from datetime import timedelta

import httpx
import sentry_sdk
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

from backend.github_api import fetch_authenticated_user
from backend.github_api import fetch_contribution_days
from backend.settings import Settings

bearer_scheme = HTTPBearer(auto_error=False)
settings = Settings()


def init_sentry(app_settings: Settings) -> None:
    if not app_settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=app_settings.sentry_dsn,
        environment=app_settings.environment,
        release=app_settings.release,
        traces_sample_rate=app_settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )


init_sentry(settings)
app = FastAPI()


def contribution_level(count: int) -> int:
    if count <= 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 9:
        return 3
    return 4


def extract_bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization Bearer token is required",
        )

    if credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise HTTPException(
            status_code=401,
            detail="Authorization Bearer token is required",
        )

    return credentials.credentials.strip()


def build_weeks_payload(
    contribution_days: list[dict[str, str | int]],
) -> tuple[list[dict[str, object]], int]:
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


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sentry-debug")
async def trigger_error() -> None:
    division_by_zero = 1 / 0
    return division_by_zero


@app.get("/heatmap/me")
def get_authenticated_user_heatmap(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, object]:
    token = extract_bearer_token(credentials)

    try:
        github_user = fetch_authenticated_user(token)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            raise HTTPException(
                status_code=401, detail="GitHub token is invalid"
            ) from exc
        raise HTTPException(
            status_code=502, detail="GitHub API request failed"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail="GitHub API request failed"
        ) from exc

    raw_username = github_user.get("login")
    if not isinstance(raw_username, str) or not raw_username:
        raise HTTPException(status_code=502, detail="GitHub user response is invalid")
    username = raw_username.lower()

    try:
        contribution_days = fetch_contribution_days(
            username=username,
            token=token,
            graphql_url=settings.github_graphql_url,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            raise HTTPException(
                status_code=401, detail="GitHub token is invalid"
            ) from exc
        raise HTTPException(
            status_code=502, detail="GitHub API request failed"
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail="GitHub API request failed"
        ) from exc

    weeks, total = build_weeks_payload(contribution_days)
    return {
        "username": username,
        "total": total,
        "weeks": weeks,
    }
