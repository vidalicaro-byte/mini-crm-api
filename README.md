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

## Endpoints so far

| Method | Path | Notes |
| --- | --- | --- |
| `POST` | `/api/auth/login` | E-mail and password → `{token, user}` |
| `GET` | `/api/auth/me` | The signed-in user |
| `GET` | `/api/users` | Admins only |
| `GET` | `/api/contacts` | `page`, `pageSize` (max 100), `sort` (`name`, `email`, `company`, `createdAt`), `order`, `q`, `companyId` |
| `GET` | `/api/contacts/{id}` | 404 for a contact the user may not see |
| `POST` | `/api/contacts` | 201; the creator owns it. 422 (validation, unknown company), 409 (e-mail taken) |
| `PATCH` | `/api/contacts/{id}` | Partial update: only the fields sent change; the owner never does |
| `GET` | `/api/companies` | `q`, `size`, `sort` (`name`, `industry`, `size`, `city`, `contactsCount`, `openDealsValue`), `order`, pagination |
| `GET` | `/api/companies/{id}` | With `contactsCount` and `openDeals {count, value}` |
| `GET` | `/api/deals` | Newest first; all visible deals in one page by default (the funnel board). `contactId`, `companyId` |
| `PATCH` | `/api/deals/{id}` | `{"stage": ...}`; closing stamps `closedAt`, reopening clears it |
| `GET` | `/api/activities?contactId=` | A contact's activities, newest first |
| `GET` | `/api/overview?period=` | `7d`, `30d` (default), `90d`, `12m`: KPIs with the previous period, funnel and revenue, aggregated in SQL |

Sellers only see the contacts they own; admins see everything. Companies are visible to everyone,
but their figures only count what the viewer may see. Text sorts follow Brazilian
Portuguese rules on both databases (`Ágata` next to `Agnes`).

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
