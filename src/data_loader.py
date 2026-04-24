"""Data loading with CSV-first strategy and embedded fallback data."""

from __future__ import annotations

import pandas as pd
from pathlib import Path

from .config import (
    DATA_DIR,
    DEFAULT_CITIES,
    CITY_REGIONS,
    CITY_STATE_TAX_RATES,
    get_display_name,
)

# ---------------------------------------------------------------------------
# Embedded fallback dataset (2023-2024 estimates from public sources)
# Used when scraped CSV files are not present.
# ---------------------------------------------------------------------------
_FALLBACK_ROWS = [
    {
        "city": "Boston",
        "cost_of_living_index": 82.4,
        "rent_index": 68.2,
        "groceries_index": 77.5,
        "restaurant_price_index": 76.8,
        "local_purchasing_power_index": 115.2,
        "median_gross_rent": 2200,
        "median_household_income": 79298,
        "total_population": 675647,
        "unemployment_rate_pct": 3.8,
        "median_home_value": 598900,
    },
    {
        "city": "New-York",
        "cost_of_living_index": 100.0,
        "rent_index": 100.0,
        "groceries_index": 86.4,
        "restaurant_price_index": 95.2,
        "local_purchasing_power_index": 100.0,
        "median_gross_rent": 2400,
        "median_household_income": 70663,
        "total_population": 8336817,
        "unemployment_rate_pct": 5.1,
        "median_home_value": 680000,
    },
    {
        "city": "San-Francisco",
        "cost_of_living_index": 94.7,
        "rent_index": 110.3,
        "groceries_index": 89.2,
        "restaurant_price_index": 87.1,
        "local_purchasing_power_index": 135.4,
        "median_gross_rent": 3000,
        "median_household_income": 126187,
        "total_population": 873965,
        "unemployment_rate_pct": 3.4,
        "median_home_value": 1100000,
    },
    {
        "city": "Austin",
        "cost_of_living_index": 68.5,
        "rent_index": 50.2,
        "groceries_index": 68.5,
        "restaurant_price_index": 65.3,
        "local_purchasing_power_index": 110.8,
        "median_gross_rent": 1650,
        "median_household_income": 75752,
        "total_population": 961855,
        "unemployment_rate_pct": 3.3,
        "median_home_value": 485000,
    },
    {
        "city": "Seattle",
        "cost_of_living_index": 80.3,
        "rent_index": 72.4,
        "groceries_index": 79.8,
        "restaurant_price_index": 74.6,
        "local_purchasing_power_index": 130.2,
        "median_gross_rent": 2100,
        "median_household_income": 105391,
        "total_population": 737255,
        "unemployment_rate_pct": 3.5,
        "median_home_value": 775000,
    },
    {
        "city": "Chicago",
        "cost_of_living_index": 73.2,
        "rent_index": 51.8,
        "groceries_index": 74.9,
        "restaurant_price_index": 72.1,
        "local_purchasing_power_index": 105.6,
        "median_gross_rent": 1600,
        "median_household_income": 65501,
        "total_population": 2746388,
        "unemployment_rate_pct": 4.6,
        "median_home_value": 305000,
    },
    {
        "city": "Denver",
        "cost_of_living_index": 73.8,
        "rent_index": 58.6,
        "groceries_index": 72.3,
        "restaurant_price_index": 70.5,
        "local_purchasing_power_index": 113.4,
        "median_gross_rent": 1800,
        "median_household_income": 72971,
        "total_population": 715522,
        "unemployment_rate_pct": 3.4,
        "median_home_value": 555000,
    },
    {
        "city": "Atlanta",
        "cost_of_living_index": 63.4,
        "rent_index": 47.2,
        "groceries_index": 64.8,
        "restaurant_price_index": 63.9,
        "local_purchasing_power_index": 107.2,
        "median_gross_rent": 1550,
        "median_household_income": 72498,
        "total_population": 498715,
        "unemployment_rate_pct": 4.2,
        "median_home_value": 360000,
    },
    {
        "city": "Miami",
        "cost_of_living_index": 74.5,
        "rent_index": 62.3,
        "groceries_index": 73.2,
        "restaurant_price_index": 71.8,
        "local_purchasing_power_index": 95.8,
        "median_gross_rent": 2000,
        "median_household_income": 53572,
        "total_population": 449514,
        "unemployment_rate_pct": 4.0,
        "median_home_value": 590000,
    },
    {
        "city": "Los-Angeles",
        "cost_of_living_index": 87.6,
        "rent_index": 82.5,
        "groceries_index": 83.7,
        "restaurant_price_index": 83.2,
        "local_purchasing_power_index": 105.3,
        "median_gross_rent": 2200,
        "median_household_income": 72797,
        "total_population": 3898747,
        "unemployment_rate_pct": 5.0,
        "median_home_value": 790000,
    },
    {
        "city": "Dallas",
        "cost_of_living_index": 66.2,
        "rent_index": 48.9,
        "groceries_index": 66.7,
        "restaurant_price_index": 66.3,
        "local_purchasing_power_index": 108.4,
        "median_gross_rent": 1500,
        "median_household_income": 58580,
        "total_population": 1304379,
        "unemployment_rate_pct": 3.8,
        "median_home_value": 310000,
    },
    {
        "city": "Portland",
        "cost_of_living_index": 73.1,
        "rent_index": 57.4,
        "groceries_index": 74.5,
        "restaurant_price_index": 70.2,
        "local_purchasing_power_index": 112.6,
        "median_gross_rent": 1700,
        "median_household_income": 75657,
        "total_population": 652503,
        "unemployment_rate_pct": 4.1,
        "median_home_value": 480000,
    },
    {
        "city": "Nashville",
        "cost_of_living_index": 65.8,
        "rent_index": 51.6,
        "groceries_index": 64.2,
        "restaurant_price_index": 65.1,
        "local_purchasing_power_index": 111.5,
        "median_gross_rent": 1600,
        "median_household_income": 70222,
        "total_population": 715884,
        "unemployment_rate_pct": 2.9,
        "median_home_value": 390000,
    },
    {
        "city": "Phoenix",
        "cost_of_living_index": 64.3,
        "rent_index": 49.8,
        "groceries_index": 63.9,
        "restaurant_price_index": 63.7,
        "local_purchasing_power_index": 109.3,
        "median_gross_rent": 1500,
        "median_household_income": 62055,
        "total_population": 1608139,
        "unemployment_rate_pct": 3.6,
        "median_home_value": 320000,
    },
    {
        "city": "Minneapolis",
        "cost_of_living_index": 68.9,
        "rent_index": 47.5,
        "groceries_index": 71.3,
        "restaurant_price_index": 67.8,
        "local_purchasing_power_index": 116.4,
        "median_gross_rent": 1450,
        "median_household_income": 63590,
        "total_population": 429606,
        "unemployment_rate_pct": 3.2,
        "median_home_value": 295000,
    },
]


