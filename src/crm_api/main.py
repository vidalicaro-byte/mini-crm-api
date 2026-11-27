from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from crm_api import __version__
from crm_api.config import get_settings
from crm_api.errors import register_error_handlers
from crm_api.routers import activities, auth, companies, contacts, deals, health, overview, users

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
        summary="Contacts, companies, deal pipeline and dashboard metrics, with JWT auth.",
        description=DESCRIPTION,
        swagger_ui_parameters={"persistAuthorization": True},
        # Clean operation ids (`list_contacts`, not `list_contacts_api_contacts_get`) for
        # anyone generating a client from /openapi.json.
        generate_unique_id_function=lambda route: route.name,
    )
    register_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Location"],
        max_age=600,
    )

    # HEAD too: hosts and uptime monitors probe with it.
    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/docs")

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(contacts.router)
    app.include_router(companies.router)
    app.include_router(deals.router)
    app.include_router(activities.router)
    app.include_router(overview.router)
    return app


app = create_app()
