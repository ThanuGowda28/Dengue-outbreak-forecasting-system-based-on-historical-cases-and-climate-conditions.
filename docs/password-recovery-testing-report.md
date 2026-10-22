# Password Recovery Testing Report

**Current status:** Implemented. This replaces the earlier point-in-time report
that described the recovery flow as UI-only.

## Implemented workflow

- `POST /api/auth/password-reset-request` validates an email, applies the
  public-request limit, and returns a generic response that does not reveal
  whether the account exists.
- Recovery instructions are sent through the configured SMTP service. Reset
  tokens are random, stored only as SHA-256 hashes, expire after one hour, and
  are deleted when used or expired. Issuing a new token replaces the prior one.
- `POST /api/auth/password-reset` validates token expiry/reuse and password
  policy, then changes the password hash.
- The Forgot Password and Reset Password pages are connected to the backend
  and display request, expiry, invalid-token, and success states.
- Delivery requires `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`,
  `MAIL_USERNAME`, `MAIL_PASSWORD`, and `MAIL_DEFAULT_SENDER`. Missing or
  failing mail configuration is reported as a
  service error; it is not represented as a successful email delivery.

## Verification scope

The backend authentication suite exercises recovery validation and password
reset behavior with email delivery mocked. The frontend test suite and
production build verify the connected client code. These checks do not prove
that deployment SMTP credentials are valid; test email delivery in the target
environment before relying on recovery there.
