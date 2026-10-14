"""Acquire and validate daily State/UT climate data from NASA POWER."""
from __future__ import annotations

import argparse
import html
import math
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

DATASET_DIR = Path(__file__).resolve().parent
RAW_DIR = DATASET_DIR / "raw"
DENGUE_DATASET = RAW_DIR / "ncvbdc_dengue.csv"
OUTPUT_CSV = RAW_DIR / "climate_data.csv"
VALIDATION_REPORT = RAW_DIR / "climate_validation_report.html"
NASA_POWER_URL = os.getenv("NASA_POWER_URL", "https://power.larc.nasa.gov/api/temporal/daily/point")
PARAMETERS = ("T2M", "RH2M", "PRECTOTCORR", "WS2M", "PS", "ALLSKY_SFC_SW_DWN")
REQUEST_TIMEOUT = (15, 90)
MAX_RETRIES = 3

# One representative administrative-centre coordinate per Indian State/UT.
# These point observations are not spatial averages for an entire State/UT.
STATE_UT_COORDINATES: dict[str, tuple[float, float]] = {
    "Andhra Pradesh": (16.5062, 80.6480), "Arunachal Pradesh": (27.0844, 93.6053),
    "Assam": (26.1433, 91.7898), "Bihar": (25.5941, 85.1376),
    "Chhattisgarh": (21.2514, 81.6296), "Goa": (15.4909, 73.8278),
    "Gujarat": (23.2156, 72.6369), "Haryana": (30.7333, 76.7794),
    "Himachal Pradesh": (31.1048, 77.1734), "Jharkhand": (23.3441, 85.3096),
    "Karnataka": (12.9716, 77.5946), "Kerala": (8.5241, 76.9366),
    "Madhya Pradesh": (23.2599, 77.4126), "Maharashtra": (19.0760, 72.8777),
    "Manipur": (24.8170, 93.9368), "Meghalaya": (25.5788, 91.8933),
    "Mizoram": (23.7271, 92.7176), "Nagaland": (25.6751, 94.1086),
    "Odisha": (20.2961, 85.8245), "Punjab": (30.7333, 76.7794),
    "Rajasthan": (26.9124, 75.7873), "Sikkim": (27.3314, 88.6138),
    "Tamil Nadu": (13.0827, 80.2707), "Telangana": (17.3850, 78.4867),
    "Tripura": (23.8315, 91.2868), "Uttar Pradesh": (26.8467, 80.9462),
    "Uttarakhand": (30.3165, 78.0322), "West Bengal": (22.5726, 88.3639),
    "Andaman and Nicobar Islands": (11.6234, 92.7265), "Chandigarh": (30.7333, 76.7794),
    "Dadra and Nagar Haveli and Daman and Diu": (20.3974, 72.8328),
    "Delhi": (28.6139, 77.2090), "Jammu and Kashmir": (34.0837, 74.7973),
    "Ladakh": (34.1526, 77.5771), "Lakshadweep": (10.5667, 72.6417),
    "Puducherry": (11.9416, 79.8083),
}
ALIASES = {
    "chattisgarh": "Chhattisgarh", "uttrakhand": "Uttarakhand", "uttaranchal": "Uttarakhand",
    "west bengal*": "West Bengal", "j & k": "Jammu and Kashmir", "j&k": "Jammu and Kashmir",
    "jammu & kashmir": "Jammu and Kashmir", "a& n island": "Andaman and Nicobar Islands",
    "a & n island": "Andaman and Nicobar Islands", "andaman & nicobar islands": "Andaman and Nicobar Islands",
    "d&n haveli": "Dadra and Nagar Haveli and Daman and Diu", "d & n haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "dadra and nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "puduchery": "Puducherry", "pondicherry": "Puducherry", "nct of delhi": "Delhi",
}
OUTPUT_COLUMNS = [
    "state_ut", "latitude", "longitude", "date", "year", "temperature_c",
    "relative_humidity_pct", "precipitation_mm_day", "wind_speed_m_s",
    "surface_pressure_kpa", "solar_radiation_mj_m2_day",
]
PARAMETER_COLUMNS = {
    "T2M": "temperature_c", "RH2M": "relative_humidity_pct",
    "PRECTOTCORR": "precipitation_mm_day", "WS2M": "wind_speed_m_s",
    "PS": "surface_pressure_kpa", "ALLSKY_SFC_SW_DWN": "solar_radiation_mj_m2_day",
}
VALID_RANGES = {
    "temperature_c": (-90.0, 65.0), "relative_humidity_pct": (0.0, 100.0),
    "precipitation_mm_day": (0.0, 2000.0), "wind_speed_m_s": (0.0, 100.0),
    "surface_pressure_kpa": (30.0, 120.0), "solar_radiation_mj_m2_day": (0.0, 60.0),
}


