# Email Verification Testing Report

**Date:** 2026-10-13  
**Scope:** Registration verification, token lifecycle, login policy, profile status, frontend, and API contract.

## Implemented behavior

Registration creates an unverified account without issuing a session, then emails a cryptographically random 256-bit token. Only its SHA-256 digest is stored; the token is single-use and expires after 24 hours. Resending replaces the previous token and returns an enumeration-resistant response. Login, administrator login, and refresh reject unverified accounts. The public Verify Email page verifies query tokens, reports invalid or expired links, and offers a resend form. The authenticated profile response and Profile page expose verification status.

## Verification

The backend authentication tests cover registration gating, hashed storage, valid and replayed tokens, expiration, resend/rotation, enumeration resistance, profile status, login, and administrator policy. The full register → verify → login → profile API flow is exercised with email delivery mocked. Frontend Node tests cover verification-link parsing, resend address validation, and display of invalid/expired API messages.

- `python -m unittest discover -s backend\tests -v` — **66 passed**.
- `npm test` — **12 passed**.
- `npm run build` — **passed**.
- Python compile check — **passed**.

SMTP must be configured in the deployment environment, and migrations must be applied through `0007_email_verification_tokens`. Registration is unavailable when mail configuration is missing. If a delivery attempt fails after account creation, the frontend provides a path to request a replacement message.
