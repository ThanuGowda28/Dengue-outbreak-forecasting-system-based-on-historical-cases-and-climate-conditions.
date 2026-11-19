# Production Deployment Guide

This repository supports Docker Compose on a single VM or container host, a
Railway Docker backend, and a Vercel static frontend. Compose runs React behind
Nginx, proxies `/api` to Gunicorn/Flask, and keeps MySQL on a private Docker
network.

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
- `DATABASE_URL` using MySQL, or `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`,
  and `DB_PASSWORD`
- `OPENWEATHER_API_KEY`
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`,
  `MAIL_PASSWORD`, and `MAIL_DEFAULT_SENDER`
- `REDIS_URL`, or `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`, pointing to a private Redis
  service. Docker Compose provides Redis internally; other deployment platforms
  must provision Redis and background worker/Beat processes.
- `MOSQUITO_DETECTOR_PATH` pointing to a compatible, trained YOLO weights file.
  No mosquito detector weights are included in this repository. Deploy a
  model trained with the class names listed in
  `backend/app/services/detection_model.py`; the analysis endpoint returns
  `503 model_unavailable` until those weights and the inference packages are
  installed.
- SMTP TLS settings (`MAIL_USE_TLS` or `MAIL_USE_SSL`, but not both)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` to enable
  SMS delivery. SMS remains disabled for users until they opt in.
- `ML_MODEL_DIR` and `ML_PROCESSED_DIR` if using locations other than the
  container defaults

Production startup fails if required secrets, MySQL settings, HTTPS CORS
origins, OpenWeather, SMTP settings, or Redis settings are missing or invalid.
If TensorFlow or its model artifacts cannot load, model prediction endpoints
return an explicit unavailable response while experimental trend forecasting
continues to work. Never use development secret
values, localhost CORS origins, or an empty database password in production.
Configure managed-MySQL TLS/CA settings according to the provider's
instructions, and do not expose MySQL publicly.

The frontend defaults to the same-origin `/api` path. Docker builds it with
`VITE_API_BASE_URL=/api`, and Nginx proxies that prefix to the backend. For a
separate frontend host, set `VITE_API_BASE_URL` to the deployed HTTPS API URL
at frontend build time and set backend `FRONTEND_ORIGIN` to the exact frontend
origin.

## Build, migrate, and start

Run from the repository root with a completed production `.env`. Compose runs
the migration service once and waits for it to complete before starting the API:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The Compose MySQL volume persists database data; configure encrypted
off-host backups and test restoration.

Mosquito image uploads are stored privately under the persistent
`detection_data` backend volume;
image retrieval requires the owning user's JWT or an administrator JWT. Back up
or retain this volume according to the deployment's data-retention policy.
Install the CPU/GPU-compatible PyTorch build for the target host before
deploying Ultralytics weights. The detector label vocabulary includes standing
or stagnant water, tires, buckets, flower pots, tanks, drains, low-risk/dry
containers, and explicit no-breeding-site labels. Calibrate and validate the
trained model before using scores for operational public-health decisions.

Compose starts a private, persistent Redis instance, an alert worker, and a
Celery Beat scheduler alongside the API. The worker retries failed deliveries
up to three times; Beat queues opted-in daily email summaries at 09:00 UTC.
For a non-Compose deployment, run one worker and one Beat process with the same
application image, database, Redis, SMTP, and Twilio environment:

```powershell
celery -A backend.celery_worker:celery worker --loglevel=info
celery -A backend.celery_worker:celery beat --loglevel=info
```

Use the `alert-worker` and `alert-beat` Compose service logs to troubleshoot
delivery. Alert settings and history are available under `/api/alerts`; test
with a verified account, an eligible prediction, valid SMTP/Twilio credentials,
and an opted-in SMS preference before enabling real user notifications.

## Verify deployment

Check container health and the public same-origin API:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
Invoke-RestMethod https://your-frontend.example.com/api/health
Invoke-RestMethod https://your-frontend.example.com/api/health/database
Invoke-RestMethod https://your-frontend.example.com/api/health/model
Invoke-RestMethod https://your-frontend.example.com/api/health/weather
```

The backend container health check calls `/api/health` for liveness; model
health is independently reported by `/api/health/model`. Verify database
health reports `available`, and weather health reports `configured: true`.
Weather health checks
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
`/api/health` as its liveness endpoint. Connect the repository in
Render, select the root Blueprint, and create the service. Render generates
distinct Flask/JWT secrets; configure all `sync: false` variables in the
Render dashboard before the first successful deploy. Provision external MySQL
and Redis services and set `DATABASE_URL` and `REDIS_URL`; Render does not
provide the MySQL service used by this app.

Allow the external database and Redis services to accept connections from
Render. Supply a valid OpenWeather key and SMTP host/from address as well.
The configured pre-deploy command applies database migrations once before
the service update; normal app startup does not race migrations across replicas.
For asynchronous alert delivery, add two Render Background Worker services
using the same repository Dockerfile and production environment: run
`celery -A backend.celery_worker:celery worker --loglevel=info` for the worker
and `celery -A backend.celery_worker:celery beat --loglevel=info` for the
scheduler. Use the same `DATABASE_URL`, `REDIS_URL`, signing keys, SMTP,
frontend origin, and weather key on each service.

After deployment, copy the assigned `https://<service>.onrender.com` URL and
set `FRONTEND_ORIGIN` to the exact HTTPS origin serving the frontend. Save the
setting and redeploy. Check `/api/health`, `/api/health/database`,
`/api/health/model`, and `/api/health/weather`; then perform authenticated
weather, prediction, login, and report requests against the deployed URL.
Swagger UI is available at `/api/docs`, and the raw OpenAPI document is at
`/api/openapi.yaml`. Render's dashboard provides build and runtime deployment
logs.

