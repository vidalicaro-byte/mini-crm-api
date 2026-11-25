from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


@router.get("/health", summary="Liveness check")
def health() -> HealthResponse:
    """Return 200 while the process is up (used by the host health check)."""
    return HealthResponse(status="ok")
