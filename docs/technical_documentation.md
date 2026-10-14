# Technical Documentation

## 1. System overview

The system is a React single-page application backed by a Flask REST API and a
MySQL relational database. External data sources are OpenWeather (location
search, current conditions, forecast) and NASA POWER (historical/daily
climate). Offline data engineering transforms NCVBDC annual dengue totals and
NASA POWER point observations into State/UT-year rows. An offline TensorFlow
trainer and Flask prediction integration exist, but the current workspace
does not have the complete model bundle required for inference.

```text
Browser (React/Vite)
  ├── AuthContext + Axios services
  ├── Public pages and role-protected workspaces
  └── React Router / lazy page chunks
          │ HTTPS in deployment; bearer JWT in API requests
          ▼
Flask app factory
  ├── Auth / weather / dashboard / reports / prediction / health blueprints
  ├── Weather and prediction services
  ├── SQLAlchemy repositories and models
  └── MySQL
       ├── users + token_blocklist
       ├── weather_history
       └── prediction_history

OpenWeather ── current/geocode/forecast
NASA POWER ─── historical climate and offline point observations
NCVBDC CSV ─── annual dengue cases and deaths
Offline ML ─── merge → preprocess → train (training incomplete)
```

## 2. Folder map

```text
backend/
  app/
    config/              Environment-based Flask configurations
    middleware/          Middleware extension point
    ml/
      dataset/            Climate acquisition and local data merging
      preprocessing/      Validation, features, split, scaling, reports
      models/             Saved ensemble, preprocessing artifacts and metrics
      evaluate_model.py   Held-out saved-model evaluation
      training.py         Standalone three-ANN training script
    models/               User, token, weather, prediction ORM models
    repositories/         Persistence queries
    routes/               Flask Blueprints
    services/             Weather providers and prediction service
    logging_config.py     Rotating application log setup
  migrations/             Alembic revisions 0001–0007
  tests/                  unittest API and ML pipeline tests
  requirements.txt
frontend/
  src/
    components/           Shared UI and dashboard elements
    context/              Authentication context
    layouts/              Dashboard shell
    pages/                Public, account, weather, prediction, admin pages
    services/             Axios API clients
    styles/               Shared page styles
    utils/                Validation and display helpers
  package.json
  nginx.conf
ops/                      Backup helpers and deployment checklist
docs/                     Submission reports and manuals
```

The current repository has additional empty extension-point packages; their
presence does not imply that the associated feature is implemented.

## 3. Technology and configuration

- Frontend: React 18, Vite, React Router, Axios, Bootstrap 5, React Icons,
  Chart.js, Leaflet / React Leaflet
- Backend: Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-JWT-Extended,
  Flask-Bcrypt, Flask-CORS
- Data/ML: pandas, NumPy, scikit-learn, Joblib, TensorFlow/Keras, Matplotlib
- Database: MySQL/PyMySQL; API tests use in-memory SQLite

`.env.example` documents configuration. Important values include
`DB_HOST/PORT/NAME/USER/PASSWORD`, `SECRET_KEY`, `JWT_SECRET_KEY`,
`FRONTEND_ORIGIN`, `OPENWEATHER_API_KEY`, `NASA_POWER_URL`,
`WEATHER_CACHE_TTL_SECONDS`, `WEATHER_RATE_LIMIT_PER_MINUTE`, `ML_MODEL_DIR`,
`ML_PROCESSED_DIR`, and `LOG_DIR`. Production mode rejects absent, short, or
identical signing keys. `.env` must remain private.

## 4. Authentication and roles

`users` stores account fields and a Bcrypt password hash. New public signups
receive the `user` role and must verify their email before login. Single-use
verification tokens are stored as hashes and expire after 24 hours. Password
recovery uses a one-hour signed token sent through the configured email
service. JWT access/refresh tokens are issued on verified login; revoked token
identifiers are stored in `token_blocklist`. The React client persists tokens
in local storage.

Admin-protected APIs support user and prediction management, analytics,
date-filtered system reports, isolated dataset uploads, climate-data browsing,
model status, and isolated training-job start/status. The training endpoint
does not activate generated artifacts as the production prediction model.
Account suspension and server infrastructure settings are not implemented.

## 5. Database schema

| Table | Main fields and relations |
| --- | --- |
| `users` | `id`, `full_name`, unique normalized `email`, `password_hash`, `phone`, `district`, `state`, `role`, `is_verified`, `created_at`, `updated_at`; role check permits `user` or `admin`. |
| `token_blocklist` | Unique JWT `jti`, token type, user FK, revoked and expiry timestamps. |
| `weather_history` | User FK, location/district, coordinates, record type, provider, observation/creation timestamps, normalized weather columns, JSON payload. |
| `prediction_history` | User FK, State/UT, annual climate input columns, predicted class, confidence, probability/recommendation JSON, prediction timestamp. |
| `email_verification_tokens` | User FK, unique token hash, expiry and creation timestamps. |
| `emergency_contacts` | One emergency-contact record per user. |
| `prescription_records` | User-owned prescription transcription records. |
| `user_preferences` | One row per user for alert, weekly-summary and dark-mode preferences. |

