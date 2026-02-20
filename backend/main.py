from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import UTC
import json

from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel
from pydantic import Field
from fastapi.responses import HTMLResponse
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db import engine
from backend.db import get_db
from backend.github_api import fetch_contribution_days
from backend.models import GitHubProfile
from backend.models import HeatmapDay
from backend.models import SyncRun
from backend.settings import Settings

app = FastAPI()

WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
HEATMAP_LEVELS = [
    {"level": 0, "label": "0", "min": 0, "max": 0},
    {"level": 1, "label": "1-2", "min": 1, "max": 2},
    {"level": 2, "label": "3-5", "min": 3, "max": 5},
    {"level": 3, "label": "6-9", "min": 6, "max": 9},
    {"level": 4, "label": "10+", "min": 10, "max": None},
]


class ProfileCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)


class HeatmapDayCreate(BaseModel):
    day: date
    count: int = Field(ge=0)


def rebuild_heatmap_days_for_profile(
    db: Session,
    profile_id: int,
    contribution_days: list[dict[str, str | int]],
) -> int:
    db.execute(delete(HeatmapDay).where(HeatmapDay.profile_id == profile_id))

    saved_rows = 0
    for item in contribution_days:
        raw_day = item.get("date")
        raw_count = item.get("count")
        if not isinstance(raw_day, str) or not isinstance(raw_count, int):
            continue

        parsed_day = date.fromisoformat(raw_day)
        if raw_count <= 0:
            continue

        db.add(
            HeatmapDay(
                profile_id=profile_id,
                day=parsed_day,
                contribution_count=raw_count,
            )
        )
        saved_rows += 1

    return saved_rows


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/demo/{username}", response_class=HTMLResponse)
def demo_heatmap(username: str) -> str:
    safe_username = json.dumps(username.lower())
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Heatmap Demo</title>
  <style>
    :root {{
      --bg: #f6f8fa;
      --panel: #ffffff;
      --text: #24292f;
      --muted: #57606a;
      --border: #d0d7de;
      --l0: #ebedf0;
      --l1: #9be9a8;
      --l2: #40c463;
      --l3: #30a14e;
      --l4: #216e39;
    }}
    body {{ margin: 0; padding: 24px; font-family: Segoe UI, sans-serif; background: var(--bg); color: var(--text); }}
    .card {{ max-width: 1100px; margin: 0 auto; background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }}
    .top {{ display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; }}
    .title {{ font-size: 20px; font-weight: 600; }}
    .muted {{ color: var(--muted); font-size: 13px; }}
    .legend {{ display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--muted); }}
    .cell {{ width: 11px; height: 11px; border-radius: 2px; border: 1px solid rgba(27,31,36,0.06); }}
    .l0 {{ background: var(--l0); }} .l1 {{ background: var(--l1); }} .l2 {{ background: var(--l2); }} .l3 {{ background: var(--l3); }} .l4 {{ background: var(--l4); }}
    .months {{ display: flex; gap: 4px; margin: 16px 0 6px 40px; color: var(--muted); font-size: 12px; }}
    .grid-wrap {{ display: grid; grid-template-columns: 32px auto; gap: 8px; overflow-x: auto; }}
    .weekdays {{ display: grid; grid-template-rows: repeat(7, 12px); row-gap: 3px; color: var(--muted); font-size: 11px; margin-top: 2px; }}
    .weeks {{ display: grid; grid-auto-flow: column; grid-auto-columns: 12px; column-gap: 3px; }}
    .week {{ display: grid; grid-template-rows: repeat(7, 12px); row-gap: 3px; }}
    .status {{ margin-top: 12px; font-size: 13px; color: var(--muted); }}
  </style>
