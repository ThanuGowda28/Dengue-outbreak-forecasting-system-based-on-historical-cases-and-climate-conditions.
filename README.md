# Dengue Outbreak Forecasting System

Starter architecture for the **Ensemble Neural Network Approach to Forecast Dengue Outbreak Based on Climate Conditions** final-year engineering project.

This repository contains a React/Vite frontend and Flask API. The authentication module supports anonymous public visitors, registered users, and administrators. Authenticated weather APIs provide current and forecast conditions from OpenWeather and daily history from NASA POWER. A trained three-network ensemble and its preprocessing artifacts are present and loaded by the prediction API. Its held-out test evaluation is documented as preliminary research evidence, not as validated operational outbreak forecasting.

## Project structure

```text
.
├── backend/
│   ├── app/
│   │   ├── config/
│   │   ├── middleware/
│   │   ├── ml/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── uploads/
│   │   ├── utils/
│   │   ├── __init__.py
│   │   └── extensions.py
│   ├── config/
│   ├── instance/
│   ├── requirements.txt
│   └── run.py
└── frontend/
    ├── public/
    ├── src/
    │   ├── assets/
    │   ├── components/
    │   ├── context/
    │   ├── hooks/
    │   ├── layouts/
    │   ├── pages/
    │   ├── services/
    │   ├── styles/
    │   └── utils/
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## Prerequisites

- Python 3.10–3.12
- Node.js 20.19+ (or 22.12+) and npm
- MySQL 8.0 or newer

TensorFlow and its supported Python versions can vary by operating system. If your platform does not provide a compatible TensorFlow wheel, follow the TensorFlow installation guidance for that platform.

## Setup

### 1. Configure environment

From the project root, copy `.env.example` to `.env` and replace the
placeholder secrets and database credentials. Keep `.env` private and out of
version control. For production, set `APP_ENV=production` and remove
`FLASK_DEBUG`; the app requires distinct signing keys of at least 32 characters.

Create the MySQL database and application user, then grant that user access to the project database. The backend uses `mysql+pymysql` and reads its connection settings from the environment.

### 2. Start the backend

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
flask --app backend.run run --debug
```

The API is available at `http://localhost:5000`; its health endpoint is
`http://localhost:5000/api/health`. In development, local demo mode is enabled
by default: registration is auto-verified if SMTP is missing or delivery fails,
and password recovery displays a one-hour reset link when email cannot be sent.
Testing and production configurations do not enable this fallback.

Apply the checked-in database migrations after installing dependencies:

```powershell
flask --app backend.run db upgrade
```

The migrations create the existing user/token tables and per-user weather
history table. Weather history stores queryable district, weather date, and
climate scalar columns alongside the normalized provider payload (so complete
forecast/history series are retained). For future model changes, create a revision with
`flask --app backend.run db migrate -m "Describe the change"` and apply it with
`flask --app backend.run db upgrade`.

Set `OPENWEATHER_API_KEY` to enable geocoding, current weather, and forecast
requests. Historical observations use NASA POWER, configured by `NASA_POWER_URL`.
The development environment example intentionally leaves this credential blank;
put your own OpenWeather key in `backend/.env` and restart Flask. The weather
screen reports provider configuration/network errors instead of showing sample
conditions when the service is unavailable.
`WEATHER_CACHE_TTL_SECONDS` controls the process-local provider-response cache
(default 300 seconds); set it to `0` to disable caching. Authenticated weather
endpoints are rate-limited per user. Deployments with multiple Flask workers
should use shared cache and rate-limit infrastructure if limits must be global.
NASA POWER surface pressure (`PS`) is returned in kPa and normalized to hPa to
match the units used by the current weather and forecast APIs.
The search field provides debounced city suggestions through the authenticated
geocoding endpoint. Weather responses are cached briefly and rate-limited per
authenticated user. The cache and rate limiter are process-local; deployments
with multiple application workers should use a shared cache/rate-limit backend
to enforce consistent limits and cache entries across workers.

