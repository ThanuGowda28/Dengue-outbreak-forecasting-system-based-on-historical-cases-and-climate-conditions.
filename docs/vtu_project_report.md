# VTU Final-Year Project Report Content

## Project title

**Ensemble Neural Network Approach to Forecast Dengue Outbreak Based on
Climate Conditions**

## Abstract

Dengue is a climate-sensitive mosquito-borne disease for which timely,
location-specific surveillance can support public-health planning. This
project develops a modular web-based research prototype that combines
historical dengue case counts and climate variables in an end-to-end data
workflow. Official annual NCVBDC dengue records are normalized to State/UT and
year. NASA POWER daily climate observations for representative administrative
centres are aggregated into annual temperature, relative humidity, rainfall,
wind speed, surface pressure, and solar-radiation features. The current
prepared dataset contains 190 State/UT-year examples from 2021 through 2026,
with separate training and testing files and preprocessing artifacts.

The system architecture includes a React frontend, Flask REST API, JWT-based
accounts, SQLAlchemy persistence, external weather services, and a trained
TensorFlow/Keras bundle defining three neural networks and a soft-voting
ensemble. Outbreak-risk labels are assigned transparently from annual
confirmed-case thresholds rather than randomly. The project provides weather
search, dashboards, maps, reporting, and prediction API integration.

The saved ensemble achieved 0.6579 accuracy, 0.6295 macro precision, 0.6001
macro recall, 0.6093 macro F1, and 0.8798 macro one-vs-rest ROC AUC on the
existing 38-row held-out test split. These are preliminary results only. The
2026 climate series is year-to-date, climate points represent one coordinate
per State/UT, and the limited annual sample and random split do not establish
future-year or external performance. The prototype is not a validated
public-health forecasting service.

## 1. Introduction

Dengue transmission is influenced by biological, environmental, and
population factors. Temperature and humidity can affect mosquito development
and survival, while rainfall can create breeding habitats; the relationships
are nonlinear and vary by geography and time. This motivates combining
surveillance records with climate observations while preserving clear
provenance and data-quality checks.

The project uses an ensemble neural-network approach as a research direction.
It builds an application around the workflow: acquire and validate source
data, aggregate annual climate indicators, engineer features, prepare
reproducible train/test files, define neural models, and expose model
availability through a web API. Account roles, weather endpoints, and
record-scoped dashboards make the prototype suitable for demonstration.

This application is decision support research only. It is not a diagnostic
system, does not replace public-health surveillance, and should not guide
clinical care or resource allocation without independent scientific and
operational validation.

## 2. Literature Survey

### 2.1 Dengue surveillance

Official case and death reports provide a fundamental outcome measure for
epidemiological analysis. Annual totals are useful for broad regional
comparisons but remove within-year timing and reporting delays. They should
not be interpreted as weekly outbreak-onset labels.

### 2.2 Climate and vector-borne disease

Temperature, humidity, and precipitation are frequently considered when
modelling vector ecology and dengue incidence. Their effects can be delayed,
nonlinear, and location-dependent. Using a single annual aggregate can hide
lagged and seasonal relationships. Future research should test monthly or
weekly observations and explicit lag features against suitable surveillance
data.

### 2.3 Neural networks and ensemble learning

Artificial neural networks can model nonlinear feature interactions.
Combining several networks by soft voting averages predicted class
probabilities and can reduce reliance on one architecture when member errors
are complementary. Ensemble performance must still be compared with
appropriate baselines and evaluated using temporally separated data,
calibration, class-sensitive metrics, and uncertainty analysis.

### 2.4 Data and software platforms

NASA POWER supplies gridded/point-accessible meteorological and solar
parameters. NCVBDC publishes national dengue case information. React and
Flask support a modular client/server design, while SQLAlchemy provides
relational persistence and TensorFlow/Keras provides a neural-network
implementation framework.

### 2.5 Gap addressed

The prototype focuses on a reproducible engineering pipeline linking
surveillance data, climate acquisition, preprocessing, an ensemble-training
implementation, and a web application. The saved model bundle is available to
the application; its scientific-validation limits are stated rather than
presenting preliminary classifications as operational forecasts.

## 3. Problem Statement

Historical dengue case counts and climate observations are stored in
different formats, temporal resolutions, and sources. Direct use without
normalization, data validation, and leakage-aware preprocessing can produce
incorrect or misleading model inputs. There is also a need for an accessible
application that presents real weather context and communicates the limits of
model outputs.

The problem is to design a modular application and data workflow that
converts verified dengue and climate records into structured annual
State/UT-level features and provides a secure interface for users to view
weather information and inspect research risk classifications using the saved
model. Those classifications are not scientifically validated outbreak
forecasts.

## 4. Objectives

1. Acquire and normalize official annual dengue case/death data.
2. Obtain NASA POWER climate variables for each source State/UT using
   documented representative coordinates.
3. Validate, aggregate, merge, and preprocess the local datasets without
   introducing random target labels.
4. Define three distinct ANN architectures and a soft-voting ensemble with
   training/evaluation/report generation code.
5. Provide a React and Flask architecture with authentication, weather
   access, dashboards, reports, map visualization, and prediction API
   integration.
6. Keep user records scoped, validate inputs, and report model availability
   and research limitations explicitly.
7. Document test evidence, limitations, and a safe path toward future
   validation and deployment.

## 5. Proposed Methodology

The implemented data workflow reads existing source CSVs, canonicalizes
State/UT names, converts annual dengue columns into one row per State/UT/year,
and aggregates NASA POWER daily values into annual climate statistics.
Climate metrics are imputed where necessary, data are validated, categorical
location/season/threshold categories are encoded, and train/test files are
written with fitted scaler and label-encoder artifacts.

