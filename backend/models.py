from datetime import date
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from backend.db import Base


class GitHubProfile(Base):
    __tablename__ = "github_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    days: Mapped[list["HeatmapDay"]] = relationship(back_populates="profile")


class HeatmapDay(Base):
    __tablename__ = "heatmap_days"
    __table_args__ = (UniqueConstraint("profile_id", "day", name="uq_profile_day"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("github_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
    contribution_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    profile: Mapped[GitHubProfile] = relationship(back_populates="days")
