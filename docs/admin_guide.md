# Administrator Guide

## 1. Current administrator capabilities

The application recognizes the `admin` role. Its protected dashboard provides
system summaries, analytics, date-filtered reports, user and prediction
management, dataset inventory/upload/removal, climate-data browsing, model
status, and isolated training-job controls. These endpoints are implemented
under `/api/admin`; admin reports are system-wide aggregates, while the regular
user Reports page remains scoped to its signed-in account.

The admin workspace does not implement account suspension, server
infrastructure settings, automated dataset ingestion, or production model
deployment. Dataset uploads are isolated CSV files and do not replace source
or training data. Training jobs produce staged artifacts and do not replace
the active prediction model. Do not describe those capabilities as available.

## 2. Safe account administration

Public registration always assigns the `user` role. An administrator can
create accounts and change roles through the protected user-management API;
ordinary users cannot edit their own role. The application prevents removing
or demoting the last administrator. Email verification is required for login,
and password recovery uses the configured email service.

## 3. Dataset operations

The checked-in files are research inputs and outputs. The administrator dataset
page manages isolated CSV uploads; those uploads do not replace the files used
by the training or inference pipeline:

- Official annual dengue source:
  `backend/app/ml/dataset/raw/ncvbdc_dengue.csv`
- NASA POWER point observations:
  `backend/app/ml/dataset/raw/climate_data.csv`
- Merged annual dataset:
  `backend/app/ml/dataset/merged/dengue_climate_dataset.csv`
- Train/test files and preprocessing artifacts:
  `backend/app/ml/dataset/processed/`

The current merged dataset contains 190 State/UT-year rows for 2021–2026.
Climate values use one representative administrative-centre point per
State/UT, not a spatially averaged state estimate. The 2026 values are
year-to-date. Do not re-download or overwrite the raw source files when
reproducing the existing package unless new source acquisition is explicitly
approved.

The local merge/preprocessing script reads the existing CSVs and writes the
merged dataset and splits:

```powershell
python -m backend.app.ml.dataset.merge_and_preprocess
```

This command does not train a model, but it rewrites generated output files.
Use a copy of the project/data directory if the existing artifacts must be
preserved byte-for-byte.

## 4. Model training and monitoring

An offline three-ANN training script exists at
`backend/app/ml/training.py`; it uses early stopping and averages class
probabilities for soft voting. The saved three-network ensemble,
matching scaler/encoder, and evaluation artifacts are present, and the Flask
prediction service loads the bundle. The admin training screen starts an
isolated job and exposes its status; generated output is staged and does not
replace the active inference model. The held-out evaluation is small and
randomly split, so it is preliminary evidence rather than operational
forecasting validation.

Do not publish a model metric or label the feature a validated outbreak
forecast until a complete reproducible run is completed, artifacts are
verified against the held-out dataset, and data leakage/temporal validation
have been reviewed. The current 190-row annual dataset is small, and 2026 is
partial.

## 5. Reports

The regular Reports page summarizes observations saved for the authenticated
account. The administrator Reports workspace returns system-wide, date-filtered
prediction and weather aggregates. Admin prediction and analytics pages expose
cross-account data; do not export or share account-level information without
authorization.

## 6. System configuration and deployment

Set environment variables outside source control. Production requires unique,
distinct `SECRET_KEY` and `JWT_SECRET_KEY` values of at least 32 characters,
an exact `FRONTEND_ORIGIN`, a least-privilege database account, provider
credentials, HTTPS, centralized logs, and monitored backups.

Current weather caching and request limiting are process-local. A
multi-worker/multi-replica deployment needs a shared backend before limits and
cache state can be treated consistently. Health endpoints expose operational
readiness; `/api/health/system` additionally exposes CPU, memory, disk, and
dependency state and should be limited to trusted monitoring networks.

## 7. Backup and restore

`ops/backup.ps1` and `ops/backup.sh` are operator-run helpers. They create a
database dump and archive the model directory when present. They do not
schedule backups, encrypt files, enforce retention, or prove restore
integrity. Store database credentials through a protected MySQL login path or
secret manager, keep backup storage access-controlled, and test restores in a
separate environment.

Example manual restore of a verified SQL dump:

```powershell
mysql --host=<database-host> --user=<restore-user> <database-name> < backup.sql
```

Substitute the actual database name and dump location. Do not restore over a
live database without a maintenance window and a verified pre-restore backup.

## 8. Incident checklist

1. Check liveness and database/provider readiness from a trusted monitoring
   network.
2. Confirm application version, migration state, logs, and provider status.
3. Preserve relevant logs and a database backup before making changes.
4. If model availability is red, verify artifact provenance and file/schema
   compatibility; do not copy `ann1.keras` into the ensemble filename.
5. Record the incident and verify recovery with role-scoped smoke tests.
