# User Manual

## 1. Purpose and scope

The Dengue Outbreak Forecasting System is a research and demonstration web
application. It provides account access, provider-backed weather information,
weather history/reports, a Karnataka district map, and a climate-risk
classification interface. It is not a clinical decision tool and must not be
used to diagnose or treat dengue.

The prediction screen and API use the saved three-network ensemble. Its
case-count labels and small random held-out evaluation do not establish a
validated future outbreak forecast; do not use it for clinical or public-health
decisions.

## 2. System requirements

- Windows, macOS, or Linux
- Python 3.10–3.12 with packages from `backend/requirements.txt`
- Node.js 20.19+ (or 22.12+) and npm
- MySQL 8+ for a local application installation
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

Create the MySQL database and a least-privilege application account, then run:

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
`http://localhost:5000/api`. Apply migrations before the first real login or
weather request. The current database migration head is
`0007_email_verification_tokens`.

## 4. Public access, registration, and login

Visitors can view the public home, information, prevention, FAQ, and contact
pages without an account. Use **Register** to create a registered-user
account. Registration requires a full name, email, phone, district, state, and
a password of at least eight characters containing uppercase, lowercase,
numeric, and special characters. Duplicate email addresses are rejected.

After submitting registration, check the email account for a verification link
and open it within 24 hours. The public **Verify Email** page confirms a valid
link; expired or invalid links show an explanation and allow requesting a new
link. A user who did not receive the message can visit `/verify-email`, enter
the registration email, and request another link. Resending replaces the
previous token. Configure working SMTP settings before registering; without
email delivery configuration registration is unavailable.

Use **Login** with the registered email and password after verification.
Unverified users, including administrators, cannot sign in. The authenticated
**Profile** page displays the email-verification status. The browser stores
access and refresh tokens in local storage. Log out on shared devices and use
HTTPS outside local development. Password recovery is available when SMTP is
configured.

## 5. Dashboard and navigation

The authenticated dashboard summarizes provider-backed weather history and
saved prediction history. Empty alert and prediction sections mean data is
not available; they are not evidence of low dengue risk. The sidebar provides Weather, Risk Map, Prediction, History, Profile, and
Settings. The Risk Map displays approximate district locations and weather
context, not calculated dengue-risk areas. Admin-only navigation is role-gated;
the admin guide lists the implemented administrative workflows and their
limits.

## 6. Weather

1. Open **Weather**.
2. Search for a city, district, or state; select a suggested location.
3. View current conditions and forecast when the OpenWeather key is configured.
4. Use the history controls to request daily historical climate data from
   NASA POWER.

Temperature is Celsius, humidity is percent, precipitation is millimetres,
pressure is hPa, and wind speed is m/s. Some values (for example UV index or
provider rainfall) may be `null` when the source does not provide them. The
map uses approximate Karnataka district-centre coordinates. It does not
display observed dengue case rates.

## 7. Prediction

The current classifier expects **annual** State/UT climate aggregates:

- Annual mean temperature (°C)
- Annual mean relative humidity (%)
- Annual total rainfall (mm)
- Annual mean wind speed (m/s)
- Annual mean pressure (hPa)
- Annual mean solar radiation (MJ/m²/day)
- Year (2021–2026 in the current dataset)

The prediction API validates these fields, runs the saved ensemble, records
successful results per account, and exposes prediction history. Do not treat
an instantaneous weather snapshot as annual climate statistics. This research
classifier is not validated for medical or public-health decisions.

## 8. Reports, history, profile, and settings

- **Reports** displays date-filterable weather records previously stored for
  the signed-in account. Administrators can view system-wide date-filtered
  aggregates in the admin reports workspace.
- **History** displays saved prediction records when available.
- **Profile** can update name, phone, district, and state, show verification
  status, and manage an emergency contact. Email is immutable through this
  form. Health-note fields, if shown, are demonstration-only.
- **Prescriptions** stores user-entered transcriptions of clinician-issued
  prescriptions; it does not provide medical advice or issue prescriptions.
- **Settings** persists alert, weekly-summary, and dark-mode preferences; it
  does not configure server infrastructure.

## 9. Troubleshooting

| Symptom | Check |
| --- | --- |
| Login/profile returns 401 | Sign in again; check that migrations were applied and the token is current. |
| Weather says provider unavailable | Configure `OPENWEATHER_API_KEY`, check network access and provider quota. |
| Historical weather request fails | Check NASA POWER connectivity, valid dates, and coordinates. |
| Prediction shows unavailable | Check model readiness at `/api/health/model` and inspect the saved model artifacts. |
| Browser cannot reach API | Check `VITE_API_BASE_URL`, `FRONTEND_ORIGIN`, and that Flask is running. |
| Database error | Check MySQL service, database grants, connection values, and migration status. |
| Forgot Password does not send email | Configure `MAIL_SERVER`, `MAIL_FROM`, SMTP credentials, and check provider connectivity. |

For application routes and schema details, see
[Technical Documentation](./technical_documentation.md). The verified tests
and limitations are recorded in the [Test Report](./test_report.html).
