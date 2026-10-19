# Orbit Platform

A large-scale backend system for ride-hailing, food delivery, and multi-service operations.

The repo has two parts:

- `backend/` - Django + Django REST Framework API on PostgreSQL 17
- `frontend/` - React + TypeScript web app (Vite) for riders, drivers and admins

Backend apps:

- `drivers` - driver profiles, approval, online/offline, location updates, nearby search
- `rides` - ride requests, offers to nearby drivers (accept, decline, timeout), fare estimate, driver tracking with ETA, trip lifecycle, rating drivers after a trip
- `food` - restaurants, menus, approval, nearby search and an OpenStreetMap import
- `accounts` - sign up, log in, change password, token auth
- `places` - place and address search for the map, backed by Photon (OpenStreetMap data)

## Getting started

You need [uv](https://docs.astral.sh/uv/), Node 24 and Docker.

Backend:

```bash
docker compose up -d
cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

API docs are at http://localhost:8000/api/docs/.

Frontend, in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend on port 8000, so both need to be running. Sign up as a normal user to request rides and browse food. Use "Become a driver" or "Open a restaurant" to register as a partner. Log in with the superuser to approve drivers and restaurants in the Admin tab.

The TypeScript API types are generated from `backend/openapi.yaml`. After changing an endpoint, regenerate it:

```bash
cd backend
uv run python manage.py spectacular --file openapi.yaml
```

Map search goes through the backend to the public Photon server at photon.komoot.io. Results are cached for a day. The public server is meant for light use, so point `GEOCODER_URL` at your own Photon instance for real traffic.

`docker compose up -d` only starts Postgres. To run the whole thing in containers, from the repo root:

```bash
docker compose --profile app up -d --build
curl localhost:8000/health/
```

Need some data to play with? This creates 200 fake drivers around Ho Chi Minh City (run inside `backend/`):

```bash
uv run python manage.py seed_drivers
uv run python manage.py seed_drivers --count 50000
uv run python manage.py seed_drivers --clear
```

Running it again replaces the previous batch. `--clear` removes them. Seeded locations go stale after a minute, so they won't be matched to rides unless you seed right before testing.

For food, `import_restaurants` pulls real restaurants, cafes and fast food places from OpenStreetMap through the Overpass API (100 within 3 km of District 1 by default). Names, locations, phone numbers and addresses come from OSM, with missing addresses filled in by a reverse lookup. OSM has no menus, so each place gets a sample menu picked from its name or cuisine. It takes a minute or two because the public Overpass server is slow and often busy; the command retries on its own.

```bash
uv run python manage.py import_restaurants
uv run python manage.py import_restaurants --latitude 21.0285 --longitude 105.8542 --radius-km 2
uv run python manage.py import_restaurants --clear
```

Restaurant data is from OpenStreetMap contributors, available under the ODbL.

## Tests and linting

```bash
cd backend
uv run pytest
uv run ruff check .
uv run ruff format --check .

cd ../frontend
npm run lint
npm run build
```

The backend tests need the Postgres container running. CI runs the same commands and also fails if `openapi.yaml` is out of date.

## Configuration

Settings come from environment variables. Defaults are fine for local development.

- `DJANGO_DEBUG` - `1` by default, set to `0` in production
- `DJANGO_SECRET_KEY` - required when debug is off
- `DJANGO_ALLOWED_HOSTS` - comma separated, defaults to `localhost,127.0.0.1`
- `DJANGO_SSL_REDIRECT` - on by default when debug is off
- `DJANGO_HSTS_SECONDS` - `0` by default
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