class AcquisitionError(RuntimeError):
    """Raised when required source data cannot be loaded or parsed."""


def canonical_state_name(value: Any) -> str | None:
    if pd.isna(value):
        return None
    name = re.sub(r"\s+", " ", str(value)).strip().rstrip("*")
    if not name or name.casefold() in {"total", "grand total"}:
        return None
    if name.casefold() in ALIASES:
        return ALIASES[name.casefold()]
    return next((state for state in STATE_UT_COORDINATES if state.casefold() == name.casefold()), None)


def load_states(path: Path = DENGUE_DATASET) -> list[str]:
    if not path.is_file():
        raise AcquisitionError(f"Dengue source CSV was not found: {path}")
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeError) as error:
        raise AcquisitionError(f"Could not read dengue source CSV '{path}': {error}") from error
    if "state_ut" not in frame.columns:
        raise AcquisitionError("The dengue CSV must contain a 'state_ut' column.")
    states: list[str] = []
    unknown: list[str] = []
    for value in frame["state_ut"]:
        raw_name = str(value).strip() if pd.notna(value) else ""
        state = canonical_state_name(value)
        if state:
            if state not in states:
                states.append(state)
        elif raw_name and raw_name.casefold() not in {"total", "grand total"} and not raw_name.isdigit():
            unknown.append(raw_name)
    if unknown:
        raise AcquisitionError("No coordinate mapping exists for: " + ", ".join(sorted(set(unknown))))
    if not states:
        raise AcquisitionError("No recognized Indian State/UT rows were found in the dengue CSV.")
    return states