def _enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add display name, region, and state tax columns."""
    df = df.copy()
    df["display_name"] = df["city"].map(get_display_name)
    df["region"] = df["city"].map(lambda c: CITY_REGIONS.get(c, "Other"))
    df["state_tax_rate"] = df["city"].map(
        lambda c: CITY_STATE_TAX_RATES.get(c, 0.05)
    )
    return df


def load_city_data(data_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    """
    Load city data. Returns (DataFrame, source_label).

    Priority:
      1. data/master_summary.csv  (generated by scraper)
      2. data/processed/          (intermediate files)
      3. Built-in fallback estimates
    """
    search_dir = data_dir or DATA_DIR

    # --- Try master summary first -------------------------------------------
    master_path = search_dir / "master_summary.csv"
    if master_path.exists():
        try:
            df = pd.read_csv(master_path)
            df = _clean_scraped_df(df)
            if len(df) >= 5:
                return _enrich_dataframe(df), "scraped"
        except Exception:
            pass

    # --- Try individual processed files -------------------------------------
    numbeo_path = search_dir / "processed" / "numbeo_indices.csv"
    census_path = search_dir / "processed" / "census_places.csv"
    if not numbeo_path.exists():
        numbeo_path = search_dir / "raw" / "numbeo_indices.csv"
    if not census_path.exists():
        census_path = search_dir / "raw" / "census_places.csv"

    if numbeo_path.exists() and census_path.exists():
        try:
            df = _merge_raw_files(numbeo_path, census_path)
            if len(df) >= 5:
                return _enrich_dataframe(df), "scraped"
        except Exception:
            pass

    # --- Fallback to embedded data ------------------------------------------
    df = pd.DataFrame(_FALLBACK_ROWS)
    return _enrich_dataframe(df), "fallback"


def _clean_scraped_df(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise column names and deduplicate after scraper merge."""
    # Deduplicate: keep highest-population row per city
    if "total_population" in df.columns and "city" in df.columns:
        df["total_population"] = pd.to_numeric(
            df["total_population"], errors="coerce"
        )
        df = df.sort_values("total_population", ascending=False)
        df = df.drop_duplicates(subset=["city"], keep="first")

    # Ensure numeric types for key columns
    numeric_cols = [
        "cost_of_living_index",
        "rent_index",
        "groceries_index",
        "restaurant_price_index",
        "local_purchasing_power_index",
        "median_gross_rent",
        "median_household_income",
        "total_population",
        "unemployment_rate_pct",
        "median_home_value",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.reset_index(drop=True)


def _merge_raw_files(
    numbeo_path: Path, census_path: Path
) -> pd.DataFrame:
    """Merge raw Numbeo and Census files the same way the scraper does."""
    import re

    numbeo = pd.read_csv(numbeo_path)
    census = pd.read_csv(census_path)

    numbeo["city_norm"] = numbeo["city"].str.lower().str.replace("-", " ")
    census["city_norm"] = (
        census["place_name"]
        .str.lower()
        .str.replace(r"\s*(city|town|village|cdp|borough).*", "", regex=True)
        .str.strip()
    )

    merged = numbeo.merge(census, on="city_norm", how="left", suffixes=("", "_census"))
    return _clean_scraped_df(merged)


def filter_by_region(
    df: pd.DataFrame, region: str
) -> pd.DataFrame:
    if region == "Any":
        return df
    return df[df["region"] == region].reset_index(drop=True)
