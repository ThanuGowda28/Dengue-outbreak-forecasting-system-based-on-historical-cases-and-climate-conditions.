from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..ml.dataset.climate_data_acquisition import canonical_state_name
from .andhra_pradesh_districts import ANDHRA_PRADESH_DISTRICTS
from .karnataka_districts import KARNATAKA_DISTRICTS

CLIMATE_COLUMNS = {
    "temperature": "temperature_c",
    "humidity": "relative_humidity_pct",
    "rainfall": "precipitation_mm_day",
    "wind_speed": "wind_speed_m_s",
    "solar_radiation": "solar_radiation_mj_m2_day",
}
DISTRICTS_BY_STATE = {
    "Andhra Pradesh": [item["district"] for item in ANDHRA_PRADESH_DISTRICTS],
    "Karnataka": [item["district"] for item in KARNATAKA_DISTRICTS],
}
RECOMMENDATIONS = {
    "Low": [
        "Continue routine mosquito surveillance and source reduction.",
        "Share seasonal prevention guidance with the community.",
    ],
    "Moderate": [
        "Increase mosquito surveillance in affected communities.",
        "Promote community awareness and water stagnation control.",
        "Review local clinic readiness for seasonal increases.",
    ],
    "High": [
        "Increase mosquito surveillance and community awareness.",
        "Strengthen hospital and primary-care preparedness.",
        "Prioritize water stagnation control in high-risk areas.",
    ],
    "Very High": [
        "Activate intensified mosquito surveillance and public communication.",
        "Coordinate hospital preparedness and essential supply checks.",
        "Conduct urgent water stagnation control and source reduction.",
    ],
}
FORECAST_START_YEAR = 2026
FORECAST_HORIZON_YEARS = 5


class ForecastingError(RuntimeError):
    """Raised when historical source data cannot support a forecast."""


def _dataset_directory() -> Path:
    return Path(__file__).resolve().parents[1] / "ml" / "dataset" / "raw"


@lru_cache(maxsize=1)
def _load_annual_data(
    climate_path: str, dengue_path: str, excluded_year: int
) -> pd.DataFrame:
    climate_file = Path(climate_path)
    dengue_file = Path(dengue_path)
    if not climate_file.is_file() or not dengue_file.is_file():
        raise ForecastingError("Historical climate or dengue data files are unavailable.")

    try:
        climate_daily = pd.read_csv(climate_file)
        dengue_wide = pd.read_csv(dengue_file)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ForecastingError("Historical forecasting data could not be read.") from error

    required_climate = {"state_ut", "year", *CLIMATE_COLUMNS.values()}
    required_dengue = {"state_ut"}
    if not required_climate.issubset(climate_daily.columns):
        raise ForecastingError("Historical climate data is missing required fields.")
    if not required_dengue.issubset(dengue_wide.columns):
        raise ForecastingError("Historical dengue data is missing required fields.")

    climate_daily["state"] = climate_daily["state_ut"].map(canonical_state_name)
    climate_daily["year"] = pd.to_numeric(climate_daily["year"], errors="coerce")
    climate_daily = climate_daily.loc[
        climate_daily["state"].notna()
        & climate_daily["year"].notna()
        & (climate_daily["year"] < excluded_year)
    ].copy()

    for column in CLIMATE_COLUMNS.values():
        climate_daily[column] = pd.to_numeric(climate_daily[column], errors="coerce")
    climate_daily = climate_daily.loc[
        climate_daily["temperature_c"].between(-90, 65)
        & climate_daily["relative_humidity_pct"].between(0, 100)
        & climate_daily["precipitation_mm_day"].between(0, 250)
        & climate_daily["wind_speed_m_s"].between(0, 100)
        & climate_daily["solar_radiation_mj_m2_day"].between(0, 60)
    ]
    climate_annual = climate_daily.groupby(["state", "year"], as_index=False).agg(
        temperature=("temperature_c", "mean"),
        humidity=("relative_humidity_pct", "mean"),
        rainfall=("precipitation_mm_day", "sum"),
        wind_speed=("wind_speed_m_s", "mean"),
        solar_radiation=("solar_radiation_mj_m2_day", "mean"),
    )

    dengue_wide["state"] = dengue_wide["state_ut"].map(canonical_state_name)
    dengue_rows: list[dict[str, Any]] = []
    for column in dengue_wide.columns:
        match = re.fullmatch(r"cases_(20\d{2})", column)
        if match is None:
            continue
        year = int(match.group(1))
        if year >= excluded_year:
            continue
        values = pd.to_numeric(dengue_wide[column], errors="coerce")
        for state, value in zip(dengue_wide["state"], values):
            if state and pd.notna(value) and math.isfinite(float(value)) and value >= 0:
                dengue_rows.append(
                    {"state": state, "year": year, "confirmed_cases": float(value)}
                )
    if not dengue_rows:
        raise ForecastingError("Historical dengue case data is unavailable.")
    dengue_annual = pd.DataFrame(dengue_rows).groupby(
        ["state", "year"], as_index=False
    )["confirmed_cases"].sum()
    annual = climate_annual.merge(
        dengue_annual, on=["state", "year"], how="inner", validate="one_to_one"
    )
    if annual.empty:
        raise ForecastingError("No matching annual climate and dengue records were found.")
    return annual.sort_values(["state", "year"]).reset_index(drop=True)


