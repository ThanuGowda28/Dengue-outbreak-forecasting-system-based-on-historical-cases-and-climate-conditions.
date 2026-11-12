# User Manual

## 1. Purpose and scope

The Dengue Outbreak Forecasting System is a research and demonstration web
application. It provides account access, provider-backed weather information,
weather history/reports, a Karnataka district map, and a climate-risk
classification interface. It is not a clinical decision tool and must not be
used to diagnose or treat dengue.

Two separate research workflows are available. **Climate Risk Assessment**
applies the existing three-network ensemble to annual climate inputs. **AI
Forecast** projects historical annual case-count trends. The projection does
not use the climate ensemble, and neither workflow is validated for clinical
or public-health decisions.

## 2. System requirements

- Windows, macOS, or Linux
- Python 3.10–3.12 with packages from `backend/requirements.txt`
- Node.js 20.19+ (or 22.12+) and npm
- SQLite for a simple local demonstration; MySQL 8+ is supported for a
  MySQL-backed installation
- OpenWeather API key for geocoding, current weather, and forecasts
- Network access to NASA POWER for historical climate queries

Docker files are provided for deployment experiments, but Docker was not
available in the validation environment and the container build has not been
verified.

## 3. Installation and startup

From the project root, create a private `.env` based on `.env.example`. Set
database values, `OPENWEATHER_API_KEY`, and distinct random values for
`SECRET_KEY` and `JWT_SECRET_KEY`. In production, each signing key must be at
least 32 characters. Do not use example credentials or commit `.env`.

For the default local setup, configure `DATABASE_URL=sqlite:///dengue_local.sqlite`
in `.env.example` copied to `.env`. For MySQL, create the database and a
least-privilege application account. Then run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
flask --app backend.run db upgrade
flask --app backend.run run --debug
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The backend is normally at
`http://localhost:5000/api`. Apply migrations before the first login or
weather request; the current repository migration head is
`0012_forecast_history`.

## 4. Public access, registration, and login

Visitors can view the public home, information, prevention, FAQ, and contact
pages without an account. Use **Register** to create a registered-user
account. Registration requires a full name, email, phone, district, state, and
a password of at least eight characters containing uppercase, lowercase,
numeric, and special characters. Duplicate email addresses are rejected.

When SMTP works, check the email account for a verification link and open it
within 24 hours. The public **Verify Email** page confirms a valid link;
expired or invalid links show an explanation and allow requesting a new link.
In local demo mode, accounts are verified automatically when email is
unavailable, and password recovery provides a one-hour reset link directly in
the page. SMTP-backed recovery keeps the same enumeration-resistant response.

Use **Login** with the registered email and password after verification.
Unverified users, including administrators, cannot sign in. The authenticated
**Profile** page displays the email-verification status. The browser stores
access and refresh tokens in local storage. Log out on shared devices and use
HTTPS outside local development. Password recovery is available when SMTP is
configured.

## 5. Dashboard and navigation

The authenticated dashboard summarizes current weather, saved risk
assessments, and recent notifications. Its Forecast Now action opens the
dedicated Forecasting page. The Risk Map shows district risk results produced
by the existing ensemble; location markers and available climate data are
informational, not official surveillance.

## 6. Weather

1. Open **Weather**.
2. Search for a city, district, or state; select a suggested location.
3. View current conditions and forecast when the OpenWeather key is configured.
4. Weather observations refresh automatically every 30 minutes; use **Refresh**
   to request them sooner. Temperature, humidity, rainfall, and wind trends can
   be viewed for today, the last 7 days, or the last 30 days.
5. Weather alerts use configured rainfall and humidity thresholds. They are
   weather indicators, not case-count forecasts. Climate risk assessment
   requires annual climate aggregates rather than a live weather snapshot.
6. Historical chart data is requested from NASA POWER.

Temperature is Celsius, humidity is percent, precipitation is millimetres,
pressure is hPa, and wind speed is m/s. Some values (for example UV index or
provider rainfall) may be `null` when the source does not provide them. The
map uses approximate Karnataka district-centre coordinates. It does not
display observed dengue case rates.

## 7. Climate Risk Assessment and Forecasting

The climate risk assessment expects **annual** State/UT climate aggregates:

- Annual mean temperature (°C)
- Annual mean relative humidity (%)
- Annual total rainfall (mm)
- Annual mean wind speed (m/s)
- Annual mean pressure (hPa)
- Annual mean solar radiation (MJ/m²/day)
- Year (2021–2026 in the current dataset)

The risk assessment validates these fields, runs the saved ensemble, and saves
successful results to history. Do not treat an instantaneous weather snapshot
as annual climate statistics.

The separate **Forecasting** page projects annual dengue case-count trends
from historical records. It saves forecast reports and can export an
individual report as PDF. This trend projection does not use or change the
ANN ensemble.

## 8. Reports, history, profile, and settings

- **Reports** displays date-filterable weather records previously stored for
  the signed-in account. Administrators can view system-wide date-filtered
  aggregates in the admin reports workspace.
- **History** combines saved AI forecasts, climate risk assessments, alerts,
  and site detections into a newest-first searchable timeline. Use the activity
  and result filters, pagination, CSV export, or the browser's print-to-PDF
  option. Assessment and detection records can be deleted where permitted;
  forecasts and alerts are read-only in this view.
- **Alerts** combines alert history and alert preferences. Email, SMS, risk
  threshold, daily-summary, and weather-alert preferences can be saved.
  Browser push notifications are not supported by the current alert service.
- **Profile** can update name, phone, district, and state, show verification
  status, and manage an emergency contact. Email is immutable through this
  form. Health-note fields, if shown, are demonstration-only.
- **Prescriptions** stores user-entered transcriptions of clinician-issued
  prescriptions; it does not provide medical advice or issue prescriptions.
- **Settings** persists weekly-summary and dark-mode preferences; alert
  preferences are managed in **Alerts**. Settings do not configure server
  infrastructure.

## 9. Troubleshooting

| Symptom | Check |
| --- | --- |
| Login/profile returns 401 | Sign in again; check that migrations were applied and the token is current. |
| Weather says provider unavailable | Configure `OPENWEATHER_API_KEY`, check network access and provider quota. |
| Historical weather request fails | Check NASA POWER connectivity, valid dates, and coordinates. |
| Climate risk assessment is unavailable | Try again later; if it persists, ask the project administrator to check the application setup. |
| Weather or history cannot load | Check the local application is running and retry after a short wait. |
| Database error | Ask the project administrator to check the database setup and applied migrations. |
| Forgot Password does not send email | Configure `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, and `MAIL_DEFAULT_SENDER`; for Gmail, use an App Password and check provider connectivity. |

For application routes and schema details, see
[Technical Documentation](./technical_documentation.md). The verified tests
and limitations are recorded in the [Test Report](./test_report.html).
