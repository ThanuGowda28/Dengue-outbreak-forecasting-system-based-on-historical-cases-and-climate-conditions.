# QR Code Module Testing Report

**Date:** 2026-10-07  
**Scope:** Emergency-contact QR generation, QR scanning, emergency-contact persistence, and frontend/backend verification.

## Summary

The profile already persisted emergency contacts through authenticated, user-scoped API endpoints and generated a vCard QR code. The missing scan flow has now been added: users can scan with a camera or select a QR image, valid emergency vCards are decoded and displayed locally, and scanned content is not saved or used to overwrite the account contact. QR generation now uses the saved contact, not unsaved edits.

## Results

| Area | Status | Evidence |
|---|---|---|
| QR generation | Pass | Generates a QR-encoded vCard containing only the saved emergency contact name and phone. Values escape vCard delimiters and line breaks. The QR is disabled when there is no saved contact or edits have not been saved. |
| QR scanning | Implemented; build/unit verified | Added camera and image scanning through `html5-qrcode`. Scanner accepts QR codes only, parses vCard name and phone fields, validates the decoded contact, and displays it without automatic persistence. |
| Emergency details storage | Pass | Existing authenticated `GET`, `PUT`, and `DELETE /api/profile/emergency-contact` routes store one contact per user. The API tests verify CRUD, validation, unauthenticated denial, and that another user cannot read the saved contact. |
| Frontend | Pass with device-test limitation | vCard generation/parsing tests pass and production build succeeds. The camera permission, physical camera scan, and image-file scanner were not manually tested in a browser because `http://localhost:5173/profile` returned `ERR_CONNECTION_REFUSED`. |
| Backend | Pass | Patient-record API suite: **3 passed**. No backend application changes were needed; the existing emergency-contact API provides the required persistence. |

## Tests Run

- `python -m unittest backend.tests.test_patient_records_api -v` — **3 passed**.
- `npm test` — **5 passed**, including vCard generation, escaped delimiters/line breaks, and invalid QR payload cases.
- `npm run build` — **passed**. The scanner is lazy-loaded into a separate production chunk.
- Browser/device scan: **not completed** because the local frontend server was unreachable. Camera access normally also requires browser permission and a secure context (HTTPS or localhost).

## Remaining Work

1. Start the frontend and backend and perform a device/browser smoke test with camera permission granted; also test image-file selection.
2. Test scans across multiple QR reader apps/devices for vCard interoperability.
3. Confirm privacy expectations before distributing QR codes: the QR contains the contact name and phone in readable vCard data, as noted in the UI.

## Files Modified

- `backend/tests/test_patient_records_api.py` — added an unauthenticated-access assertion.
- `frontend/package.json` and `frontend/package-lock.json` — added `html5-qrcode`.
- `frontend/src/components/EmergencyQrScanner.jsx` — camera and image QR scanner.
- `frontend/src/pages/ProfileWorkspace.jsx` — scanning UI, scanned-contact result display, saved-contact-only QR generation.
- `frontend/src/utils/emergencyVCard.js` — vCard generation, escaping, and validation/parser.
- `frontend/src/utils/emergencyVCard.test.js` — QR data utility tests.
- `docs/qr-code-testing-report.md` — this report.
