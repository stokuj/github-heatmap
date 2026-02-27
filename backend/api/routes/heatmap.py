from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials

from backend.core.security import bearer_scheme
from backend.core.security import extract_bearer_token
from backend.services.heatmap_service import GitHubAPIError
from backend.services.heatmap_service import InvalidGitHubTokenError
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
    """Trigger a test exception endpoint for Sentry verification."""

    division_by_zero = 1 / 0
    return division_by_zero


@router.get("/heatmap/me")
def get_authenticated_user_heatmap(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, object]:
    """Return contribution heatmap payload for the authenticated GitHub user."""

    token = extract_bearer_token(credentials)

    try:
        return get_authenticated_user_heatmap_data(
            token=token,
            graphql_url=settings.github_graphql_url,
        )
    except InvalidGitHubTokenError as exc:
        raise HTTPException(status_code=401, detail="GitHub token is invalid") from exc
    except GitHubAPIError as exc:
        raise HTTPException(
            status_code=502, detail="GitHub API request failed"
        ) from exc