Current weather and the five-day forecast use OpenWeather's geocoding and
weather APIs; historical daily climate data uses NASA POWER. The frontend sends
these requests through the Flask API with the stored bearer access token; the
provider key remains server-side. Missing or rejected credentials, provider
timeouts, provider rate limits, and malformed responses return explicit API
errors rather than demonstration data. Invalid OpenWeather credentials return
HTTP 503 without exposing the key. Historical requests must end before today
and cover no more than 90 days. NASA POWER may not yet have observations for
the most recent dates; use a date range with published data if the requested
range has no valid temperature observations. An entirely unpublished range is
reported as HTTP 503; partial ranges return the available daily observations.

### Administrator and personal-record APIs

An existing administrator account can sign in through `/admin/login`. To bootstrap
the first administrator, create a normal account and run
`flask --app backend.run admin promote user@example.com` from the project root;
this operator-only command requires database access and grants the selected
existing account administrator privileges.

Administrator routes under `/api/admin` provide a dashboard, paginated user
management, prediction review/deletion, and aggregate reports. All routes other
than `/api/admin/auth/login` require an access token whose account currently has
the administrator role.

Authenticated users can manage their own emergency contact through
`/api/profile/emergency-contact` and clinician-issued prescription records
through `/api/prescriptions`. Prescription fields are for transcription only;
the application does not generate or validate treatment advice. The optional
emergency-contact QR is generated in the browser and contains only the contact
name and phone number. Anyone who scans a displayed QR can read that information.

### 3. Start the frontend

In a separate terminal:

```powershell
cd frontend
npm install
npm run dev
```

Vite serves the frontend at `http://localhost:5173`. The Axios client reads its base URL from `VITE_API_BASE_URL`.

## Frontend experience

The public home page includes project information, dengue and climate education,
FAQs, and a contact form that sends email when configured. The registered-user
workspace includes live weather, stored weather history, a district location
map, climate-input predictions, profile, settings, emergency contacts, and
prescription records. Dashboard alerts and reports use saved, account-scoped
data. Administrators can manage users and predictions, review system reports
and climate data, manage isolated dataset uploads, inspect model readiness,
and launch isolated training jobs. The classifier is available, but its
case-count labels and small random held-out evaluation do not establish a
validated future outbreak forecast.

Dashboard routes require authentication; admin tools are role-gated in the
client. Weather requests and reports are scoped to the authenticated user. The
map plots all 31 approximate Karnataka district-centre coordinates from the
public district catalog on OpenStreetMap tiles; it does not calculate dengue
risk. Contact sends a message by email when SMTP and `CONTACT_EMAIL` are
configured. Profile health-note fields, where shown, are demonstration-only
and do not persist their content.

## Authentication

The `user` table stores registered users with a unique, normalized email,
Bcrypt password hash, profile fields, role, verification flag, and timestamps.
Public users are anonymous; new registrations always receive the `user` role.
Administrators can create accounts and assign roles through the protected
user-management workspace.
Passwords and token blocklist entries are never included in profile responses.

All routes below are prefixed with `http://localhost:5000/api`:

