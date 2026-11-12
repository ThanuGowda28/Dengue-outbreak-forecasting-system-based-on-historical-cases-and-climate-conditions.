# Email Verification Testing Report

**Date:** 2026-10-13  
**Scope:** Registration verification, token lifecycle, login policy, profile status, frontend, and API contract.

> Historical feature-verification snapshot. The current full suite (2026-11-05)
> passed 124 backend tests and 17 frontend tests; the active migration revision
> reported by the Flask CLI is `0012_forecast_history`.

## Implemented behavior

Registration creates an unverified account without issuing a session, then emails a cryptographically random 256-bit token. Only its SHA-256 digest is stored; the token is single-use and expires after 24 hours. Resending replaces the previous token and returns an enumeration-resistant response. Login, administrator login, and refresh reject unverified accounts. The public Verify Email page verifies query tokens, reports invalid or expired links, and offers a resend form. The authenticated profile response and Profile page expose verification status.

## Verification

The backend authentication tests cover registration gating, hashed storage, valid and replayed tokens, expiration, resend/rotation, enumeration resistance, profile status, login, and administrator policy. The full register → verify → login → profile API flow is exercised with email delivery mocked. Frontend Node tests cover verification-link parsing, resend address validation, and display of invalid/expired API messages.

- Historical feature run: `python -m unittest discover -s backend\tests -v` — **66 passed**.
- Historical frontend run: `npm test` — **12 passed**.
- `npm run build` — **passed**.
- Python compile check — **passed**.

Production deployments must configure SMTP and apply migrations through the current head, `0012_forecast_history`. In local development demo mode, registration is auto-verified if SMTP is missing or delivery fails; test and production configurations do not enable this fallback. When a verification message cannot be delivered outside demo mode, users can request a replacement message.
