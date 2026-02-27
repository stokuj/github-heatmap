from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from backend.api.routes.heatmap import router as heatmap_router
from backend.core.observability import init_sentry
from backend.services.heatmap_service import GitHubAPIError
from backend.services.heatmap_service import InvalidGitHubTokenError
from backend.settings import Settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    app_settings = Settings()
    init_sentry(app_settings)

    fastapi_app = FastAPI()

    @fastapi_app.exception_handler(InvalidGitHubTokenError)
    async def invalid_token_handler(
        _request: Request,
        _exc: InvalidGitHubTokenError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401, content={"detail": "GitHub token is invalid"}
        )

    @fastapi_app.exception_handler(GitHubAPIError)
    async def github_api_error_handler(
        _request: Request,
        _exc: GitHubAPIError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"detail": "GitHub API request failed"},
        )

    fastapi_app.include_router(heatmap_router)
    return fastapi_app


app = create_app()
