# End-to-End Testing Report

**Date:** 2026-10-07  
**Scope:** Registration, login, profile, dashboard, weather, prediction, prediction history, reports, admin, and logout.

> Historical execution snapshot. The configured MySQL database was later
> upgraded to `0007_email_verification_tokens`, and the model/authentication/
> weather checks described by this final audit were performed after this
> report's date. The test counts and incomplete browser journey below are not
> current readiness results.

## Current follow-up verification (2026-10-13)

- Backend suite: **70 passed**.
- Frontend unit tests: **12 passed**.
- Frontend production build: **passed**.
- Database migration: **`0007_email_verification_tokens` applied**; verification-token table confirmed.
- Live service checks: backend, model, and weather health checks passed; authenticated current weather, forecast, and historical weather requests returned success.
- Full live authenticated browser-to-MySQL journey: not run in this audit.

## Test approach and limits

- Ran the selected backend API suites against their isolated in-memory SQLite test databases, not the configured MySQL database.
- Ran the trained-model prediction integration test, frontend unit tests, and production frontend build.
- Smoke-checked the frontend registration, login, and admin-login screens. Direct navigation to the protected dashboard redirected to login as expected.
- Did not create a user in the configured database, use real user/admin credentials, or call OpenWeather with a live provider key. Therefore, successful authenticated browser-to-live-MySQL flows and live weather-provider behavior remain unverified.
- At the time of this snapshot, the configured MySQL database was at revision `0004_prediction_history`. It was later upgraded to `0007_email_verification_tokens`; consult the current database audit for the migration verification.

## Test case results

| Test Case ID | Module | Expected Output | Actual Output | Pass/Fail |
|---|---|---|---|---|
| E2E-REG-01 | Registration | Valid registration creates a user, does not return a password/hash, and duplicate email is rejected with 409. | Registration returned 201; duplicate returned 409; password fields were absent from response and stored password was hashed. | PASS |
| E2E-LOGIN-01 | Login | Invalid password is rejected; valid credentials (including normalized email) return access and refresh tokens. | Invalid login returned 401; valid login returned 200 with both tokens. | PASS |
| E2E-PROFILE-01 | Profile | Unauthenticated profile access is rejected; JWT profile update persists; email change is rejected. | Unauthenticated access returned 401; profile update returned 200; email change returned 400. | PASS |
| E2E-DASH-01 | Dashboard | Dashboard returns prediction totals, latest prediction, and risk summary based on stored records. | API test created a prediction and dashboard returned count 1, latest risk `High`, and a risk-distribution entry. Protected browser route redirected to `/login`. | PASS |
| E2E-WEATHER-01 | Weather | Auth/validation, current/forecast/history, provider error handling, per-user persistence, and report-shaped weather data behave as specified. | Weather API tests passed for mocked providers, validation, persistence, error handling, and report shape. No live OpenWeather request was made. | PASS |
| E2E-PRED-01 | Prediction | A valid payload uses the trained model and returns a result that is saved to history; missing model/input failures are handled. | Trained-model integration test passed: prediction returned and persisted. The API test suite also covered validation and unavailable-model behavior. | PASS |
| E2E-HISTORY-01 | Prediction History | Results are user-scoped; filters/pagination work; only authorized owners/admins can delete. | API tests passed for ownership, filters, pagination, and authorized deletion. | PASS |
| E2E-REPORT-01 | Reports | Weather/admin report endpoints return expected summaries, filters, and frontend-compatible result structures. | Report filter/limit and frontend-shape tests passed; admin report summary and risk counts passed. | PASS |
| E2E-ADMIN-01 | Admin | Non-admin access is denied; admin login/dashboard/user and prediction CRUD/report endpoints work. | Admin login/role protection, dashboard, reports, user and prediction CRUD, and admin deletion safeguards passed in API tests. | PASS |
| E2E-LOGOUT-01 | Logout | Logout revokes access and refresh tokens and subsequent protected access is rejected. | API test passed; logout returned 200 and revoked-token checks passed. | PASS |
| E2E-UI-01 | Browser-to-live-backend journey | A browser user registers, logs in, completes protected flows, and logs out against the configured live database/provider. | Registration/login/admin-login screens rendered; protected dashboard redirected to login. The full authenticated journey was not run in this historical snapshot. | NOT RUN |

## Automated run summary

- **Backend API suites:** 46 tests; **44 passed, 2 failed**.
- **Trained-model integration:** 1 test; **passed**. It emitted scikit-learn artifact-version warnings: `StandardScaler` and `LabelEncoder` were serialized with scikit-learn 1.9.0 and loaded with 1.9.1.
- **Frontend unit tests:** 8 passed, 0 failed.
- **Frontend production build:** passed.
- **Live authenticated browser E2E:** not run.

## Bugs and issues found

### 1. Stale tests assert that a retired prediction endpoint still works

The only two backend test failures are in `backend/tests/test_weather_api.py`:

- `test_auth_validation_and_prediction_placeholder` expects `GET /api/prediction` to return 200 with placeholder data; actual response is 410.
- `test_user_scoped_rate_limit` uses `GET /api/prediction` as its rate-limit target and expects the first request to return 200; actual response is 410.

The supported prediction API tests separately confirm that the legacy endpoint returns 410 rather than fabricated placeholder predictions. These are outdated test expectations, not evidence that the supported prediction route is broken. Update those tests to exercise the current supported route for rate limiting and to expect 410 from the retired route.

### 2. Configured MySQL schema was behind the application migration head at the time

At the time of this report, the configured database was at revision
`0004_prediction_history`; the repository then had migrations through
`0006_user_preferences`. The pending migrations have since been applied and
the current revision is `0007_email_verification_tokens`. The original
MySQL-backed browser CRUD journey was not run.

### 3. Model artifacts were produced with a different scikit-learn version

The trained-model integration test succeeded, but loading the scaler and label encoder emitted `InconsistentVersionWarning` because artifact version 1.9.0 differs from runtime 1.9.1. This is a compatibility risk rather than a reproduced prediction failure. Rebuild/version the artifacts with the deployed dependency version, or pin the runtime to the artifact version, then rerun the model integration test.

## Overall status

At the time of this historical report, the listed workflows had broad API
coverage, but the authenticated browser journey and MySQL-backed CRUD had not
been executed. The current follow-up results above supersede its old test
counts and migration state. A complete authenticated browser E2E journey and
live-MySQL CRUD are still not claimed as verified.
