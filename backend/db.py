from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

from backend.settings import Settings


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    settings = Settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set")
    return settings.database_url


engine = create_engine(get_database_url())
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
