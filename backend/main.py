from fastapi import FastAPI

from backend.api.routes.heatmap import router as heatmap_router
from backend.core.observability import init_sentry
from backend.settings import Settings


def create_main() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    app_settings = Settings()
    init_sentry(app_settings)

    fastapi_app = FastAPI()
    fastapi_app.include_router(heatmap_router)
    return fastapi_app


main = create_main()