</head>
<body>
  <div class=\"card\">
    <div class=\"top\">
      <div>
        <div class=\"title\">GitHub Heatmap Demo</div>
        <div id=\"range\" class=\"muted\">Loading...</div>
      </div>
      <div class=\"legend\">Less
        <span class=\"cell l0\"></span><span class=\"cell l1\"></span><span class=\"cell l2\"></span><span class=\"cell l3\"></span><span class=\"cell l4\"></span>
        More
      </div>
    </div>
    <div id=\"months\" class=\"months\"></div>
    <div class=\"grid-wrap\">
      <div id=\"weekdayLabels\" class=\"weekdays\"></div>
      <div id=\"weeks\" class=\"weeks\"></div>
    </div>
    <div id=\"status\" class=\"status\"></div>
  </div>

  <script>
    const username = {safe_username};

    function labelForWeekday(idx) {{
      return idx === 1 || idx === 3 || idx === 5 ? ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][idx] : '';
    }}

    async function load() {{
      const status = document.getElementById('status');
      try {{
        const gridRes = await fetch(`/heatmap/${{username}}/calendar-grid`);
        if (!gridRes.ok) throw new Error(`API error: ${{gridRes.status}}`);
        const grid = await gridRes.json();

        document.getElementById('range').textContent = `@${{grid.username}} | ${{grid.from}} to ${{grid.to}} | total: ${{grid.total}}`;

        const weekdays = document.getElementById('weekdayLabels');
        weekdays.innerHTML = '';
        const labels = grid.weekday_labels || ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
        for (let i = 0; i < 7; i++) {{
          const row = document.createElement('div');
          row.textContent = labelForWeekday(i) || '';
          weekdays.appendChild(row);
        }}

        const months = document.getElementById('months');
        months.innerHTML = '';
        for (const m of grid.month_labels || []) {{
          const el = document.createElement('div');
          el.textContent = m.label;
          el.style.minWidth = '52px';
          months.appendChild(el);
        }}

        const weeks = document.getElementById('weeks');
        weeks.innerHTML = '';
        for (const week of grid.weeks) {{
          const col = document.createElement('div');
          col.className = 'week';
          for (const day of week.days) {{
            const cell = document.createElement('div');
            cell.className = `cell l${{day.level}}`;
            cell.title = `${{day.date}}: ${{day.count}}`;
            col.appendChild(cell);
          }}
          weeks.appendChild(col);
        }}

        status.textContent = 'Loaded successfully';
      }} catch (err) {{
        status.textContent = `Cannot load heatmap for @${{username}}. ${{err.message}}`;
      }}
    }}

    load();
  </script>
