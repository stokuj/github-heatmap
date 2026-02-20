from fastapi import FastAPI
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy import text

from backend.settings import Settings

app = FastAPI()


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
        engine = create_engine(database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="Database connection failed"
        ) from exc

    return {"status": "ok"}