def _numeric_value(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number in {-999.0, -9999.0}:
        return None
    return number


def _fetch_state(session: requests.Session, state: str, start_date: date, end_date: date) -> list[dict[str, Any]]:
    latitude, longitude = STATE_UT_COORDINATES[state]
    params = {
        "parameters": ",".join(PARAMETERS), "community": "AG", "longitude": longitude,
        "latitude": latitude, "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"), "format": "JSON",
    }
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(NASA_POWER_URL, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            daily = response.json()["properties"]["parameter"]
            if not isinstance(daily, dict) or not any(key in daily for key in PARAMETERS):
                raise AcquisitionError("NASA POWER response omitted requested parameters.")
            dates: set[str] = set()
            for parameter in PARAMETERS:
                if isinstance(daily.get(parameter), dict):
                    dates.update(daily[parameter])
            records = []
            for date_key in sorted(dates):
                try:
                    observed = datetime.strptime(date_key, "%Y%m%d").date()
                except ValueError:
                    continue
                if not start_date <= observed <= end_date:
                    continue
                record: dict[str, Any] = {
                    "state_ut": state, "latitude": latitude, "longitude": longitude,
                    "date": observed.isoformat(), "year": observed.year,
                }
                for parameter, column in PARAMETER_COLUMNS.items():
                    values = daily.get(parameter, {})
                    record[column] = _numeric_value(values.get(date_key)) if isinstance(values, dict) else None
                records.append(record)
            if not records:
                raise AcquisitionError(f"NASA POWER returned no daily records for {state}.")
            return records
        except (requests.RequestException, ValueError, KeyError, TypeError, AcquisitionError) as error:
            last_error = error
            if attempt < MAX_RETRIES:
                time.sleep(2 ** (attempt - 1))
    raise AcquisitionError(f"NASA POWER request failed for {state} after {MAX_RETRIES} attempts: {last_error}")


def validate_climate_data(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Count missing/invalid climate values and drop duplicate state/date rows."""
    if frame.empty:
        raise AcquisitionError("No climate records were acquired; cannot validate an empty dataset.")
    missing_columns = [column for column in OUTPUT_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise AcquisitionError(f"Climate data is missing required columns: {missing_columns}")
    result = frame.loc[:, OUTPUT_COLUMNS].copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    invalid_counts: dict[str, int] = {}
    invalid_examples: dict[str, list[str]] = {}
    for column, (lower, upper) in VALID_RANGES.items():
        values = pd.to_numeric(result[column], errors="coerce")
        invalid = values.notna() & (~values.between(lower, upper) | ~values.map(math.isfinite))
        invalid_counts[column] = int(invalid.sum())
        if invalid.any():
            invalid_examples[column] = values.loc[invalid].astype(str).head(5).tolist()
            values.loc[invalid] = float("nan")
        result[column] = values
    invalid_dates = int(result["date"].isna().sum())
    result["year"] = pd.to_numeric(result["year"], errors="coerce")
    invalid_years = int((result["year"].isna() | ~result["year"].between(2021, 2026)).sum())
    result["latitude"] = pd.to_numeric(result["latitude"], errors="coerce")
    result["longitude"] = pd.to_numeric(result["longitude"], errors="coerce")
    invalid_coordinates = int((result["latitude"].isna() | ~result["latitude"].between(-90, 90) | result["longitude"].isna() | ~result["longitude"].between(-180, 180)).sum())
    duplicates = result.duplicated(subset=["state_ut", "date"], keep="first")
    duplicate_count = int(duplicates.sum())
    result = result.loc[~duplicates].copy()
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    result["year"] = result["year"].astype("Int64")
    missing_counts = {column: int(count) for column, count in result.isna().sum().items()}
    report = {
        "records_before_duplicate_removal": int(len(frame)),
        "records_after_validation": int(len(result)),
        "duplicate_state_date_rows_detected_and_removed": duplicate_count,
        "missing_values_by_column": missing_counts,
        "rows_with_any_missing_climate_parameter": int(result[list(VALID_RANGES)].isna().any(axis=1).sum()),
        "invalid_values_replaced_with_missing": invalid_counts,
        "invalid_value_examples": invalid_examples,
        "invalid_date_rows": invalid_dates,
        "invalid_year_rows": invalid_years,
        "invalid_coordinate_rows": invalid_coordinates,
        "valid_ranges": {column: {"minimum": limits[0], "maximum": limits[1]} for column, limits in VALID_RANGES.items()},
        "duplicate_key": ["state_ut", "date"],
    }
    return result, report


def create_html_report(validation: dict[str, Any], states: list[str], years: list[int], failures: dict[str, str], path: Path) -> None:
    missing_rows = "".join(f"<tr><td>{html.escape(name)}</td><td>{count}</td></tr>" for name, count in validation["missing_values_by_column"].items())
    invalid_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{count}</td><td>{html.escape(', '.join(validation['invalid_value_examples'].get(name, [])) or '?')}</td></tr>"
        for name, count in validation["invalid_values_replaced_with_missing"].items()
    )
    range_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{limits['minimum']}</td><td>{limits['maximum']}</td></tr>"
        for name, limits in validation["valid_ranges"].items()
    )
    failure_rows = "".join(f"<tr><td>{html.escape(name)}</td><td>{html.escape(message)}</td></tr>" for name, message in failures.items()) or '<tr><td colspan="2">None</td></tr>'
    state_names = ", ".join(html.escape(state) for state in states)
    year_names = ", ".join(str(year) for year in years) or "None"
    status = "PARTIAL / FAILED" if failures else "COMPLETE"
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NASA POWER Climate Data Validation Report</title>
<style>body{{font:15px/1.5 Arial,sans-serif;color:#24313d;margin:2rem auto;max-width:1100px;padding:0 1rem}}h1,h2{{color:#00695c}}table{{border-collapse:collapse;width:100%;margin:1rem 0 2rem}}th,td{{border:1px solid #d4dde4;padding:.55rem;text-align:left}}th{{background:#e8f5f3}}.status{{font-weight:bold}}</style></head><body>
<h1>NASA POWER Climate Data Validation</h1><p class="status">Acquisition status: {status}</p><p>Generated UTC: {datetime.now(timezone.utc).isoformat()}</p>
<h2>Acquisition summary</h2><ul><li>States/UTs requested: {len(states)}</li><li>Request failures: {len(failures)}</li><li>Years with downloaded records: {year_names}</li><li>Records after duplicate removal: {validation['records_after_validation']}</li><li>Duplicate state/date rows removed: {validation['duplicate_state_date_rows_detected_and_removed']}</li><li>Rows with missing climate values: {validation['rows_with_any_missing_climate_parameter']}</li><li>Invalid dates, years, coordinates: {validation['invalid_date_rows']}, {validation['invalid_year_rows']}, {validation['invalid_coordinate_rows']}</li></ul>
<h2>States/UTs requested</h2><p>{state_names}</p><h2>Missing values by column</h2><table><thead><tr><th>Column</th><th>Missing count</th></tr></thead><tbody>{missing_rows}</tbody></table>
<h2>Invalid climate values replaced with missing</h2><table><thead><tr><th>Column</th><th>Count</th><th>Examples</th></tr></thead><tbody>{invalid_rows}</tbody></table>
<h2>Validity bounds</h2><table><thead><tr><th>Column</th><th>Minimum</th><th>Maximum</th></tr></thead><tbody>{range_rows}</tbody></table>
<h2>State/UT request failures</h2><table><thead><tr><th>State/UT</th><th>Error</th></tr></thead><tbody>{failure_rows}</tbody></table>
<p>Coordinates represent administrative-centre points, not state-wide averages. Source: NASA POWER Daily Point API; provider sentinels are treated as missing. Units: ?C, %, mm/day, m/s, kPa, and MJ/m?/day.</p></body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def acquire_climate_data(dengue_csv: Path = DENGUE_DATASET, output_csv: Path = OUTPUT_CSV, report_path: Path = VALIDATION_REPORT, start_date: date = date(2021, 1, 1), end_date: date | None = None) -> tuple[pd.DataFrame, dict[str, Any], list[str], list[int], dict[str, str]]:
    if end_date is None:
        end_date = min(date(2026, 12, 31), date.today() - timedelta(days=2))
    if start_date > end_date:
        raise AcquisitionError("Start date must not be later than end date.")
    states = load_states(dengue_csv)
    records: list[dict[str, Any]] = []
    failures: dict[str, str] = {}
    with requests.Session() as session:
        session.headers.update({"User-Agent": "DengueClimateResearch/1.0 (NASA POWER daily data)"})
        for index, state in enumerate(states):
            try:
                records.extend(_fetch_state(session, state, start_date, end_date))
                print(f"Downloaded {state}")
            except AcquisitionError as error:
                failures[state] = str(error)
                print(f"Warning: {error}", file=sys.stderr)
            if index + 1 < len(states):
                time.sleep(0.25)
    if not records:
        raise AcquisitionError("NASA POWER returned no records for any requested State/UT.")
    frame, validation = validate_climate_data(pd.DataFrame.from_records(records))
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_csv, index=False, na_rep="")
    years = sorted(int(year) for year in frame["year"].dropna().unique())
    create_html_report(validation, states, years, failures, report_path)
    return frame, validation, states, years, failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Download NASA POWER climate observations for State/UTs in NCVBDC data.")
    parser.add_argument("--input", type=Path, default=DENGUE_DATASET, help="NCVBDC source CSV")
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV, help="Climate CSV output")
    parser.add_argument("--report", type=Path, default=VALIDATION_REPORT, help="HTML validation report output")
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2021, 1, 1), help="Inclusive YYYY-MM-DD")
    parser.add_argument("--end-date", type=date.fromisoformat, default=None, help="Inclusive YYYY-MM-DD; default is two days ago, capped at 2026-12-31")
    args = parser.parse_args()
    try:
        frame, _, states, years, failures = acquire_climate_data(args.input, args.output, args.report, args.start_date, args.end_date)
    except (AcquisitionError, OSError) as error:
        print(f"Climate acquisition failed: {error}", file=sys.stderr)
        return 1
    print(f"Total states processed: {len(states) - len(failures)} of {len(states)} requested")
    print(f"Years downloaded: {years}")
    print(f"Total climate records: {len(frame)}")
    print("First five rows:")
    print(frame.head().to_string(index=False))
    print(f"Climate CSV: {args.output}")
    print(f"Validation report: {args.report}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