The linear migration chain is `0001_auth_tables`, `0002_weather_history`,
`0003_weather_observation_fields`, `0004_prediction_history`,
`0005_admin_patient_records`, `0006_user_preferences`, and
`0007_email_verification_tokens`. The configured database was upgraded and
verified at head `0007_email_verification_tokens`; the verification-token
table exists.

## 6. API reference

All routes are prefixed `/api`. Except the static district catalog and health
routes, application APIs require a bearer access JWT unless specified.

| Method | Endpoint | Access | Behavior |
| --- | --- | --- | --- |
| POST | `/auth/register` | Public | Validate and create user |
| POST | `/auth/email-verification` | Public | Consume a single-use, expiring verification token |
| POST | `/auth/email-verification/resend` | Public | Resend verification email with generic response |
| POST | `/auth/login` | Public | Issue access and refresh JWT |
| POST | `/auth/password-reset-request` | Public | Request password recovery by email |
| POST | `/auth/password-reset` | Public | Validate reset token and set password |
| GET/PUT | `/auth/profile` | Access JWT | Read/update allowed profile fields |
| GET/PUT | `/auth/settings` | Access JWT | Read/update saved user preferences |
| POST | `/auth/logout` | Access JWT | Revoke current and supplied refresh token |
| POST | `/auth/refresh` | Refresh JWT | Issue a new access token |
| POST | `/auth/change-password` | Access JWT | Change password after current-password verification |
| POST | `/admin/auth/login` | Public | Authenticate a verified administrator |
| POST | `/contact` | Public | Send contact form message when email is configured |
| GET/PUT/DELETE | `/profile/emergency-contact` | Access JWT | Manage current user's emergency contact |
| GET/POST | `/prescriptions` | Access JWT | List/create current user's prescription records |
| PUT/DELETE | `/prescriptions/{record_id}` | Access JWT | Update/delete one current user's prescription record |
| GET | `/weather/districts` | Public | Approximate Karnataka district-centre catalog |
| GET | `/weather/search` | Access JWT | Search/reverse-geocode a location |
| GET | `/weather/current` | Access JWT | OpenWeather current observation |
| GET | `/weather/forecast` | Access JWT | OpenWeather forecast |
| GET | `/weather/history` | Access JWT | NASA POWER historical observations |
| GET | `/dashboard` | Access JWT | Current weather plus saved weather/prediction summaries |
| GET | `/reports/weather` | Access JWT | Weather history for current account |
| GET | `/reports/statistics` | Access JWT | Current-account weather counts and trends |
| POST | `/prediction/predict` | Access JWT | Validate annual inputs, infer if model available, save result |
| GET | `/prediction/history` | Access JWT | Paginated history; admin can see all prediction records |
| DELETE | `/prediction/history/{id}` | Access JWT | Delete own record, or any record as admin |
| GET | `/prediction/latest` | Access JWT | Latest record for user, or latest overall for admin |
| GET | `/prediction/model-info` | Access JWT | Model metadata/availability |
| GET/POST | `/admin/users` | Admin JWT | Search and create accounts |
| PATCH/DELETE | `/admin/users/{user_id}` | Admin JWT | Update/delete one account |
| GET | `/admin/predictions` | Admin JWT | List prediction records |
| GET/DELETE | `/admin/predictions/{prediction_id}` | Admin JWT | Inspect/delete one prediction |
| GET | `/admin/dashboard` | Admin JWT | System overview |
| GET | `/admin/analytics` | Admin JWT | Prediction, user, and weather analytics |
| GET | `/admin/reports` | Admin JWT | Date-filtered system-wide aggregates |
| GET/POST | `/admin/datasets` | Admin JWT | List/upload isolated CSV files |
| DELETE | `/admin/datasets/{relative_path}` | Admin JWT | Delete an isolated CSV upload |
| GET | `/admin/climate-data` | Admin JWT | Browse stored weather/climate records |
| GET | `/admin/model-status` | Admin JWT | Inspect prediction and training model status |
| POST | `/admin/model-training` | Admin JWT | Start training job |
| GET | `/admin/model-training/{job_id}` | Admin JWT | Retrieve training-job status |
| GET/POST | `/prediction` | Deprecated | Returns `410 Gone`; use `/prediction/predict` and `/prediction/history` |
| GET | `/health` | Public | Liveness |
| GET | `/health/database` | Public | Database readiness |
| GET | `/health/model` | Public | Model readiness |
| GET | `/health/weather` | Public | Weather-key readiness |
| GET | `/health/system` | Public | CPU/memory/disk and dependency status |

