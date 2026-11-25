from fastapi import FastAPI

from crm_api import __version__
from crm_api.config import get_settings
from crm_api.routers import health


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        summary="REST API for the Mini-CRM front end.",
    )
    app.include_router(health.router)
    return app


app = create_app()
