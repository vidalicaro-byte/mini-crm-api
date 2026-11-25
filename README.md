# Mini-CRM API

REST API for the [Mini-CRM](https://github.com/vidalicaro-byte/mini-crm) front end, built with FastAPI.

> Work in progress. The full README (English and Portuguese) comes with the first release.

## Run locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run fastapi dev src/crm_api/main.py
```

Interactive docs: http://127.0.0.1:8000/docs

## Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

## License

[MIT](LICENSE)