`backend/openapi.yaml` documents the implemented API operations and access
requirements. It is maintained alongside the Flask blueprints rather than
generated automatically.

## 7. Weather data workflow

Location search resolves a user query through OpenWeather; current and
forecast requests normalize source values into consistent API fields.
Historical requests query NASA POWER. Successful responses are persisted with
user ownership in `weather_history`. The cache and limiter are process-local,
so a multi-worker deployment does not share their state. Current and forecast
provider availability requires an OpenWeather key; NASA POWER is external and
can fail independently.

## 8. ML and prediction workflow

1. NCVBDC annual wide data is normalized to State/UT, year, confirmed cases,
   and deaths.
2. NASA POWER daily observations are grouped by State/UT and year.
3. Local preprocessing imputes missing climate values and produces features,
   train/test files, a scaler, and label encoder.
4. The target labels use explicit annual case-count thresholds:
   `Low Risk < 1,000`, `Moderate Risk 1,000–9,999`, and
   `High Risk >= 10,000`.
5. The standalone trainer defines three neural networks, early stopping,
   checkpointing, evaluation, and soft voting.
6. The Flask service expects `ensemble_model.keras`, `scaler.pkl`,
   `label_encoder.pkl`, and compatible feature schema metadata.
7. The trained model bundle is present under `backend/app/ml/models/`; its
   scaler and label encoder are checked against the processed feature order and
   class outputs at startup. The current prediction integration test confirms
   successful inference and saved history.

The generated annual dataset has 190 rows (152 training, 38 test) across
2021–2026; its risk labels are 88 Low, 67 Moderate, 35 High. The 2026 climate
series is year-to-date. Each State/UT climate point uses one representative
coordinate and is not a statewide spatial average. The data size and
temporal/label construction do not support a validated operational outbreak
forecast claim.

The saved three-network soft-voting ensemble was evaluated against the existing
38-row held-out test split without retraining. The saved StandardScaler contains
47 numeric feature columns (the year feature is not scaled); the model consumes
48 ordered features, and its three output units align with the saved label
encoder classes (`High Risk`, `Low Risk`, `Moderate Risk`). Test data are already
preprocessed/scaled and are not scaled again.

| Metric | Held-out result |
| --- | ---: |
| Accuracy | 0.6579 |
| Precision, macro | 0.6295 |
| Recall, macro | 0.6001 |
| F1-score, macro | 0.6093 |
| ROC AUC, macro one-vs-rest | 0.8798 |

Confusion matrix (rows actual, columns predicted; class order High, Low,
Moderate): `[[3, 0, 4], [1, 15, 2], [1, 5, 7]]`. Run
`python -m backend.app.ml.evaluate_model` to re-evaluate and regenerate
`models/evaluation_metrics.json`, `models/confusion_matrix.png`,
`models/roc_curve.png`, and `models/evaluation_report.html`. The command also
adds a link to the current test evaluation in `models/training_report.html`.
Repeated inference is checked for deterministic output; artifact and test CSV
SHA-256 digests are saved for provenance. This is a random small-sample test
split, not temporal/external validation; labels are threshold-derived, 2026 is
partial-year, and probabilities are not calibrated. Results must not be
presented as validated future outbreak prediction.

## 9. Performance and optimization status

Existing measures include lazy-loaded React routes, a Vite production build
with separate page chunks, a short-lived process-local weather cache,
SQL indexes for account/time/state/risk lookups, rotating log files, one-time
model loading per Flask app, and Nginx static asset caching. In the measured
build, the main JavaScript chunk is about 263 kB (about 86 kB gzip); the map
and chart chunks are separate and are about 160 kB and 173 kB respectively
before gzip.

No production traffic or representative load test was available, so API
latency, database query duration, TensorFlow inference latency, and memory
peaks have not been measured. Recommended next steps are shared Redis
cache/limiting, query-plan checks against MySQL data volume, authentication
abuse controls, protected detailed health probes, real-user performance
measurement, and bundle profiling before removing dependencies.

## 10. Deployment and operations

The Compose files, Python and Nginx Dockerfiles, CI workflow, OpenAPI YAML,
health routes, and operator backup scripts are present. Docker was not
installed in the validation environment, so images/Compose were not built.
Production startup does not automatically apply database migrations; run
`flask --app backend.run db upgrade` as an explicit, reviewed release step
before traffic. The CI workflow runs Python tests and frontend tests/builds.

Use [the deployment checklist](../ops/deployment-checklist.md) for production
controls. The Compose configuration is an unverified starting point, not a
certified deployment.
