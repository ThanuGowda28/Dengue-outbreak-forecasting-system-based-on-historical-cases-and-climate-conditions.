# Deployment checklist

## Before deployment

- [ ] Use a supported Python and Node.js runtime and pin reviewed dependency versions.
- [ ] Set unique `SECRET_KEY` and `JWT_SECRET_KEY` values (at least 32 characters each); store them in the host's secret manager.
- [ ] Configure a dedicated least-privilege MySQL account, TLS for remote database traffic, automated encrypted backups, and restore tests.
- [ ] Configure `FRONTEND_ORIGIN` to the exact deployed frontend origins.
- [ ] Set `DATABASE_URL` to MySQL or configure all `DB_*` fields; production rejects SQLite.
- [ ] Set `REDIS_URL` or both Celery Redis URLs for alert delivery.
- [ ] Set `OPENWEATHER_API_KEY`; NASA POWER remains the historical climate provider.
- [ ] Confirm model artifact bundle presence: `ensemble_model.keras`, `scaler.pkl`, `label_encoder.pkl`, plus `training_metrics.json` and feature schema metadata.
- [ ] Review model/data provenance, validation results, intended use, and limitations; the application is not a clinical decision system.
- [ ] Run migrations once as a release step with `flask --app backend.run db upgrade`.
- [ ] Build the frontend and backend images from reviewed source; scan image/dependency vulnerabilities.
- [ ] Put the frontend behind HTTPS and a trusted reverse proxy; configure TLS, DNS, and HSTS at that proxy.
- [ ] Configure centralized log collection, retention, alerting, resource requests/limits, and health probes.
- [ ] Verify provider quotas, process-local cache/auth-rate-limit behavior, and any multi-replica restrictions.
- [ ] Run the health checks, smoke tests, and user-role authorization tests against the deployment candidate.

## Release and rollback

- [ ] Deploy to staging and verify `/api/health`, `/api/health/database`, `/api/health/model`, and `/api/health/weather`.
- [ ] Run a backup and verify that a restore works in a separate environment.
- [ ] Deploy gradually; check API error rate, latency, CPU/memory, model availability, and provider failures.
- [ ] Keep a known-good application image and database backup available for rollback.
- [ ] Back up before schema changes; migrations must be backward compatible with the currently running application.
- [ ] After rollback, verify the API and database health endpoints and record the incident.

## Deployment destinations

The Docker Compose setup is suitable for a single VM or a controlled demonstration environment. For Render or Railway, deploy the backend and frontend as separate services and use managed MySQL; provide the same environment variables and a persistent/immutable model artifact source. For Azure or AWS, use container hosting, managed MySQL, a managed secret store, TLS-enabled ingress, centralized logs/metrics, and scheduled database backups. Do not expose MySQL publicly. No cloud deployment is performed by this repository's CI.
