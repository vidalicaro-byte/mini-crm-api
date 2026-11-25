"""Every error answers with `{"message": "..."}`, the body the front end shows to the user."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from crm_api.schemas import ErrorResponse


class ApiError(StarletteHTTPException):
    """An HTTP error with a user-facing message (in Portuguese, like the rest of the UI)."""

    def __init__(self, status_code: int, message: str, headers: dict[str, str] | None = None):
        super().__init__(status_code=status_code, detail=message, headers=headers)


def unauthorized() -> ApiError:
    return ApiError(401, "Sessão expirada. Entre novamente.", {"WWW-Authenticate": "Bearer"})


def forbidden() -> ApiError:
    return ApiError(403, "Você não tem permissão para acessar este recurso.")


def not_found(message: str) -> ApiError:
    return ApiError(404, message)


def responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Document error statuses in OpenAPI with the shared error body."""
    return {code: {"model": ErrorResponse} for code in status_codes}


async def _http_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    message = exc.detail if isinstance(exc.detail, str) else "Erro inesperado."
    return JSONResponse({"message": message}, status_code=exc.status_code, headers=exc.headers)


async def _validation_error(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    errors = [
        {"field": ".".join(str(part) for part in error["loc"][1:]), "message": error["msg"]}
        for error in exc.errors()
    ]
    # `message` for people (the front end shows it); `errors` for programs and debugging.
    return JSONResponse({"message": "Dados inválidos.", "errors": errors}, status_code=422)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
