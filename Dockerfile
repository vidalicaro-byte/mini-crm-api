# syntax=docker/dockerfile:1

# --- Build: install dependencies into a virtual environment with uv ---
FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies first (cached while uv.lock doesn't change), then the project itself.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# --- Runtime: only Python, the virtual environment and what migrations need ---
FROM python:3.14-slim

RUN useradd --create-home --uid 10001 app
WORKDIR /app

COPY --from=builder --chown=app:app /app/.venv /app/.venv
# Alembic reads its settings from pyproject.toml.
COPY --chown=app:app pyproject.toml alembic.ini docker-entrypoint.sh ./
COPY --chown=app:app migrations ./migrations

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

USER app
EXPOSE 8000
CMD ["sh", "/app/docker-entrypoint.sh"]
