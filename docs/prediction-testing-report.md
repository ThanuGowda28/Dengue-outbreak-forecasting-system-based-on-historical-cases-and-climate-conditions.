# Prediction Module Testing Report

**Date:** 2026-10-07  
**Scope:** Prediction model artifacts, preprocessing, API, persisted history, and React result page. Authentication and Admin implementations were not changed.

## Summary

The production Prediction service loads and runs the trained three-network Keras soft-voting ensemble. Scaler and label-encoder artifacts load successfully, and an authenticated API request using the real model returns a class distribution that is saved and retrievable through both history and latest-result endpoints.

The old `/api/prediction` compatibility route returned a successful response containing an empty `predictions` list. It now returns `410 Gone` with links to the supported predict and history endpoints; it no longer looks like a successful empty prediction result. The separately linked History page now queries persisted records, and stale public-facing text claiming that the model and history API were not implemented has been corrected. The deterministic `StubPredictionService` remains isolated to the existing API unit tests, where it tests route behavior; production startup and the added integration test use the trained model.

## Verification Results

| Area | Result | Evidence |
|---|---|---|
| Model loading | Pass | `ensemble_model.keras` loaded in the backend venv; service reported available with no load error. |
| Scaler | Pass | Fitted `StandardScaler` loaded; 47 named columns align with the 48-feature model schema (year is not scaled). |
| Label encoder | Pass | Fitted `LabelEncoder` loaded; classes are `High Risk`, `Low Risk`, and `Moderate Risk`, matching the model's three outputs. |
| Preprocessing | Pass | Runtime feature frame was finite and shaped `(1, 48)`. API pressure in hPa is converted to kPa; the annual interaction and state/category one-hot features are built; training and serving category cutoffs match. |
| Real model inference | Pass | Sample input produced a real inference result with normalized class probabilities (sum `1.0`); not a fixed stub result. |
| Prediction API | Pass | Authenticated real-model POST returned `200`; missing inputs returned `400`; unauthenticated history returned `401`. Model info returned `200` and reported the loaded model. |
| History/latest | Pass | The real-model API request inserted one history row; history and latest-result endpoints each returned that saved result. Existing tests also verify user scoping and Admin-wide history access. |
| Deprecated API | Pass | GET and POST to `/api/prediction` now return `410` and migration paths rather than a `200` empty-list placeholder. |
| Prediction and history pages | Build pass; browser check partial | The Prediction page's API client uses model-info, predict, and history endpoints; result, probabilities, recommendations, and history are rendered from API data. The separate History page now calls the persisted history API with search, risk filter, and pagination. Production Vite build passed. Browser navigation reached the protected route but redirected to Login after API `401` responses because no valid authenticated browser session was available; an authenticated visual interaction could not be completed. |

## Automated Tests

- `python -m unittest discover -s backend\tests -p "test_prediction*.py" -v` — **7 tests passed**, including one new real-model integration test.
- `npm test` in `frontend` — **2 tests passed**.
- `npm run build` in `frontend` — **passed**.
- Real-model integration test uses a temporary SQLite database and verifies artifacts, class/probability validity, model-info, filtered history, and persistence via prediction/history/latest APIs.

## Artifact and Model-Quality Notes

- Trained artifacts present: `ensemble_model.keras` (954,962 bytes), `scaler.pkl` (3,071 bytes), and `label_encoder.pkl` (512 bytes); three constituent ANN models and training metrics are also present.
- Recorded evaluation: 152 training rows, 38 test rows, 48 input features, 65.79% ensemble accuracy, and 60.93% macro F1.
- The displayed top-class probability is the model's softmax output; calibration was not evaluated. The result labels and API warning now state that it is not calibrated confidence.
- The test set is small, and the available 2026 climate series is year-to-date. Treat model outputs as research classifications, not authoritative outbreak forecasts or medical advice; validate with a larger, temporally independent dataset before operational use.
- Runtime emitted scikit-learn `InconsistentVersionWarning`: the pickled scaler/encoder report version 1.9.0 while this environment runs 1.9.1. Loading and inference passed here, but pin/re-export artifacts with a consistent scikit-learn version to avoid future compatibility uncertainty.

## Remaining Work

1. Run an authenticated browser-level submit/result/history check with a valid user session.
2. Re-evaluate the model on a larger, temporally independent holdout and refresh the artifacts/metrics if warranted.
3. Align the scikit-learn version used to create and load the serialized preprocessing artifacts.

## Files Changed

- `backend/app/routes/prediction.py`
- `backend/app/services/prediction.py`
- `backend/tests/test_prediction_api.py`
- `backend/tests/test_prediction_model_integration.py`
- `frontend/src/pages/Prediction.jsx`
- `frontend/src/pages/History.jsx`
- `frontend/src/utils/dashboardData.js`
- `frontend/src/pages/HomePage.jsx`
- `docs/prediction-testing-report.md`