| Method | Route | Authentication | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register` | Public | Create an unverified user and send a verification link |
| POST | `/auth/email-verification` | Public | Verify an email using its single-use, 24-hour token |
| POST | `/auth/email-verification/resend` | Public | Resend a verification link without disclosing account existence |
| POST | `/auth/login` | Public | Authenticate a verified user and return access/refresh JWTs |
| POST | `/admin/auth/login` | Public | Authenticate a verified administrator |
| POST | `/auth/password-reset-request` | Public | Send generic password recovery instructions by email |
| POST | `/auth/password-reset` | Public | Consume a valid one-hour reset link and set a new password |
| POST | `/auth/refresh` | Refresh JWT | Issue a new access JWT |
| GET | `/auth/profile` | Access JWT | Read the current user's profile |
| PUT | `/auth/profile` | Access JWT | Update name, phone, district, and state |
| GET/PUT | `/auth/settings` | Access JWT | Read/update alert, weekly-summary, and dark-mode preferences |
| POST | `/auth/change-password` | Access JWT | Verify and change the password |
| POST | `/auth/logout` | Access JWT | Revoke the access JWT and supplied refresh JWT |
| POST | `/contact` | Public | Email a validated contact message when configured |
| GET/PUT/DELETE | `/profile/emergency-contact` | Access JWT | Manage the current user's emergency contact |
| GET/POST | `/prescriptions` | Access JWT | List/create the current user's prescription transcriptions |
| PUT/DELETE | `/prescriptions/{id}` | Access JWT | Update/delete one of the current user's prescription transcriptions |
| GET | `/weather/districts` | Public | Static Karnataka district-centre coordinates |
| GET | `/weather/search?q=...` | Access JWT | Search cities/districts/states, or reverse-geocode `lat` and `lon` |
| GET | `/weather/current?district=...` | Access JWT | Current conditions; accepts district/city/state or lat/lon |
| GET | `/weather/forecast?city=...&state=...&days=1..5` | Access JWT | Forecast; accepts district/city/state or lat/lon |
| GET | `/weather/history?district=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` | Access JWT | NASA POWER daily history; coordinates are also accepted |
| GET | `/dashboard` | Access JWT | Personal weather and prediction summary; generated informational alerts for today's Moderate/High saved assessments |
| GET | `/reports/statistics?district=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` | Access JWT | User-scoped weather aggregates and climate trends for the selected inclusive range |
| GET | `/reports/weather?type=current&district=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&limit=50&page=1` | Access JWT | Paginated user-scoped observations filtered by type, district, and inclusive date range |
| GET | `/admin/reports?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` | Administrator JWT | System-wide prediction/weather aggregates for the selected range; user count remains all-time |
| POST | `/prediction/predict` | Access JWT | Annual-climate risk classification using the loaded model |
| GET | `/prediction/history?page=1&per_page=10` | Access JWT | Paginated saved results; users see their own records and admins can view all |
| DELETE | `/prediction/history/{id}` | Access JWT | Delete own result or any result as admin |
| GET | `/prediction/latest` | Access JWT | Latest saved result for the signed-in user; admins see the latest overall |
| GET | `/prediction/model-info` | Access JWT | Model artifact availability and expected input units |
| POST | `/alerts/send` | Access JWT | Queue eligible email/SMS alerts for one of the signed-in user's saved predictions |
| GET | `/alerts/history` | Access JWT | Paginated alert history scoped to the signed-in user |
| GET/PUT | `/alerts/settings` | Access JWT | Read or update email, opted-in SMS, daily-summary, high-risk, and weather alert preferences |
| GET | `/alerts/admin/history` | Admin JWT | Search/filter system alert history |
| GET | `/alerts/admin/export` | Admin JWT | Download filtered alert history as CSV |
| POST | `/mosquito-detection/analyze` | Access JWT | Analyze a JPG/JPEG/PNG image (max 10 MB), save its result, and queue eligible high-risk alerts |
| GET | `/mosquito-detection/history` | Access JWT | Search and date/risk-filter the current user's saved image analyses |
| GET/DELETE | `/mosquito-detection/{id}/image`, `/mosquito-detection/{id}` | Access JWT | Retrieve owner-scoped images or delete an analysis and its stored images |
| GET | `/mosquito-detection/{id}/report.pdf` | Access JWT | Download an analysis report with the uploaded image |
| GET | `/mosquito-detection/admin/reports`, `/mosquito-detection/admin/export` | Admin JWT | Search/filter all analyses, view uploaded images, and export report rows to CSV |
| GET | `/mosquito-detection/high-risk-locations` | Admin JWT | Show user-shared high-risk site coordinates on the Karnataka risk map |
| GET/POST | `/admin/users` | Admin JWT | Search and create accounts |
| PATCH/DELETE | `/admin/users/{id}` | Admin JWT | Update/delete an account |
| GET | `/admin/predictions` | Admin JWT | List prediction records |
| GET/DELETE | `/admin/predictions/{id}` | Admin JWT | Inspect/delete one prediction record |
| GET | `/admin/dashboard`, `/admin/analytics`, `/admin/reports` | Admin JWT | System summaries, analytics, and date-filtered reports |
| GET/POST | `/admin/datasets` | Admin JWT | List/upload isolated CSV files |
| DELETE | `/admin/datasets/{path}` | Admin JWT | Remove an isolated CSV upload |
| GET | `/admin/climate-data` | Admin JWT | Browse stored climate/weather records |
| GET | `/admin/model-status` | Admin JWT | Inspect inference model and training artifact status |
| POST | `/admin/model-training` | Admin JWT | Start isolated training |
| GET | `/admin/model-training/{job_id}` | Admin JWT | Inspect training job status |

The retired `/prediction` compatibility route returns `410 Gone`; use
`/prediction/predict` and `/prediction/history`.

Weather current, forecast, and history responses use a common location object
(`district`, `city`, `state`, `latitude`, `longitude`), a `source`, a `cached`
flag, and weather fields (`weather_date`, `temperature`, `humidity`, `rainfall`,
`pressure`, `wind_speed`, `cloud_cover`, `sunrise`, `sunset`, `uv_index`,
`description`, `icon`). Units are Celsius, percent, mm, hPa, and m/s
respectively. Unsupported provider fields are `null`, not estimated. All
weather, dashboard, report, and prediction routes require an access JWT except
the static district catalog. Weather results are stored per user and are never
included in another user's dashboard/reports.
Geocoding/current/forecast return a clear `503` when OpenWeather credentials are
not configured; provider outages are returned as `503`/`502`, and invalid inputs
as `400`.

### Weather integration test

Run the mocked provider/API tests from the project root; they use in-memory
SQLite and do not require live provider credentials:

```powershell
python -m unittest backend.tests.test_weather_api -v
python -m compileall -q backend\app
```

For a live-provider smoke test, set `OPENWEATHER_API_KEY` and confirm
`NASA_POWER_URL` is reachable in `backend/.env`; restart Flask and start the
frontend with its API base URL set to the Flask server. Sign in, open Weather,
and select a Karnataka district or search for a city. Confirm current
conditions, forecast, and historical observations load; repeat a request
within the cache TTL and confirm it is marked cached in the API response.
Without a provider key, the authenticated API returns HTTP 503 for OpenWeather
data rather than fake weather. The Reports page shows only weather results
previously stored by the signed-in account.

Dashboard `weather` follows the current-weather shape and uses the user's most
recently stored current observation (or null weather values if none exists).
`recent_predictions`, prediction counts, and `risk_summary` are based on saved
model predictions when available. `alerts` contains a generated informational
notice when the latest same-day saved model assessment is Moderate or High and
the account's alerts preference is enabled. It reports the stored model output
only; it is not a verified outbreak warning or medical advice. Weather
conditions by themselves are not converted into a dengue prediction.

`GET /weather/districts` returns
`{"districts":[{"state":"Karnataka","name":"Mysuru","district":"Mysuru","latitude":12.30,"longitude":76.65,"lat":12.30,"lon":76.65}, ...]}`.
It is public and requires no JWT. District-centre coordinates are approximate
map points. Dashboard shape is
`{weather_record_count, recent_weather, weather:{location,current,source,cached}, recent_predictions, latest_prediction, prediction_count, risk_distribution, today_risk, alerts, risk_summary}`.
`GET /reports/statistics` returns
`{statistics:{total_weather_records,records_by_type:{current,forecast,history},distinct_locations,monthly_weather,rainfall_trend,temperature_trend,humidity_trend}}`.
Statistics and reports accept optional `district`, `start_date`, and `end_date`
filters; dates are inclusive and apply to each observation inside saved
forecast/history series as well as individual current observations. User report
and statistics endpoints only include the signed-in account's stored weather.
`GET /reports/weather` returns `{reports:[{id,location:{district,city,state,latitude,longitude},record_type,source,observed_at,created_at,weather}],pagination:{page,per_page,total_items,total_pages,has_next,has_previous}}`; `weather` contains normalized `current` or an `items` array for forecast/history, clipped to the selected date range. The Reports page follows all pages so its charts include every matching stored request.
Administrators use `/admin/reports` for date-filtered system aggregates; it is
administrator-only, includes records across accounts, and applies the selected
range to prediction timestamps and weather-record dates.

Send access tokens as `Authorization: Bearer <access_token>`. The frontend
stores the returned tokens in browser local storage as requested. For
production deployments, serve the application exclusively over HTTPS and
consider an HttpOnly-cookie token strategy if the client security requirements
allow changing that persistence requirement.

Registration expects `full_name`, `email`, `phone`, `district`, `state`,
`password`, and `confirm_password`. Passwords must be 8–72 UTF-8 bytes and
include uppercase, lowercase, numeric, and special characters. Login takes
`email` and `password`. Profile updates accept only `full_name`, `phone`,
`district`, and `state`; email changes are rejected. Change-password requests
use `current_password`, `new_password`, and `confirm_password`.

Configure `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`,
`MAIL_PASSWORD`, and `MAIL_DEFAULT_SENDER` before accepting registrations.
For Gmail, use `smtp.gmail.com`, port `587`, TLS enabled, your full Gmail
address for both username and sender, and a Gmail App Password for the password.
Never use your normal Gmail password or commit SMTP credentials. Apply the
database migrations with `flask --app backend.run db upgrade`; registration
returns HTTP 503 without creating an account when email delivery is not
configured. Registration creates
an unverified account and sends a single-use verification link that expires
after 24 hours. Sign-in, including administrator sign-in, is denied until the
email is verified. The resend endpoint returns a generic response for unknown,
verified, and eligible unverified addresses. If a message cannot be delivered
after account creation, the API returns HTTP 503 with `account_created: true`;
use the Verify Email page to request a replacement link.

Successful registration returns a safe `user` object and a message, but no
session tokens. After verification, successful login returns `message`, a safe
`user` object, `access_token`, and `refresh_token`. Validation failures return
HTTP 400 with an `errors` object; duplicate email returns 409; invalid or
revoked tokens return 401. The profile endpoint returns `is_verified`, and the
Profile page displays whether the current account's email is verified.
Password recovery is also sent by email and requires the configured SMTP
settings.

### Authentication smoke test

After applying migrations and starting both servers:

1. Apply migrations and configure working SMTP settings.
2. Register from `/register` with valid details and a compliant password.
3. Confirm registration does not sign in; open the emailed link or visit
   `/verify-email` and request a resend.
4. Verify the email, sign in, then reload and check the session persists.
5. Open `/profile`, update a profile field, and verify it is saved.
6. Log out, then try the profile page again; access should be denied.

## Technology

- **Frontend:** React, Vite, React Router, Axios, Bootstrap 5, React Icons, Chart.js, Leaflet
- **Backend:** Flask application factory and Blueprints, Flask-SQLAlchemy, Flask-Migrate, Flask-JWT-Extended, Flask-CORS
- **Data and ML dependencies:** MySQL, TensorFlow/Keras, scikit-learn, pandas, NumPy, Joblib

Keep signing keys and database credentials private. Add future domain models,
authorization policies, and forecasting features in separate, testable modules.


## ML data engineering (preprocessing only)

The data pipeline is under `backend/app/ml`; it does not train or evaluate a
model and does not add prediction APIs. It reads a CSV, validates and normalizes
column names, removes duplicate rows, marks invalid climate readings as missing,
removes rows without a target, derives calendar features from recognized date
columns, performs a reproducible train/test split, clips climate outliers using
training-set IQR bounds, imputes missing features using training-set statistics,
encodes categorical columns, and scales numeric features. The scaler and
encoders/imputation metadata are fitted without using test feature statistics.

By default, the input is `backend/app/ml/dataset/dengue_climate.csv`, the target
column is `dengue_cases`, and the 80/20 split is seeded with 42. Provide your
own source data; no dataset is bundled. Column names are normalized to lowercase
snake case. Climate bounds are checked for common temperature, humidity,
rainfall, pressure, wind, cloud-cover, latitude, and longitude column aliases.

From the project root, run:

```powershell
python -m backend.app.ml.preprocessing.preprocessing --input backend/app/ml/dataset/dengue_climate.csv --target dengue_cases
```

Outputs are written to `backend/app/ml/dataset/processed/` by default:
`processed_dataset.csv`, `train.csv`, `test.csv`, `scaler.joblib`,
`label_encoder.joblib`, `imputer.joblib`, and `preprocessing_report.json`.
Override paths, target, split size, and random seed with the CLI flags
`--input`, `--output-dir`, `--target`, `--test-size`, and `--random-state`.
The output report explicitly records `model_trained: false`.

Run the focused pipeline test with:

```powershell
python -m unittest backend.tests.test_ml_preprocessing -v
```


## Climate data acquisition

`backend/app/ml/dataset/climate_data_acquisition.py` downloads NASA POWER daily
point observations for every State/UT recognized in the official NCVBDC CSV. It
uses representative administrative-centre coordinates (the 36-entry mapping is
in the module), retrieves 2021 through the latest available date in 2026, and
requests `T2M`, `RH2M`, `PRECTOTCORR`, `WS2M`, `PS`, and
`ALLSKY_SFC_SW_DWN`. Each CSV row is one state/coordinate/date observation; it is
not a state-wide spatial average.

Run from the project root:

```powershell
python -m backend.app.ml.dataset.climate_data_acquisition
```

The module reads `backend/app/ml/dataset/raw/ncvbdc_dengue.csv` and writes
`climate_data.csv` and `climate_validation_report.html` in that same `raw`
directory. Optional `--input`, `--output`, `--report`, `--start-date`, and
`--end-date` flags override paths and inclusive date bounds. NASA POWER `-999`
sentinels are stored as missing values; the report counts missing/invalid
values and duplicate state/date rows, and invalid climate values are marked
missing. No dengue/climate merge or model training is performed.


## Dengue/climate merge and preprocessing

The local-only pipeline at `backend/app/ml/dataset/merge_and_preprocess.py` uses
the existing `raw/ncvbdc_dengue.csv` and `raw/climate_data.csv`. It does not
redownload or regenerate inputs and does not train a model. It normalizes annual
cases/deaths into State/UT-year rows, aggregates annual climate averages and
rainfall totals, and joins on State/UT plus year. Missing annual climate values
are filled by within-state interpolation, same-year cross-state medians, then a
global median. The current climate file has year-to-date rather than full-year
values for 2026. Since inputs are annual, `season` is `Annual` and no month is
created. Population and per-capita rates are omitted because population data was
not supplied.

`outbreak_risk` is a deterministic label based only on annual confirmed cases:
Low Risk is fewer than 1,000 cases, Moderate Risk is 1,000 through 9,999, and
High Risk is 10,000 or more. These are transparent project thresholds, not
clinically validated outbreak definitions. The `temperature_humidity_interaction`
is annual average temperature multiplied by annual average relative humidity.
Rainfall categories use annual totals `<500`, `500?<1500`, and `>=1500` mm;
humidity categories use `<40`, `40?<70`, and `>=70` percent; temperature
categories use `<20`, `20?<30`, and `>=30` ?C.

Run from the project root:

```powershell
python -m backend.app.ml.dataset.merge_and_preprocess
```

This writes `dataset/merged/dengue_climate_dataset.csv`, and under
`dataset/processed/` writes `train.csv`, `test.csv`, `scaler.pkl`,
`label_encoder.pkl`, `preprocessing_report.html`, and `validation_report.html`.
The stratified 80/20 split uses random seed 42; scaling is fitted on training
features only. `outbreak_risk` is encoded in the split CSVs using the saved label
encoder; `confirmed_cases` and `deaths` are not input features to avoid target
leakage.

## Standalone ANN ensemble training

The offline trainer at `backend/app/ml/training.py` consumes the existing
`dataset/processed/train.csv`, `test.csv`, `scaler.pkl`, and
`label_encoder.pkl`. Run it from the project root:

```powershell
python -m backend.app.ml.training
```

It builds the three specified ReLU/softmax ANN architectures, uses Adam and
categorical cross-entropy, and monitors a stratified training-only validation
subset with EarlyStopping, ReduceLROnPlateau, and best-checkpoint restoration.
The processed feature values are not scaled twice; the fitted preprocessing
scaler and label encoder are copied alongside model artifacts. The ensemble
averages all three networks' class probabilities. Training is an offline
operation; the resulting bundle is consumed by the separate Flask prediction
service.

Models, metrics, plots, model summaries, and `training_report.html` are saved
under `backend/app/ml/models/`. The dataset contains only 190 annual
State/UT-year examples, and the 2026 climate observations are year-to-date, so
reported evaluation metrics are preliminary and should not be interpreted as
validated forecasting performance.

### Held-out model evaluation

Evaluate the saved ensemble without retraining or changing its weights:

```powershell
python -m backend.app.ml.evaluate_model
```

The command validates the saved model, 47-feature `StandardScaler`, target
`LabelEncoder`, 48-column processed test split, and class-output order; it then
evaluates the 38 held-out test rows and verifies repeatable inference. It writes
`evaluation_metrics.json`, `confusion_matrix.png`, `roc_curve.png`, and
`evaluation_report.html` beside the model artifacts, and links the latest
evaluation from `training_report.html`. The committed/current result is:
accuracy **0.6579**, macro precision **0.6295**, macro recall **0.6001**,
macro F1 **0.6093**, and multiclass one-vs-rest macro ROC AUC **0.8798**.
The confusion matrix row/column order is High Risk, Low Risk, Moderate Risk:
`[[3, 0, 4], [1, 15, 2], [1, 5, 7]]`.

These estimates are based on a small random split of annual State/UT examples
whose labels are deterministic case-count thresholds. They are not temporal or
external validation, and model probabilities are not calibrated. Do not
interpret them as clinical advice or an operational dengue forecast.

Focused checks:

```powershell
python -m unittest backend.tests.test_ml_preprocessing backend.tests.test_ml_evaluation backend.tests.test_dataset_merge_preprocessing backend.tests.test_prediction_model_integration -v
```


## Flask prediction integration

The Flask application factory initializes one `PredictionService` per app at
startup. It loads `models/ensemble_model.keras`, `models/scaler.pkl`, and
`models/label_encoder.pkl` once and stores the service in the app extensions;
missing or invalid artifacts make inference return HTTP 503 with an explicit
error instead of fabricated predictions. Set `ML_MODEL_DIR` and optionally
`ML_PROCESSED_DIR` if artifacts/schema are not at their default paths. The model
feature order is loaded from `training_metrics.json` or the existing processed
training CSV. Apply database migrations with `flask --app backend.run db upgrade`
to create the prediction history table.

All prediction endpoints require an access JWT (`Authorization: Bearer <token>`):

| Method | Route | Description |
| --- | --- | --- |
| POST | `/api/prediction/predict` | Validate annual climate inputs, run soft voting, persist and return result |
| GET | `/api/prediction/history?page=1&per_page=10&search=Karnataka` | Paginated prediction history; users see only their own, admins see all |
| GET | `/api/prediction/latest` | Latest saved result (admin sees latest across accounts) |
| GET | `/api/prediction/model-info` | Model availability, classes, supported states and units |

Example request in `backend/app/ml/sample_prediction.json`:

```json
{
  "state": "Karnataka",
  "temperature": 25.4,
  "humidity": 68.2,
  "rainfall": 1250.0,
  "wind_speed": 2.8,
  "pressure": 1008.6,
  "solar_radiation": 18.2,
  "year": 2025
}
```

Values must represent annual climate aggregates consistent with training: average
temperature (?C), average humidity (%), annual total rainfall (mm), average wind
(m/s), average pressure (hPa; converted to kPa), average solar radiation
(MJ/m?/day), and year 2021?2026. Current-weather autofill is a snapshot, so
replace those values with annual statistics before interpreting the output. The
model predicts labels created from historical annual confirmed-case thresholds;
it is a research classifier, not a validated future outbreak forecast or medical
advice. The response includes `risk_level`, confidence percent, probabilities
for each class, recommendations, and UTC prediction time.

The React Prediction page calls these APIs, allows editing, displays class
probabilities/confidence and saved history, supports search/pagination/CSV
export, and shows an annual-data caveat. The Dashboard consumes the API's latest
prediction, same-day risk, total count, and risk distribution.

Postman: log in using `POST /api/auth/login`, copy `access_token`, set
`Authorization: Bearer <access_token>`, send the sample JSON to
`POST /api/prediction/predict`, then call history/latest/model-info. In React,
start Flask after applying migrations and start Vite; sign in and open
`/prediction`. The backend tests use an injected test service to cover API
validation, persistence, access scoping, and dashboard summaries without
requiring trained artifacts.
