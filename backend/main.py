from datetime import date

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import engine
from backend.db import get_db
from backend.models import GitHubProfile
from backend.models import HeatmapDay
from backend.settings import Settings

app = FastAPI()


class ProfileCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)


class HeatmapDayCreate(BaseModel):
    day: date
    count: int = Field(ge=0)


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
