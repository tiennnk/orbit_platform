# Orbit Platform

Ride-hailing and food delivery platform: a Django REST API on PostgreSQL and a React web app.

Riders book trips and order food, drivers take rides and deliveries, restaurants manage menus and orders, and admins approve partners. A chat assistant answers questions about nearby food and the user's orders.

## Features

- Rides: pick pickup and drop-off on the map or by search, see the fare, book, watch the driver come with a live ETA, rate the driver, browse trip history.
- Food: find restaurants nearby, build a cart, get a delivery quote, place an order and track it from the kitchen to the door.
- Drivers: register, go online and share location, accept or decline offers within 15 seconds, run trips and deliveries.
- Restaurants: sign up, edit the menu, open and close, accept or reject orders, search for a driver again if none was found.
- Admin: approve, reject, suspend and reinstate drivers and restaurants.
- Assistant: a chat box that looks up restaurants, dishes under a price and the user's orders through tool calls. Runs on Claude or any OpenAI-compatible API such as OpenRouter or Ollama.
- Accounts: sign up, log in, change password.

## How it is built

- Each Django app is split into domain, models, selectors (reads), services (writes) and API. Views hold no business logic.
- Models own their state changes (`approve`, `accept`, `complete`), and Postgres enforces the rules too, with check constraints and partial unique indexes such as one active ride per rider and one pending offer per driver.
- Dispatch is safe under concurrent requests without a job queue: rows are locked with `select_for_update(skip_locked=True)`, and expired offers move on to the next driver when clients poll.
- A food delivery is a ride with `service="food"`, so it reuses the whole dispatch flow. Order lines keep a snapshot of the dish name and price.
- Nearby search filters by a bounding box on indexed coordinates, then ranks by haversine distance with a heap for the top results.
- The assistant calls models through a small provider interface, so switching vendors is a config change.
- Place search results are cached, the OpenStreetMap import retries with backoff, and sensitive endpoints are rate limited.
- The OpenAPI schema is generated from the code and committed. Frontend types are generated from it, and CI fails when it is out of date.

## Stack

- Backend: Python 3.14, Django 6, Django REST Framework, PostgreSQL 17, pytest (about 430 tests), ruff
- Frontend: React 19, TypeScript, Vite, TanStack Query, Leaflet
- Infra: Docker Compose, GitHub Actions
- Data: OpenStreetMap through Photon and Overpass

Code layout:

- `backend/apps/accounts` - sign up, log in, password change, token auth
- `backend/apps/drivers` - driver profiles, approval, availability, location, nearby search
- `backend/apps/rides` - requests, offers, dispatch, tracking, trip lifecycle, ratings
- `backend/apps/food` - restaurants, menus, orders, OpenStreetMap import
- `backend/apps/places` - place and address search for the map
- `backend/apps/assistant` - chat assistant and its tools
- `frontend/` - web app for riders, drivers, restaurants and admins

## Getting started

You need [uv](https://docs.astral.sh/uv/), Node 24 and Docker.

Backend (copy `backend/.env.example` to `backend/.env` and fill it in first, see Configuration below):

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

Settings come from environment variables or `backend/.env` (see `.env.example`). Fill in the values you need and delete the lines you don't; missing ones fall back to defaults that work for local development.

- `DJANGO_DEBUG` - `1` by default, set to `0` in production
- `DJANGO_SECRET_KEY` - required when debug is off
- `DJANGO_ALLOWED_HOSTS` - comma separated, defaults to `localhost,127.0.0.1`
- `DJANGO_SSL_REDIRECT` - on by default when debug is off
- `DJANGO_HSTS_SECONDS` - `0` by default
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- `ASSISTANT_PROVIDER` - `openai` (any OpenAI-compatible API) or `anthropic`
- `ASSISTANT_MODEL` - defaults to `nvidia/nemotron-3-ultra-550b-a55b:free` for `openai` and `claude-opus-5-5` for `anthropic`
- `ASSISTANT_BASE_URL` - defaults to OpenRouter, `http://localhost:11434/v1` for Ollama
- `ASSISTANT_API_KEY` - key for the OpenAI-compatible API
- `ANTHROPIC_API_KEY` - key for Claude when the provider is `anthropic`
