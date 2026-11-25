# Mini-CRM API

REST API for the [Mini-CRM](https://github.com/vidalicaro-byte/mini-crm) front end, built with FastAPI.

> Work in progress. The full README (English and Portuguese) comes with the first release.

## Run locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run alembic upgrade head      # create the tables (SQLite file crm.db by default)
uv run python -m crm_api.seed    # load the demo data (safe to run again: it resets the data)
uv run fastapi dev src/crm_api/main.py
```

Demo users share the password `demo1234`: `marina@minicrm.demo` (admin) and
`rafael@minicrm.demo` (seller).

Set `DATABASE_URL` (see `.env.example`) to use PostgreSQL instead of SQLite.

## Authentication

`POST /api/auth/login` with `{"email", "password"}` returns a JWT (valid for 8 hours). Send it as
`Authorization: Bearer <token>`. In the interactive docs, click **Authorize** and use the e-mail as
the username. `GET /api/users` is admin-only (403 for sellers). Errors always answer with
`{"message": "..."}`; validation errors (422) add an `errors` list with the fields.

Interactive docs: http://127.0.0.1:8000/docs

## Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run alembic check   # models and migrations agree
```

## License

[MIT](LICENSE)