</body>
</html>"""


@app.get("/meta/heatmap")
def get_heatmap_meta() -> dict[str, object]:
    return {
        "weekday_labels": WEEKDAY_LABELS,
        "levels": HEATMAP_LEVELS,
    }


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


@app.get("/heatmap/{username}/calendar-grid")
def get_calendar_grid(
    username: str,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
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
    counts_by_date = {item.day: item.contribution_count for item in selected_days}

    start_offset = (from_date.weekday() + 1) % 7
    grid_start = from_date - timedelta(days=start_offset)
    end_offset = (6 - ((to_date.weekday() + 1) % 7)) % 7
    grid_end = to_date + timedelta(days=end_offset)

    weeks: list[dict[str, object]] = []
    month_labels: list[dict[str, str]] = []
    current_week_start = grid_start
    total = 0
    last_labeled_month: str | None = None

    while current_week_start <= grid_end:
        week_days: list[dict[str, int | str]] = []
        week_in_range_days: list[date] = []
        for i in range(7):
            current_day = current_week_start + timedelta(days=i)
            count = counts_by_date.get(current_day, 0)
            if from_date <= current_day <= to_date:
                total += count
                week_in_range_days.append(current_day)
            week_days.append(
                {
                    "date": current_day.isoformat(),
                    "weekday": i,
                    "count": count,
                    "level": contribution_level(count),
                }
            )

        if week_in_range_days:
            month_key = week_in_range_days[0].strftime("%Y-%m")
            if month_key != last_labeled_month:
                month_labels.append(
                    {
                        "week_start": current_week_start.isoformat(),
                        "month": month_key,
                        "label": week_in_range_days[0].strftime("%b"),
                    }
                )
                last_labeled_month = month_key

        weeks.append({"week_start": current_week_start.isoformat(), "days": week_days})
        current_week_start += timedelta(days=7)

    return {
        "username": profile.username,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "total": total,
        "weekday_labels": WEEKDAY_LABELS,
        "month_labels": month_labels,
        "weeks": weeks,
    }


@app.post("/profiles/{username}/sync")
def sync_profile(username: str, db: Session = Depends(get_db)) -> dict[str, int | str]:
    normalized_username = username.lower()
    profile = db.scalar(
        select(GitHubProfile).where(GitHubProfile.username == normalized_username)
    )
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")

    settings = Settings()
    now = datetime.now(UTC)

    latest_run = db.scalar(
        select(SyncRun)
        .where(SyncRun.profile_id == profile.id)
        .order_by(SyncRun.started_at.desc())
        .limit(1)
    )
    if latest_run is not None:
        last_started_at = latest_run.started_at
        if last_started_at.tzinfo is None:
            last_started_at = last_started_at.replace(tzinfo=UTC)
        elapsed_seconds = (now - last_started_at).total_seconds()
        if elapsed_seconds < settings.sync_cooldown_seconds:
            retry_after = max(1, int(settings.sync_cooldown_seconds - elapsed_seconds))
            raise HTTPException(
                status_code=429,
                detail="sync rate limited",
                headers={"Retry-After": str(retry_after)},
            )

    hourly_window_start = now - timedelta(hours=1)
    runs_in_hour = db.scalar(
        select(func.count(SyncRun.id))
        .where(SyncRun.profile_id == profile.id)
        .where(SyncRun.started_at >= hourly_window_start)
    )
    runs_in_hour = int(runs_in_hour or 0)

    if runs_in_hour >= settings.sync_max_per_hour:
        oldest_run_in_window = db.scalar(
            select(SyncRun)
            .where(SyncRun.profile_id == profile.id)
            .where(SyncRun.started_at >= hourly_window_start)
            .order_by(SyncRun.started_at.asc())
            .limit(1)
        )

        retry_after = 3600
        if oldest_run_in_window is not None:
            oldest_started_at = oldest_run_in_window.started_at
            if oldest_started_at.tzinfo is None:
                oldest_started_at = oldest_started_at.replace(tzinfo=UTC)
            age_seconds = (now - oldest_started_at).total_seconds()
            retry_after = max(1, int(3600 - age_seconds))

        raise HTTPException(
            status_code=429,
            detail="hourly sync limit reached",
            headers={"Retry-After": str(retry_after)},
        )

    sync_run = SyncRun(profile_id=profile.id, status="running")
    db.add(sync_run)
    db.flush()

    if not settings.github_token:
        sync_run.status = "failed"
        sync_run.error_message = "GITHUB_TOKEN is not set"
        sync_run.finished_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(status_code=500, detail="GITHUB_TOKEN is not set")

    try:
        contribution_days = fetch_contribution_days(
            username=normalized_username,
            token=settings.github_token,
            graphql_url=settings.github_graphql_url,
        )
    except Exception as exc:
        sync_run.status = "failed"
        sync_run.error_message = "GitHub API request failed"
        sync_run.finished_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(
            status_code=502, detail="GitHub API request failed"
        ) from exc

    days_updated = rebuild_heatmap_days_for_profile(
        db=db,
        profile_id=profile.id,
        contribution_days=contribution_days,
    )

    sync_run.status = "success"
    sync_run.fetched_count = len(contribution_days)
    sync_run.saved_count = days_updated
    sync_run.error_message = None
    sync_run.finished_at = datetime.now(UTC)
    db.commit()

    return {
        "status": "ok",
        "fetched": len(contribution_days),
        "saved": days_updated,
        "days_updated": days_updated,
    }