class ForecastingService:
    """Transparent linear trend projection over historical climate and dengue data."""

    def __init__(self, data_directory: str | Path | None = None):
        directory = Path(data_directory) if data_directory else _dataset_directory()
        self.climate_path = str(directory / "climate_data.csv")
        self.dengue_path = str(directory / "ncvbdc_dengue.csv")

    def annual_data(self) -> pd.DataFrame:
        from datetime import datetime

        return _load_annual_data(
            self.climate_path,
            self.dengue_path,
            datetime.now().year,
        ).copy()

    def options(self) -> dict[str, Any]:
        annual = self.annual_data()
        states = sorted(annual["state"].unique().tolist())
        return {
            "states": states,
            "districts_by_state": {
                state: districts
                for state, districts in DISTRICTS_BY_STATE.items()
                if state in states
            },
            "available_years": sorted(int(year) for year in annual["year"].unique()),
            "maximum_history_years": 10,
            "forecast_years": list(
                range(
                    FORECAST_START_YEAR,
                    FORECAST_START_YEAR + FORECAST_HORIZON_YEARS,
                )
            ),
        }

    def trends(self, state: str, years: int = 5) -> dict[str, Any]:
        if years not in (5, 10):
            raise ValueError("years must be 5 or 10.")
        frame = self._state_data(state)
        frame = frame.tail(years)
        return {
            "state": state,
            "years_requested": years,
            "years_available": len(frame),
            "history": [
                {
                    "year": int(row.year),
                    "temperature": round(float(row.temperature), 2),
                    "humidity": round(float(row.humidity), 2),
                    "rainfall": round(float(row.rainfall), 2),
                    "wind_speed": round(float(row.wind_speed), 2),
                    "solar_radiation": round(float(row.solar_radiation), 2),
                    "confirmed_cases": int(round(float(row.confirmed_cases))),
                    "risk": self._risk_label(float(row.confirmed_cases), frame["confirmed_cases"]),
                }
                for row in frame.itertuples(index=False)
            ],
            "data_note": (
                "Annual state-level historical data; the current calendar year is excluded "
                "because its observations may be incomplete."
            ),
        }

    def forecast(self, state: str, forecast_year: int, district: str | None = None) -> dict[str, Any]:
        frame = self._state_data(state)
        if isinstance(forecast_year, bool) or not isinstance(forecast_year, int):
            raise ValueError("forecast_year must be an integer.")
        last_year = FORECAST_START_YEAR + FORECAST_HORIZON_YEARS - 1
        if not FORECAST_START_YEAR <= forecast_year <= last_year:
            raise ValueError(
                f"forecast_year must be between {FORECAST_START_YEAR} and {last_year}."
            )
        if district is not None:
            if not isinstance(district, str) or district not in DISTRICTS_BY_STATE.get(state, []):
                raise ValueError("district must be a supported district for the selected state.")

        cases = frame["confirmed_cases"].to_numpy(dtype=float)
        years = frame["year"].to_numpy(dtype=float)
        if len(cases) < 3:
            raise ForecastingError("At least three complete annual observations are required.")
        slope, intercept = np.polyfit(years, cases, deg=1)
        projected_cases = max(0.0, float(slope * forecast_year + intercept))
        latest_cases = float(cases[-1])
        tolerance = max(1.0, latest_cases * 0.05)
        trend = (
            "Increasing" if projected_cases > latest_cases + tolerance
            else "Decreasing" if projected_cases < latest_cases - tolerance
            else "Stable"
        )
        risk = self._risk_label(projected_cases, frame["confirmed_cases"])
        fitted = slope * years + intercept
        total_variance = float(np.sum((cases - cases.mean()) ** 2))
        residual_variance = float(np.sum((cases - fitted) ** 2))
        fit_score = 1.0 if total_variance == 0 else max(0.0, 1 - residual_variance / total_variance)
        confidence = round(min(90.0, 45.0 + min(len(cases), 6) * 3.0 + fit_score * 25.0), 1)

        climate_trend = self.trends(state, years=10)["history"]
        timeline = [
            {
                "year": int(row.year),
                "risk": self._risk_label(float(row.confirmed_cases), frame["confirmed_cases"]),
                "confirmed_cases": int(round(float(row.confirmed_cases))),
                "kind": "historical",
            }
            for row in frame.itertuples(index=False)
        ]
        timeline.append(
            {
                "year": forecast_year,
                "risk": risk,
                "confirmed_cases": int(round(projected_cases)),
                "kind": "forecast",
            }
        )
        return {
            "forecast_year": forecast_year,
            "state": state,
            "district": district,
            "risk": risk,
            "confidence": confidence,
            "expected_trend": trend,
            "projected_cases": round(projected_cases),
            "latest_historical_year": int(frame["year"].max()),
            "latest_historical_risk": timeline[-2]["risk"],
            "risk_summary": (
                f"The linear trend projects approximately {round(projected_cases):,} reported "
                f"cases for {state} in {forecast_year}, corresponding to a {risk.lower()} "
                "historical-range category."
            ),
            "recommendations": RECOMMENDATIONS[risk],
            "climate_summary": climate_trend,
            "timeline": timeline,
            "method": (
                "Exploratory linear trend projection using complete annual state-level "
                "historical dengue cases. It is not a trained forecasting model; confidence "
                "is a heuristic fit indicator, not a calibrated probability."
            ),
        }

    def map_forecasts(self, forecast_year: int) -> list[dict[str, Any]]:
        from ..ml.dataset.climate_data_acquisition import STATE_UT_COORDINATES

        annual = self.annual_data()
        output = []
        for state in sorted(annual["state"].unique()):
            latitude_longitude = STATE_UT_COORDINATES.get(state)
            if latitude_longitude is None:
                continue
            result = self.forecast(state, forecast_year)
            output.append(
                {
                    "state": state,
                    "latitude": latitude_longitude[0],
                    "longitude": latitude_longitude[1],
                    "risk": result["risk"],
                    "confidence": result["confidence"],
                    "forecast_year": forecast_year,
                }
            )
        return output

    def _state_data(self, state: str) -> pd.DataFrame:
        if not isinstance(state, str) or not state.strip():
            raise ValueError("state is required.")
        canonical = canonical_state_name(state)
        if canonical is None:
            raise ValueError("Select a recognized Indian state or union territory.")
        frame = self.annual_data()
        selected = frame.loc[frame["state"] == canonical].copy()
        if len(selected) < 3:
            raise ValueError("At least three complete annual records are required for this state.")
        return selected.sort_values("year").reset_index(drop=True)

    @staticmethod
    def _risk_label(value: float, historical_cases: pd.Series) -> str:
        values = pd.to_numeric(historical_cases, errors="coerce").dropna().to_numpy(dtype=float)
        low, moderate, high = np.quantile(values, [0.25, 0.5, 0.75])
        if value <= low:
            return "Low"
        if value <= moderate:
            return "Moderate"
        if value <= high:
            return "High"
        return "Very High"
