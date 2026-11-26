from fastapi import FastAPI

from crm_api import __version__
from crm_api.config import get_settings
from crm_api.errors import register_error_handlers
from crm_api.routers import auth, contacts, health, users

DESCRIPTION = """
REST API behind the [Mini-CRM](https://github.com/vidalicaro-byte/mini-crm) front end.

**Try it:** click **Authorize** and sign in with `marina@minicrm.demo` (admin) or
`rafael@minicrm.demo` (seller), password `demo1234`. Sellers only see their own contacts and deals.
"""


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        summary="REST API for the Mini-CRM front end.",
        description=DESCRIPTION,
        swagger_ui_parameters={"persistAuthorization": True},
    )
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(contacts.router)
    return app


app = create_app()
