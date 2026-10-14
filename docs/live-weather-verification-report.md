# Live Weather Verification Report

**Run date:** 2026-10-13  
**Scope:** Configured application weather district catalogue and the live
OpenWeather/NASA POWER provider integrations. Requests were made through the
Flask API using its test client, so route handling, JWT enforcement,
normalization, cache behavior, and MySQL persistence were exercised; provider
requests themselves were live. A uniquely named temporary verified account
was used and removed after the run. No API key or credentials are included.

## Coverage and results

| Measure | Result |
|---|---:|
| Supported states in `/api/weather/districts` | 1 — Karnataka |
| Supported districts retrieved and tested | 31 |
| Authenticated district endpoint requests | 93 (31 districts × 3 endpoints) |
| Successful requests | 93 |
| Failed requests | 0 |
| Success rate | 100% |
| Average response time | 1,160.4 ms |

Per-endpoint results:

| Endpoint | Success | Average response time | Provider |
|---|---:|---:|---|
| `GET /api/weather/current` | 31/31 | 1,026.3 ms | OpenWeather |
| `GET /api/weather/forecast` | 31/31 | 1,110.4 ms | OpenWeather |
| `GET /api/weather/history` | 31/31 | 1,344.3 ms | NASA POWER |

The historical query used 2026-10-08, within the API's accepted past-date
range. Forecast requests asked for one day; the provider returned eight
forecast intervals for each district.

## District results

All entries below returned HTTP 200 with valid JSON. Every response included
numeric temperature, humidity, rainfall/precipitation, wind speed, and
latitude/longitude coordinates; source metadata matched the expected provider.
No required measurement or coordinate was null or invalid.

| State | District | Current (ms) | Forecast (ms) | History (ms) |
|---|---|---:|---:|---:|
| Karnataka | Bagalkote | 1,334.2 | 2,455.4 | 2,038.8 |
| Karnataka | Ballari | 1,951.8 | 903.8 | 1,239.4 |
| Karnataka | Belagavi | 890.2 | 913.6 | 1,275.1 |
| Karnataka | Bengaluru Rural | 967.8 | 1,005.5 | 1,233.2 |
| Karnataka | Bengaluru Urban | 861.0 | 948.0 | 1,295.1 |
| Karnataka | Bidar | 1,066.8 | 934.3 | 1,296.4 |
| Karnataka | Chamarajanagar | 951.2 | 1,961.4 | 1,594.2 |
| Karnataka | Chikkaballapur | 951.5 | 948.3 | 1,340.7 |
| Karnataka | Chikkamagaluru | 935.9 | 881.0 | 1,164.2 |
| Karnataka | Chitradurga | 962.5 | 995.9 | 1,357.8 |
| Karnataka | Dakshina Kannada | 936.0 | 884.1 | 1,358.3 |
| Karnataka | Davanagere | 844.4 | 905.5 | 1,188.3 |
| Karnataka | Dharwad | 913.2 | 1,059.7 | 1,652.9 |
| Karnataka | Gadag | 927.1 | 1,049.7 | 1,356.6 |
| Karnataka | Hassan | 908.7 | 972.6 | 1,912.2 |
| Karnataka | Haveri | 949.7 | 1,016.4 | 1,366.4 |
| Karnataka | Kalaburagi | 848.7 | 860.9 | 853.0 |
| Karnataka | Kodagu | 895.4 | 896.8 | 1,738.1 |
| Karnataka | Kolar | 870.9 | 852.9 | 1,286.6 |
| Karnataka | Koppal | 1,291.3 | 1,235.9 | 1,149.3 |
| Karnataka | Mandya | 876.5 | 848.0 | 1,331.5 |
| Karnataka | Mysuru | 895.6 | 838.5 | 1,407.6 |
| Karnataka | Raichur | 921.6 | 998.8 | 1,205.9 |
| Karnataka | Ramanagara | 918.7 | 1,007.5 | 827.3 |
| Karnataka | Shivamogga | 888.8 | 913.4 | 1,293.9 |
| Karnataka | Tumakuru | 2,325.4 | 900.1 | 937.5 |
| Karnataka | Udupi | 853.1 | 1,166.0 | 1,703.9 |
| Karnataka | Uttara Kannada | 1,129.8 | 3,318.4 | 1,477.8 |
| Karnataka | Vijayanagara | 919.7 | 1,016.3 | 1,247.5 |
| Karnataka | Vijayapura | 945.8 | 845.7 | 1,164.3 |
| Karnataka | Yadgir | 883.1 | 889.0 | 1,379.4 |

## Authentication and response validation

- Unauthenticated requests to current weather, forecast, and history each
  returned **401**.
- Authenticated requests for those same endpoints returned **200** for every
  district.
- All 93 API responses were valid JSON objects.
- All 93 had finite numeric temperature, humidity, rainfall/precipitation, and
  wind-speed values, plus valid numeric coordinates.
- Provider source was `openweather` for current/forecast and `nasa_power` for
  history.
- Current/forecast requests with no measurable precipitation returned numeric
  `0.0`, not null. Optional values such as UV index remain nullable by design.

## Cache verification

The configured process-local cache TTL was **300 seconds**. For current
weather, after clearing the cache:

| Request | Status | `cached` | Response time |
|---|---:|---:|---:|
| First request | 200 | `false` | 941.8 ms |
| Immediate repeat | 200 | `true` | 67.8 ms |
| After 301 seconds | 200 | `false` | 1,120.5 ms |

This confirms cache population, cache hit, and refresh after TTL expiry.

## Failures and fixes

- **Failed requests:** none.
- **Failed districts:** none.
- **Fixes required:** none; no source code changes were made.
- **Provider-side limitations encountered:** none during this run. Results are
  time-specific provider observations; availability and values can vary with
  provider service, credentials, quota, and network conditions.
