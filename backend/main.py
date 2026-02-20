from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import UTC

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from pydantic import Field
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import engine
from backend.db import get_db
from backend.github_api import fetch_user_events
from backend.models import GitHubEvent
from backend.models import GitHubProfile
from backend.models import HeatmapDay
from backend.models import SyncRun
from backend.settings import Settings

app = FastAPI()


class ProfileCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)


class HeatmapDayCreate(BaseModel):
    day: date
    count: int = Field(ge=0)


def parse_github_datetime(raw_value: str) -> datetime:
    return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))


def rebuild_heatmap_days_for_profile(db: Session, profile_id: int) -> int:
    events = db.scalars(
        select(GitHubEvent).where(GitHubEvent.profile_id == profile_id)
    ).all()

    aggregated_counts: dict[date, int] = {}
    for event in events:
        day = event.event_created_at.date()
        aggregated_counts[day] = aggregated_counts.get(day, 0) + 1

    db.execute(delete(HeatmapDay).where(HeatmapDay.profile_id == profile_id))
    for day, count in sorted(aggregated_counts.items()):
        db.add(HeatmapDay(profile_id=profile_id, day=day, contribution_count=count))

    return len(aggregated_counts)


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health/db")
def health_db() -> dict[str, str]:
    settings = Settings()
    database_url = settings.database_url
    if not database_url:
        raise HTTPException(status_code=500, detail="DATABASE_URL is not set")

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="Database connection failed"
        ) from exc

    return {"status": "ok"}


@app.post("/profiles", status_code=201)
def create_profile(
    payload: ProfileCreate, db: Session = Depends(get_db)
) -> dict[str, str | int]:
    username = payload.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="username cannot be empty")

    existing_profile = db.scalar(
        select(GitHubProfile).where(GitHubProfile.username == username)
    )
    if existing_profile:
        raise HTTPException(status_code=409, detail="profile already exists")

    profile = GitHubProfile(username=username)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return {"id": profile.id, "username": profile.username}


@app.get("/profiles")
def list_profiles(db: Session = Depends(get_db)) -> list[dict[str, str | int]]:
    profiles = db.scalars(
        select(GitHubProfile).order_by(GitHubProfile.username.asc())
    ).all()
    return [{"id": profile.id, "username": profile.username} for profile in profiles]


@app.post("/profiles/{username}/days")
def create_or_update_heatmap_day(
    username: str,
    payload: HeatmapDayCreate,
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    profile = db.scalar(
        select(GitHubProfile).where(GitHubProfile.username == username.lower())
    )
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")

    heatmap_day = db.scalar(
        select(HeatmapDay).where(
            HeatmapDay.profile_id == profile.id,
            HeatmapDay.day == payload.day,
        )
    )

    if heatmap_day is None:
        heatmap_day = HeatmapDay(
            profile_id=profile.id,
            day=payload.day,
            contribution_count=payload.count,
        )
        db.add(heatmap_day)
    else:
        heatmap_day.contribution_count = payload.count

    db.commit()
    return {"day": payload.day.isoformat(), "count": payload.count}


@app.get("/heatmap/{username}")
def get_heatmap(
    username: str, db: Session = Depends(get_db)
) -> list[dict[str, str | int]]:
    profile = db.scalar(
        select(GitHubProfile).where(GitHubProfile.username == username.lower())
    )
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")

    days = db.scalars(
        select(HeatmapDay)
        .where(HeatmapDay.profile_id == profile.id)
        .order_by(HeatmapDay.day.asc())
    ).all()
    return [
        {"day": day.day.isoformat(), "count": day.contribution_count} for day in days
    ]


@app.get("/heatmap/{username}/calendar")
def get_calendar_heatmap(
    username: str,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> dict[str, str | int | list[dict[str, str | int]]]:
    profile = db.scalar(
        select(GitHubProfile).where(GitHubProfile.username == username.lower())
    )
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")

    if from_date is None and to_date is None:
        to_date = date.today()
        from_date = to_date - timedelta(days=364)
    elif from_date is None or to_date is None:
        raise HTTPException(
            status_code=400, detail="from and to must be provided together"
        )

    if from_date > to_date:
        raise HTTPException(
            status_code=400, detail="from must be before or equal to to"
        )

    selected_days = db.scalars(
        select(HeatmapDay)
        .where(HeatmapDay.profile_id == profile.id)
        .where(HeatmapDay.day >= from_date)
        .where(HeatmapDay.day <= to_date)
        .order_by(HeatmapDay.day.asc())
    ).all()

    counts_by_date = {day.day: day.contribution_count for day in selected_days}

    days: list[dict[str, str | int]] = []
    current_day = from_date
    total = 0
    while current_day <= to_date:
        count = counts_by_date.get(current_day, 0)
        total += count
        days.append({"date": current_day.isoformat(), "count": count})
        current_day += timedelta(days=1)

    return {
        "username": profile.username,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "total": total,
        "days": days,
    }


@app.post("/profiles/{username}/sync")
def sync_profile(username: str, db: Session = Depends(get_db)) -> dict[str, int | str]:
    normalized_username = username.lower()
    profile = db.scalar(
        select(GitHubProfile).where(GitHubProfile.username == normalized_username)
    )
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")

    sync_run = SyncRun(profile_id=profile.id, status="running")
    db.add(sync_run)
    db.flush()

    settings = Settings()

    try:
        remote_events = fetch_user_events(
            username=normalized_username,
            token=settings.github_token,
            api_base_url=settings.github_api_base_url,
        )
    except Exception as exc:
        sync_run.status = "failed"
        sync_run.error_message = "GitHub API request failed"
        sync_run.finished_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(
            status_code=502, detail="GitHub API request failed"
        ) from exc

    saved_count = 0
    for item in remote_events:
        event_id = item.get("id")
        event_type = item.get("type")
        created_at_raw = item.get("created_at")
        repo_data = item.get("repo")
        repo_name = repo_data.get("name") if isinstance(repo_data, dict) else None

        if not isinstance(event_id, str):
            continue
        if not isinstance(event_type, str):
            continue
        if not isinstance(created_at_raw, str):
            continue

        existing_event = db.scalar(
            select(GitHubEvent).where(GitHubEvent.github_event_id == event_id)
        )
        if existing_event:
            continue

        db.add(
            GitHubEvent(
                profile_id=profile.id,
                github_event_id=event_id,
                event_type=event_type,
                repo_name=repo_name,
                event_created_at=parse_github_datetime(created_at_raw),
                payload=item,
            )
        )
        saved_count += 1

    db.flush()
    days_updated = rebuild_heatmap_days_for_profile(db=db, profile_id=profile.id)

    sync_run.status = "success"
    sync_run.fetched_count = len(remote_events)
    sync_run.saved_count = saved_count
    sync_run.error_message = None
    sync_run.finished_at = datetime.now(UTC)
    db.commit()

    return {
        "status": "ok",
        "fetched": len(remote_events),
        "saved": saved_count,
        "days_updated": days_updated,
    }
