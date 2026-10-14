# Voice Assistant Testing Report

**Date:** 2026-10-07  
**Scope:** Voice input, speech recognition, climate-form integration, and prediction API path.

## Summary

Voice input is now available on the Prediction form. It uses the browser's Web Speech recognition API to transcribe labelled climate values, parses recognized values into the existing form, and leaves final prediction submission to the user for review. The existing prediction submission path remains the trained-model API and persists successful results to prediction history.

## Findings and Results

| Area | Status | Evidence |
|---|---|---|
| Voice input control | Implemented | The prediction form exposes “Speak climate inputs” and a stop button while recognition is active. Unsupported browsers receive a manual-entry fallback message. |
| Speech recognition | Implemented; browser capability verified | Uses `SpeechRecognition` or `webkitSpeechRecognition`, handles permission/device/network/no-speech errors, shows the transcript, and provides an example spoken format. The current browser reports both recognition APIs and `isSecureContext: true`. |
| Transcript parsing | Pass | Recognizes labelled temperature, humidity, rainfall, wind speed, pressure, solar radiation, year, and supported state values. Partial dictation is accepted; unrecognized speech does not create field values. |
| Prediction integration | Pass | Parsed values update the existing prediction form; a recognized supported state updates the state selector. Voice never submits a prediction automatically. Manual submit continues through `submitPrediction` to `/api/prediction/predict`. Newer manual/voice input is protected from an outstanding weather prefill overwriting it. |
| Prediction persistence | Pass | Existing prediction API test verifies the request returns and stores the prediction. The real trained-model integration test also passed and confirmed the result is returned and saved to history. |
| Audio privacy | Disclosed | UI notes browser speech recognition may process audio through its configured service and instructs users to review results. Provider handling depends on browser/platform settings. |

## Tests Run

- Frontend `npm test`: **8 passed**, including voice parsing for all climate fields, multiword state, alternate labels, partial dictation, and unrelated/unknown input.
- Frontend `npm run build`: **passed**.
- Backend `test_prediction_is_persisted_and_returned`: **passed**.
- Backend `test_trained_model_prediction_is_returned_and_saved_to_history`: **passed**.
- Browser capability probe: `SpeechRecognition` and `webkitSpeechRecognition` were available; browser secure-context status was `true`.
- Interactive microphone smoke test: **not completed**. The browser redirects the protected `/prediction` route to `/login`, and no authenticated backend session was available. Microphone permission and actual speech transcription therefore remain unverified in-browser.

## Remaining Work

1. Perform an authenticated browser test with microphone permission enabled, including start/stop, permission denial, no speech, and supported/unsupported browser behavior.
2. Validate recognition accuracy with representative accents, noisy environments, decimal values, and supported state names. Users should verify all recognized values; spoken number words that are not transcribed as digits may not be parsed.
3. Confirm the deployed browser's speech-recognition provider/privacy behavior and document it for deployment.

## Files Modified

- `frontend/src/components/VoiceClimateInput.jsx` — browser speech input, transcript status, and errors.
- `frontend/src/pages/Prediction.jsx` — populate existing climate form and protect recognized/manual inputs from late weather-prefill updates.
- `frontend/src/utils/voiceClimateInput.js` — label/value and supported-state parsing.
- `frontend/src/utils/voiceClimateInput.test.js` — parser tests.
- `frontend/src/utils/dashboardData.js` — link Voice climate input card to Prediction and describe actual functionality.
- `docs/voice-assistant-testing-report.md` — this report.

No backend application changes were needed; the existing prediction API/model path is reused.
