# Production Deployment Guide

This repository supports Docker Compose on a single VM or container host and
a Render Docker Web Service for the backend. Compose runs the React frontend
behind Nginx, proxies `/api` to Gunicorn/Flask, and keeps MySQL on a private
Docker network. No Vercel or Procfile deployment is included.

## Prerequisites

- Docker Engine with the Compose plugin.
- A registered DNS name and HTTPS termination at a trusted reverse proxy or
  load balancer.
- A production SMTP account for verification and recovery email.
- A valid OpenWeather API key. Historical climate observations use NASA POWER.
- A backup plan for the MySQL database and persistent volumes.

The backend image uses Python 3.12 and installs Gunicorn and application
dependencies from `backend/requirements.txt`. The frontend image uses Node 22
to build the Vite bundle and Nginx to serve it.

## Configure environment variables

Copy `.env.production.example` to `.env` on the deployment host. Do not commit
the resulting `.env` file or paste secrets into source control. Generate two
different random secrets of at least 32 characters for `SECRET_KEY` and
`JWT_SECRET_KEY`; use the deployment platform's secret store where available.
Replace every example/placeholder value before starting the application.

Set and verify:

- `APP_ENV=production`
- Unique `SECRET_KEY` and `JWT_SECRET_KEY`
- `FRONTEND_ORIGIN` as a comma-separated list of exact HTTPS frontend origins
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`
- `OPENWEATHER_API_KEY`
- `MAIL_SERVER`, `MAIL_PORT`, and `MAIL_FROM`; when SMTP authentication is
  used, set both `MAIL_USERNAME` and `MAIL_PASSWORD`
- SMTP TLS settings (`MAIL_USE_TLS` or `MAIL_USE_SSL`, but not both)
- `ML_MODEL_DIR` and `ML_PROCESSED_DIR` if using locations other than the
  container defaults

Production startup fails if required secrets, MySQL settings, HTTPS CORS
origins, OpenWeather, SMTP server/from settings, or the saved TensorFlow model,
scaler, and label encoder are missing or invalid. Never use development secret
values, localhost CORS origins, or an empty database password in production.
Configure managed-MySQL TLS/CA settings according to the provider's
instructions, and do not expose MySQL publicly.

The frontend defaults to the same-origin `/api` path. Docker builds it with
`VITE_API_BASE_URL=/api`, and Nginx proxies that prefix to the backend. For a
separate frontend host, set `VITE_API_BASE_URL` to the deployed HTTPS API URL
at frontend build time and set backend `FRONTEND_ORIGIN` to the exact frontend
origin.

## Build, migrate, and start

Run from the repository root with a completed production `.env`:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d mysql
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backend flask --app backend.run db upgrade
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Run the migration once as a release step, not concurrently from every backend
replica. The Compose MySQL volume persists database data; configure encrypted
off-host backups and test restoration.

## Verify deployment

Check container health and the public same-origin API:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
Invoke-RestMethod https://your-frontend.example.com/api/health
Invoke-RestMethod https://your-frontend.example.com/api/health/database
Invoke-RestMethod https://your-frontend.example.com/api/health/model
Invoke-RestMethod https://your-frontend.example.com/api/health/weather
```

The backend container health check calls `/api/health/model`; the container
does not become healthy unless TensorFlow and the saved model artifacts load.
Verify database health reports `available`, model health reports `available`,
and weather health reports `configured: true`. Weather health checks
configuration only; make authenticated current/forecast calls to verify
provider connectivity and quota. Confirm browser requests use HTTPS and the
expected API origin. Provider and database credentials must remain server-side.

## Tests and production checks

From the repository root:

```powershell
python -m pip check
python -m unittest discover -s backend/tests -v
Set-Location frontend
npm ci
npm test
npm run build
```

The local test suite does not prove DNS, SMTP delivery, managed-MySQL
connectivity/TLS, reverse-proxy TLS, provider quotas, or cloud resource sizing.
Validate those in staging before release.

## Deploy the backend to Render

The root `render.yaml` defines a Docker Web Service using
`backend/Dockerfile`, Python 3.12, Gunicorn, Render's assigned `PORT`, and
`/api/health/model` as the readiness endpoint. Connect the repository in
Render, select the root Blueprint, and create the service. Render generates
distinct Flask/JWT secrets; configure all `sync: false` variables in the
Render dashboard before the first successful deploy.

Render does not provide the MySQL service used by this app. Supply `DB_HOST`,
`DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` for an externally hosted
MySQL database and allow connections from Render. Verify the database
provider's TLS requirements; the application currently has no dedicated
MySQL CA/SSL environment setting. Supply a valid OpenWeather key and SMTP
host/from address as well.

After deployment, copy the assigned `https://<service>.onrender.com` URL and
set `FRONTEND_ORIGIN` to the exact HTTPS origin serving the frontend. Save the
setting and redeploy. Check `/api/health`, `/api/health/database`,
`/api/health/model`, and `/api/health/weather`; then perform authenticated
weather, prediction, login, and report requests against the deployed URL.
Swagger UI is available at `/api/docs`, and the raw OpenAPI document is at
`/api/openapi.yaml`. Render's dashboard provides build and runtime deployment
logs.

Run `flask --app backend.run db upgrade` once against production MySQL before
using the service. Do not run migrations concurrently from each replica.

## Scaling notes

Weather caching and rate limiting are process-local. The included Compose
configuration uses one Gunicorn worker; do not scale to multiple workers or
replicas if globally consistent cache and rate limits are required. Add shared
cache/rate-limit storage before horizontal scaling. Tune memory and request
timeouts only after measuring TensorFlow startup and inference on the target
host.
