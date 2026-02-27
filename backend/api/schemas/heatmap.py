from pydantic import BaseModel


class HeatmapDay(BaseModel):
    """Single day item used in the heatmap response."""

    date: str
    weekday: int
    count: int
    level: int


class HeatmapWeek(BaseModel):
    """Week bucket containing ordered daily contribution items."""

    week_start: str
    days: list[HeatmapDay]


class HeatmapResponse(BaseModel):
    """Authenticated user heatmap response payload."""

    username: str
    total: int
    weeks: list[HeatmapWeek]
