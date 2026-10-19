# Orbit Platform

A large-scale backend system for ride-hailing, food delivery, and multi-service operations.

- `drivers` - driver profiles, approval, online/offline, location updates, nearby search
- `rides` - ride requests, matching to the nearest driver, fare estimate, trip lifecycle

Stack: Python 3.14, Django 6.1, Django REST Framework, PostgreSQL 17.

## Getting started

You need [uv](https://docs.astral.sh/uv/) and Docker.

```bash
docker compose up -d
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

`docker compose up -d` only starts Postgres. To run the whole thing in containers:

```bash
docker compose --profile app up -d --build
curl localhost:8000/health/
```

Need some data to play with? This creates 10k fake drivers around Ho Chi Minh City:

```bash
uv run python manage.py seed_drivers --count 10000
```

## Tests and linting

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The tests need the Postgres container running. CI runs the same commands.

## Configuration

Settings come from environment variables. Defaults are fine for local development.

- `DJANGO_DEBUG` - `1` by default, set to `0` in production
- `DJANGO_SECRET_KEY` - required when debug is off
- `DJANGO_ALLOWED_HOSTS` - comma separated, defaults to `localhost,127.0.0.1`
- `DJANGO_SSL_REDIRECT` - on by default when debug is off
- `DJANGO_HSTS_SECONDS` - `0` by default
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
