from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials

from backend.api.schemas.heatmap import HeatmapResponse
from backend.core.security import bearer_scheme
from backend.core.security import extract_bearer_token
from backend.services.heatmap_service import get_authenticated_user_heatmap_data
from backend.settings import Settings


router = APIRouter()
settings = Settings()


@router.get("/")
async def root() -> dict[str, str]:
    """Return a basic service greeting."""

    return {"message": "Hello World"}


@router.get("/health/live")
def health_live() -> dict[str, str]:
    """Return liveness probe response for health checks."""

    return {"status": "ok"}


@router.get("/sentry-debug")
async def trigger_error() -> None:
    """Trigger a test exception endpoint for Sentry verification in development."""

    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not Found")

    raise ZeroDivisionError("Sentry debug endpoint")


@router.get("/heatmap/me", response_model=HeatmapResponse)
def get_authenticated_user_heatmap(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> HeatmapResponse:
    """Return contribution heatmap payload for the authenticated GitHub user."""

    token = extract_bearer_token(credentials)

    payload = get_authenticated_user_heatmap_data(
        token=token, graphql_url=settings.github_graphql_url
    )
    return HeatmapResponse.model_validate(payload)
