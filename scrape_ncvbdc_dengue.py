"""Download and parse the NCVBDC India dengue cases/deaths table."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

PAGE_URL = "https://ncvbdc.mohfw.gov.in/index4.php?lang=1&level=0&linkid=431&lid=3715"
OUTPUT_PATH = Path(__file__).resolve().parent / "backend" / "app" / "ml" / "dataset" / "raw" / "ncvbdc_dengue.csv"
TABLE_TITLE = "Dengue Cases and Deaths in the Country"
MISSING_MARKERS = {"", "-", "--", "?", "?", "na", "n/a", "null", "none"}


class ScrapeError(RuntimeError):
    """Raised when the source page or expected table cannot be read."""


def clean_cell(value: str) -> str | None:
    """Collapse whitespace and normalize common missing-value markers."""
    cleaned = re.sub(r"\s+", " ", value).strip()
    if cleaned.casefold() in MISSING_MARKERS:
        return None
    return cleaned


def find_dengue_table(soup: BeautifulSoup) -> Tag:
    """Find the table associated with the requested caption/heading."""
    title_pattern = re.compile(r"\s+".join(map(re.escape, TABLE_TITLE.split())), re.IGNORECASE)
    for text_node in soup.find_all(string=title_pattern):
        parent = text_node.parent
        if not isinstance(parent, Tag):
            continue
        table = parent.find_next("table")
        if table is not None:
            return table

    for table in soup.find_all("table"):
        text = re.sub(r"\s+", " ", table.get_text(" ", strip=True)).casefold()
        if TABLE_TITLE.casefold() in text:
            return table

    raise ScrapeError(f'Could not locate the "{TABLE_TITLE}" table on the page.')


def extract_years(header_rows: list[list[str]]) -> list[str]:
    years: list[str] = []
    for value in (cell for row in header_rows for cell in row):
        match = re.fullmatch(r"(19|20)\d{2}\s*\*?", value)
        if match:
            year = re.sub(r"\D", "", value)
            if year not in years:
                years.append(year)
    if not years:
        raise ScrapeError("The dengue table does not contain year headings.")
    return years


def make_columns(years: Iterable[str]) -> list[str]:
    columns = ["serial_number", "state_ut"]
    for year in years:
        columns.extend((f"cases_{year}", f"deaths_{year}"))
    return columns


def parse_table(table: Tag) -> pd.DataFrame:
    rows = table.find_all("tr")
    if not rows:
        raise ScrapeError("The dengue table is empty.")

    parsed_rows: list[list[str]] = []
    for row in rows:
        values = [
            re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip()
            for cell in row.find_all(("th", "td"), recursive=False)
        ]
        if values:
            parsed_rows.append(values)
    if not parsed_rows:
        raise ScrapeError("The dengue table contains no readable rows.")

    header_indices = [
        index
        for index, row in enumerate(parsed_rows[:4])
        if any("affected states" in cell.casefold() for cell in row)
        or any(cell.casefold() in {"sl. no.", "sl no.", "serial no."} for cell in row)
    ]
    if not header_indices:
        raise ScrapeError("Could not identify the dengue table header rows.")
    first_header = header_indices[0]
    years = extract_years(parsed_rows[first_header : min(first_header + 3, len(parsed_rows))])
    columns = make_columns(years)
    expected_width = len(columns)

    data: list[list[str | None]] = []
    for row in parsed_rows[first_header + 1 :]:
        cells = [clean_cell(value) for value in row]
        if not any(cells):
            continue
        if len(cells) == expected_width - 2 and all(
            (value or "").casefold() in {"c", "d"} for value in cells
        ):
            continue
        joined = " ".join(value or "" for value in cells).casefold()
        if "affected states" in joined or ("cases" in joined and "deaths" in joined):
            continue
        if any(re.fullmatch(r"(19|20)\d{2}\s*\*?", value or "") for value in cells):
            continue
        if len(cells) < expected_width:
            cells.extend([None] * (expected_width - len(cells)))
        elif len(cells) > expected_width:
            cells = cells[:expected_width]
        if cells[1] is None:
            continue
        data.append(cells)

    if not data:
        raise ScrapeError("The dengue table was found but contained no data rows.")

    frame = pd.DataFrame(data, columns=columns)
    for column in columns[2:]:
        frame[column] = pd.to_numeric(
            frame[column].astype("string").str.replace(",", "", regex=False),
            errors="coerce",
        ).astype("Int64")
    frame["serial_number"] = pd.to_numeric(frame["serial_number"], errors="coerce").astype("Int64")
    frame["state_ut"] = frame["state_ut"].astype("string").str.strip()
    frame = frame.dropna(how="all").reset_index(drop=True)
    return frame


def scrape(output_path: Path = OUTPUT_PATH) -> pd.DataFrame:
    """Fetch the official page, extract the target table, and save it as CSV."""
    try:
        response = requests.get(
            PAGE_URL,
            headers={"User-Agent": "DengueOutbreakResearch/1.0 (public data extraction)"},
            timeout=(10, 30),
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise ScrapeError(f"Could not download NCVBDC page: {error}") from error

    soup = BeautifulSoup(response.content, "html.parser")
    table = find_dengue_table(soup)
    frame = parse_table(table)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_csv(output_path, index=False, na_rep="")
    except OSError as error:
        raise ScrapeError(f"Could not save CSV to '{output_path}': {error}") from error
    return frame


def main() -> int:
    try:
        frame = scrape()
    except ScrapeError as error:
        print(f"NCVBDC dengue data scrape failed: {error}", file=sys.stderr)
        return 1

    print(f"Saved CSV: {OUTPUT_PATH}")
    print(f"Total rows: {len(frame)}")
    print(f"Column names: {list(frame.columns)}")
    print("First five rows:")
    print(frame.head().to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
