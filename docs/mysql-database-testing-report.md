# MySQL Database Testing Report

## Current database status (2026-10-13)

The earlier point-in-time findings below described the database before the
pending migrations were applied. The configured MySQL database has since been
upgraded to Alembic revision `0007_email_verification_tokens`. The
`email_verification_tokens` table and revision were verified after the
upgrade. The historical “missing table” and migration-backlog statements below
do not describe the current database state.

## Scope and method

Reviewed the SQLAlchemy models, Alembic revisions, configured MySQL schema, and database-backed API test suites. The initial inspection was read-only and changed no application data; migrations were applied later as recorded above. Migration upgrade/downgrade testing and the API suites use isolated SQLite test databases, so those results are not treated as proof of live-MySQL CRUD behavior.

## Summary

- The configured MySQL server was reachable and identified itself as MySQL 8.0.46.
- At the time of the original inspection, its Alembic revision was `0004_prediction_history`, before migrations were applied.
- The current migration head is `0007_email_verification_tokens`.
- The full migration chain upgraded through 0006, downgraded to base, and upgraded again successfully on isolated SQLite.
- An earlier combined API run had 43 tests: 41 passed and 2 failed because of stale expectations for the retired `/api/prediction` endpoint. This is a historical test snapshot; the current backend suite has 70 passing tests.
- No application-row writes or live-MySQL CRUD operations were attempted; the later migration upgrade changed schema only.

## Tables and relationships

| Table | Purpose and principal relationship | Configured MySQL status |
|---|---|---|
| `users` | User accounts; parent of the user-owned records below. | Present |
| `token_blocklist` | Revoked JWT identifiers; `user_id` references `users.id`. | Present |
| `weather_history` | Per-user weather observations; `user_id` references `users.id` with `ON DELETE CASCADE`. | Present |
| `prediction_history` | Per-user prediction results; `user_id` references `users.id` with `ON DELETE CASCADE`. | Present |
| `emergency_contacts` | One emergency contact per user; unique `user_id` references `users.id` with `ON DELETE CASCADE`. | Present after migrations 0005–0007 |
| `prescription_records` | User-associated prescription records; `user_id` references `users.id` with `ON DELETE CASCADE`. | Present after migrations 0005–0007 |
| `user_preferences` | One settings row per user; `user_id` is both primary key and cascading foreign key to `users.id`. | Present after migrations 0005–0007 |
| `email_verification_tokens` | Hashed, single-use verification token with expiry, linked to a user. | Present after migration 0007 |
| `email_verification_tokens` | Hashed, single-use email-verification tokens with expiry. | Present after migration 0007 |

The database also contains Alembic's `alembic_version` table.

## Constraints and indexes

### Present in the configured MySQL schema

- `users.id`, `token_blocklist.id`, `weather_history.id`, and `prediction_history.id` are primary keys.
- `users.email` is protected by a unique index (`ix_users_email`).
- `users.role` has a check constraint restricting values to `user` or `admin`.
- `token_blocklist.jti` is protected by a unique index; `user_id` is indexed.
- `weather_history` has indexes for `user_id`, `record_type`, `district`, and `weather_date`.
- `prediction_history` has indexes for `user_id`, `state`, `prediction`, `prediction_time`, and the composite `(user_id, prediction_time)`.
- Weather and prediction history foreign keys cascade when a referenced user is deleted.

### Gaps and cautions

- `token_blocklist.user_id` has no database-level `ON DELETE CASCADE`. Account deletion must explicitly remove blocklist rows first; deleting a user directly can be rejected by the foreign key. The application has a related user-deletion cleanup test, but direct database deletion remains constrained.
- Weather measurement ranges, prediction input/confidence ranges, and valid `record_type`/`token_type` values are not comprehensively guarded by database check constraints. The API layer is responsible for rejecting invalid values; direct SQL or alternate writers could bypass those validations.
- MySQL reports the date-time columns as `DATETIME`, which does not preserve a timezone offset. Application code should continue normalizing timestamps consistently (currently generated in UTC).
- The table/revision verification after migration did not inspect every MySQL-specific constraint on the new tables.

## CRUD and API test results

The combined backend suites covered authentication and settings, patient-record CRUD, prediction creation/history/filtering/deletion, weather persistence/reporting, and admin user/prediction management.

| Result | Tests |
|---|---:|
| Passed | 41 |
| Failed | 2 |
| Total | 43 |

The following two failures were recorded in that earlier run of
`test_weather_api.py`; they were stale expectations about a retired route:

1. `test_auth_validation_and_prediction_placeholder` expected `/api/prediction` to return 200; actual status is 410.
2. `test_user_scoped_rate_limit` also expected `/api/prediction` to return 200; actual status is 410.

These assertions targeted a retired endpoint, not a MySQL failure. They are
historical test results and must not be treated as the current backend test
status. See the current audit verification results for the latest suite result.

Because the API tests use SQLite, passing CRUD tests confirm application behavior against that test schema only. They do not verify CRUD against the configured MySQL database.

## Migration verification

The repository has a linear Alembic chain:

1. `0001_auth_tables` — users and token blocklist.
2. `0002_weather_history` — weather observations.
3. `0003_weather_observation_fields` — normalized weather fields and indexes.
4. `0004_prediction_history` — prediction history and indexes.
5. `0005_admin_patient_records` — emergency contacts and prescriptions.
6. `0006_user_preferences` — per-user preferences.

On an isolated SQLite database, upgrade through 0006, downgrade to base, and re-upgrade through 0006 all completed successfully. This verifies the migration sequence on SQLite, but not MySQL-specific DDL execution.

At the time of the original inspection, the configured MySQL database was at
`0004_prediction_history`. It was subsequently upgraded through
`0007_email_verification_tokens`, so this earlier missing-table finding is
resolved.

## Findings and recommended follow-up

1. **Migration backlog:** resolved; current revision is 0007.
2. **Live-MySQL CRUD:** earlier API CRUD runs used SQLite, not MySQL. Migration application and table/revision existence were verified against MySQL, but this report does not claim a complete live-MySQL CRUD run.
3. **Historical stale tests:** the two failures above describe the earlier test run only; consult the current audit run for test status.
4. **Constraint hardening:** database-level checks for critical domain/range fields and token-blocklist deletion policy remain optional follow-up.

## Overall database status

**Migration status: current.** The configured database is at `0007_email_verification_tokens`, and the verification-token table exists. This confirms schema revision and table presence after migration; it does not constitute a claim that every application CRUD path has been exercised against MySQL.