## Deploy the backend to Railway and frontend to Vercel

### Railway backend

Create a Railway project from the connected GitHub repository and configure
the service to use the repository root. The root `railway.toml` selects
`backend/Dockerfile`; the Docker image uses Python 3.12, installs
`backend/requirements.txt` (including Gunicorn), binds Gunicorn to Railway's
`PORT`, applies migrations with its pre-deploy command, and uses `/api/health`
as its liveness probe. Add a Railway
MySQL service to the same project and set the backend service variables
`DATABASE_URL` and `REDIS_URL` from the MySQL and Redis service connection
values. The Flask configuration validates a MySQL URL and does not silently
fall back to SQLite in production.

Set these backend variables through Railway's Variables panel; do not put
secret values in `railway.toml`:

- `APP_ENV=production`
- `SECRET_KEY` and `JWT_SECRET_KEY`: distinct random values, at least 32
  characters each
- `DATABASE_URL` as a MySQL URL
- `REDIS_URL` for the Celery broker and result backend (or separate
  `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`)
- `AUTO_MIGRATE_DATABASE=false`
- `OPENWEATHER_API_KEY`
- `MAIL_SERVER=smtp.gmail.com`, `MAIL_PORT=587`, `MAIL_USE_TLS=true`,
  `MAIL_USERNAME`, `MAIL_PASSWORD`, and `MAIL_DEFAULT_SENDER`
- `FRONTEND_ORIGIN`: the exact Vercel HTTPS origin after the frontend deploys
- `MAIL_USE_SSL=false` for Gmail. Use a Gmail App Password rather than your
  account password, and set `MAIL_DEFAULT_SENDER` to the same address as
  `MAIL_USERNAME`.

For local Gmail delivery, copy these values into the root `.env` (replace the
address and app-password placeholder with your own private values):

```dotenv
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-gmail-address@gmail.com
MAIL_PASSWORD=your-16-character-gmail-app-password
MAIL_DEFAULT_SENDER=your-gmail-address@gmail.com
```

Create a Gmail App Password in your Google Account after enabling 2-Step
Verification. Do not put the account password here, share the App Password, or
commit `.env`.

The pre-deploy command runs migrations once before the service update. Keep
one backend replica unless you configure shared storage for the process-local
rate limits and weather cache. Prediction endpoints return an explicit
unavailable response if TensorFlow/model loading fails; trend forecasting
remains available.

### Vercel frontend

Create a Vercel project connected to the same repository and set its Root
Directory to `frontend`. The `frontend/vercel.json` configures the Vite build
and SPA fallback. Set `VITE_API_BASE_URL` in Vercel's Production environment to
the Railway backend's full API base URL, for example
`https://<railway-service-domain>/api`, then redeploy the frontend. This is a
public API address, not a secret. Do not rely on the `/api` fallback for a
separate Vercel and Railway origin.

After Vercel assigns its production URL, add that exact HTTPS origin to the
Railway backend's `FRONTEND_ORIGIN` value and redeploy the backend. The Vercel
SPA routes `/login` and `/admin/login` should load directly.

### Smoke verification

Use the actual assigned service domains:

- Backend liveness: `https://<railway-service-domain>/api/health`
- Database: `https://<railway-service-domain>/api/health/database`
- Model: `https://<railway-service-domain>/api/health/model`
- Weather configuration: `https://<railway-service-domain>/api/health/weather`
- Swagger UI: `https://<railway-service-domain>/api/docs`
- OpenAPI: `https://<railway-service-domain>/api/openapi.yaml`
- User sign-in page: `https://<vercel-domain>/login`
- Admin sign-in page: `https://<vercel-domain>/admin/login`

Then test user/admin sign-in, email verification delivery, authenticated
weather requests, a prediction request, and report requests against production.
The health endpoint does not establish that authentication, SMTP delivery, or
live weather calls work. Promote an existing account to admin with
`flask --app backend.run admin promote <registered-email>` after verifying its
identity; never provision a default admin password in deployment config.
Check build and runtime logs in Railway's deployment view and Vercel's
deployment logs.

## Scaling notes

Weather caching and rate limiting are process-local. The included Compose
configuration uses one Gunicorn worker; do not scale to multiple workers or
replicas if globally consistent cache and rate limits are required. Add shared
cache/rate-limit storage before horizontal scaling. Tune memory and request
timeouts only after measuring TensorFlow startup and inference on the target
host.