The outbreak-risk target is rule-derived from annual confirmed cases:

| Class | Confirmed cases per State/UT/year |
| --- | ---: |
| Low Risk | < 1,000 |
| Moderate Risk | 1,000–9,999 |
| High Risk | ≥ 10,000 |

The offline trainer defines three fully connected networks using ReLU hidden
activations, softmax output, Adam, categorical cross-entropy, early stopping,
learning-rate reduction, and best-checkpoint handling. Soft voting averages
the three models' output probabilities. The intended evaluation includes
accuracy, precision, recall, F1, ROC AUC when applicable, confusion matrix,
classification report, loss curves, and comparison charts.

The saved ensemble was evaluated on the existing held-out test split without
retraining. The small random split, yearly State/UT aggregation, threshold-
derived labels, and partial-year 2026 inputs substantially limit interpretation.

## 6. System Design and Implementation

The client is a responsive React single-page application with lazy-loaded
routes, Axios services, Bootstrap styling, Leaflet mapping, and dashboard
components. The Flask application factory registers Blueprints for
authentication, weather, dashboard, reports, prediction, user records,
contact, administration, and health. JWT protects user APIs. SQLAlchemy models
store users, revoked tokens, verification tokens, weather and prediction
history, emergency contacts, prescription records, and preferences.

OpenWeather powers location search/current/forecast; NASA POWER is used for
historical observations and offline climate acquisition. Admin user/prediction
management, isolated dataset uploads, system reporting, climate-data browsing,
account recovery, and staged browser-triggered model training are implemented.
Training output does not automatically replace the active inference model.

## 7. Dataset and Current Results

The files currently present have these dimensions:

| Dataset | Rows | Columns |
| --- | ---: | ---: |
| NCVBDC annual source | 35 | 14 |
| NASA POWER climate source | 69,168 | 11 |
| Merged annual dataset | 190 | 16 |
| Training split | 152 | 49 |
| Testing split | 38 | 49 |

The merged data cover 2021–2026 with no missing cells or duplicate
State/UT-year keys in the inspected file. The target distribution is 88 Low, 67 Moderate, and 35 High. The test split
has 38 rows. The saved StandardScaler has 47 numeric input features, with year
left unscaled, and the label encoder classes align with the model's three
outputs.

### Held-out test evaluation

| Metric | Result |
| --- | ---: |
| Accuracy | 0.6579 |
| Macro precision | 0.6295 |
| Macro recall | 0.6001 |
| Macro F1-score | 0.6093 |
| Macro ROC AUC (one-vs-rest) | 0.8798 |

Confusion matrix (actual rows, predicted columns; class order High Risk, Low
Risk, Moderate Risk): `[[3, 0, 4], [1, 15, 2], [1, 5, 7]]`. Detailed metrics,
class report, ROC curve, and confusion-matrix image are saved under
`backend/app/ml/models/`; rerun them using
`python -m backend.app.ml.evaluate_model`. Repeated inference produced matching
probabilities for the same test inputs and seed.

Limitations include a small sample size, annual temporal resolution,
representative-point climate data, partial-year 2026 inputs, threshold-based
labels, possible reporting inconsistencies, and lack of independent external
validation. The random split does not establish performance on future years.
Probabilities are not calibrated; these metrics do not support clinical use or
operational public-health decisions.

## 8. Testing and Quality Assurance

The backend Python suite contains 23 tests and passes in the current
environment; the frontend Node test suite contains two passing tests and the
Vite production build passes. Backend line coverage is 52% for
`backend/app`, not an overall system coverage measure. Existing API tests use
in-memory SQLite, mocked weather providers, and a stub prediction service.
Live MySQL, external provider, complete authentication-flow, trained-model,
and container tests were not executed.

Refer to [the test report](./test_report.html) and
[the coverage report](./coverage_report.html) for details.

## 9. Conclusion and Future Work

The project delivers a structured data-preparation pipeline and a web
application integrating authentication, weather data, dashboards, and
prediction-service interfaces. It establishes reproducible target
definitions, saves preprocessing artifacts, and avoids fabricated inference
when the model package is absent.

Future work should complete a reproducible training run, verify every model
artifact and feature schema, add temporal/geographic validation and baselines,
evaluate probability calibration and uncertainty, obtain finer-grained
surveillance data, expand automated authentication and integration tests,
implement administrator workflows, add recovery/verification mechanisms,
protect detailed health probes, and validate a production deployment using
shared cache/rate-limit infrastructure.

## References

1. National Center for Vector Borne Diseases Control (NCVBDC), Ministry of
   Health and Family Welfare, Government of India, dengue cases and deaths
   data page: <https://ncvbdc.mohfw.gov.in/>.
2. NASA Prediction Of Worldwide Energy Resources (POWER), data access and
   parameter documentation: <https://power.larc.nasa.gov/>.
3. World Health Organization, “Dengue and severe dengue,” fact sheet:
   <https://www.who.int/news-room/fact-sheets/detail/dengue-and-severe-dengue>.
4. TensorFlow/Keras documentation: <https://www.tensorflow.org/guide/keras>.
5. scikit-learn user guide: <https://scikit-learn.org/stable/user_guide.html>.

Institution-specific certificate pages, student/guide details, diagrams,
formatted bibliography, and any additional VTU-required chapters should be
added by the submitting team. The visible project brief named Abstract,
Introduction, Literature Survey, Problem Statement, and Objectives; later
chapters above are standard supplementary report sections.
