"""
Post-Graduation Lifestyle Planner — Data Scraper
Group 3: Olivia Xie, Soukeyna Pitroipa, Carina Domat

Scrapes cost-of-living and city data from:
  1. Numbeo          — cost-of-living indices & itemised prices per city
  2. Census Bureau   — US population & demographic profiles (ACS 5-Year API)
  3. City-Data.com   — composite city index scores

Usage:
    python scraper.py                              # all sources, default cities
    python scraper.py --cities "Boston,Austin"     # custom city list
    python scraper.py --source numbeo              # single source only
    python scraper.py --output ./data              # custom output directory

Dependencies:
    pip install requests beautifulsoup4 pandas lxml
"""

import argparse
import os
import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_DELAY = 1.5  # seconds between requests — be polite to servers

DEFAULT_CITIES = [
    "Boston",
    "New-York",
    "San-Francisco",
    "Austin",
    "Seattle",
    "Chicago",
    "Denver",
    "Atlanta",
    "Miami",
    "Los-Angeles",
    "Dallas",
    "Portland",
    "Nashville",
    "Phoenix",
    "Minneapolis",
]

CENSUS_API_URL = "https://api.census.gov/data/2022/acs/acs5"

# ACS variables: Census code → friendly column name
CENSUS_VARS = {
    "B01003_001E": "total_population",
    "B19013_001E": "median_household_income",
    "B25064_001E": "median_gross_rent",
    "B08303_001E": "workers_travel_time_total",
    "B15003_022E": "bachelors_degree_holders",
    "B23025_004E": "employed_civilian_population",
    "B23025_005E": "unemployed_civilian_population",
    "B25077_001E": "median_home_value",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fetch(url: str, retries: int = 3, **kwargs) -> requests.Response | None:
    """GET a URL with retries and a polite delay between attempts."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            print(f"    [attempt {attempt}/{retries}] {exc}")
            if attempt < retries:
                time.sleep(REQUEST_DELAY * attempt)
    return None


def parse_html(resp: requests.Response) -> BeautifulSoup:
    return BeautifulSoup(resp.text, "lxml")


def slugify(city: str) -> str:
    """'New York' → 'New-York'  (Numbeo / city-data URL format)."""
    return city.strip().replace(" ", "-")


def safe_float(text: str) -> float | None:
    """Extract the first number from a string; return None if none found."""
    cleaned = text.strip().replace(",", "")
    match = re.search(r"-?\d+\.?\d*", cleaned)
    return float(match.group()) if match else None


# ---------------------------------------------------------------------------
# 1. Numbeo scraper
# ---------------------------------------------------------------------------


def scrape_numbeo_city(city: str) -> dict:
    """
    Scrape Numbeo cost-of-living data for a single US city.
    Returns a dict with 'indices' (summary table) and 'prices' (item list).
    """
    slug = slugify(city)
    url = f"https://www.numbeo.com/cost-of-living/in/{slug}"
    print(f"  Numbeo → {url}")

    resp = fetch(url)
    if resp is None:
        return {"city": city, "error": "request_failed"}

    page = parse_html(resp)

    # --- Summary index table (id="t2") -------------------------------------
    indices: dict = {"city": city, "source": "numbeo", "url": url}
    table = page.find("table", {"id": "t2"})
    if table:
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) == 2:
                label = cols[0].get_text(strip=True)
                value = safe_float(cols[1].get_text(strip=True))
                key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
                indices[key] = value

    # --- Individual price items (class="data_wide_table") ------------------
    prices: list[dict] = []
    for tbl in page.find_all("table", class_="data_wide_table"):
        # Determine category from nearest preceding h2 / h3
        category = "general"
        for sib in tbl.find_all_previous(["h2", "h3"]):
            cat_text = sib.get_text(strip=True)
            if cat_text:
                category = cat_text
                break

        for row in tbl.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) < 2:
                continue
            item = cols[0].get_text(strip=True)
            price = safe_float(cols[1].get_text(strip=True))
            low = safe_float(cols[2].get_text(strip=True)) if len(cols) > 2 else None
            high = safe_float(cols[3].get_text(strip=True)) if len(cols) > 3 else None
            prices.append(
                {
                    "city": city,
                    "category": category,
                    "item": item,
                    "price_usd": price,
                    "price_low_usd": low,
                    "price_high_usd": high,
                }
            )

    time.sleep(REQUEST_DELAY)
    return {"indices": indices, "prices": prices}


def scrape_numbeo(cities: list[str], raw_dir: Path, processed_dir: Path) -> None:
    print("\n=== Scraping Numbeo ===")
    all_indices: list[dict] = []
    all_prices: list[dict] = []

    for city in cities:
        result = scrape_numbeo_city(city)
        if "error" in result:
            print(f"  ✗ skipping {city}: {result['error']}")
            continue
        all_indices.append(result["indices"])
        all_prices.extend(result["prices"])

    if all_indices:
        df_idx = pd.DataFrame(all_indices)
        raw_path = raw_dir / "numbeo_indices.csv"
        proc_path = processed_dir / "numbeo_indices.csv"
        df_idx.to_csv(raw_path, index=False)
        df_idx.to_csv(proc_path, index=False)
        print(f"  ✓ saved {len(df_idx)} city rows → {proc_path}")

    if all_prices:
        df_prices = pd.DataFrame(all_prices)
        raw_path = raw_dir / "numbeo_prices.csv"
        proc_path = processed_dir / "numbeo_prices.csv"
        df_prices.to_csv(raw_path, index=False)
        df_prices.to_csv(proc_path, index=False)
        print(f"  ✓ saved {len(df_prices)} price rows → {proc_path}")


# ---------------------------------------------------------------------------
# 2. Census Bureau scraper (ACS 5-Year public API — no key required)
# ---------------------------------------------------------------------------


def scrape_census(raw_dir: Path, processed_dir: Path) -> None:
    """
    Pull selected ACS 5-year variables for all US places (cities/CDPs)
    via the Census Bureau's public JSON API.
    """
    print("\n=== Scraping Census Bureau (ACS 5-year 2022) ===")

    var_str = ",".join(CENSUS_VARS.keys())
    params = {
        "get": f"NAME,{var_str}",
        "for": "place:*",
        "in": "state:*",
    }

    print(f"  GET {CENSUS_API_URL} ...")
    resp = fetch(CENSUS_API_URL, params=params)
    if resp is None:
        print("  ✗ Census API request failed")
        return

    try:
        raw = resp.json()
    except ValueError:
        print("  ✗ Could not parse Census JSON response")
        return

    header_row, *data_rows = raw
    df = pd.DataFrame(data_rows, columns=header_row)

    rename_map = {"NAME": "place_name"}
    rename_map.update(CENSUS_VARS)
    df = df.rename(columns=rename_map)

    numeric_cols = list(CENSUS_VARS.values())
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["total_population"])

    employed = df["employed_civilian_population"]
    unemployed = df["unemployed_civilian_population"]
    total_labor = employed + unemployed
    df["unemployment_rate_pct"] = (unemployed / total_labor * 100).round(2)

    raw_path = raw_dir / "census_places.csv"
    proc_path = processed_dir / "census_places.csv"
    df.to_csv(raw_path, index=False)
    df.to_csv(proc_path, index=False)
    print(f"  ✓ saved {len(df)} place rows → {proc_path}")

    time.sleep(REQUEST_DELAY)


# ---------------------------------------------------------------------------
# 3. City-Data scraper
# ---------------------------------------------------------------------------

CITYDATA_INDEX_URL = "https://www.city-data.com/indexes/cities/"


def _scrape_citydata_page(url: str) -> list[dict]:
    """Scrape a single city-data.com index page and return rows."""
    resp = fetch(url)
    if resp is None:
        return []

    page = parse_html(resp)
    rows: list[dict] = []

    for table in page.find_all("table"):
        thead = table.find("thead")
        if thead is None:
            continue
        col_headers = [th.get_text(strip=True) for th in thead.find_all("th")]
        if not col_headers:
            continue

        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all("td")
            if not cells:
                continue
            row: dict = {}
            for i, cell in enumerate(cells):
                header = col_headers[i] if i < len(col_headers) else f"col_{i}"
                if i == 0:
                    a = cell.find("a")
                    if a and a.get("href"):
                        href = a["href"]
                        # Fix: avoid double-prepending the domain
                        if href.startswith("http"):
                            row["city_url"] = href
                        else:
                            row["city_url"] = "https://www.city-data.com" + href
                    else:
                        row["city_url"] = ""
                row[header] = cell.get_text(strip=True)
            rows.append(row)

    return rows


def scrape_citydata(raw_dir: Path, processed_dir: Path) -> None:
    """
    Scrape city-data.com index pages (A–Z) to collect composite city scores.
    """
    print("\n=== Scraping City-Data indexes ===")

    resp = fetch(CITYDATA_INDEX_URL)
    if resp is None:
        print("  ✗ Could not reach city-data index page")
        return

    page = parse_html(resp)
    all_rows: list[dict] = []

    # Discover letter-based sub-pages
    sub_links: list[str] = []
    for a in page.find_all("a", href=True):
        href = a["href"]
        if "/indexes/cities/" in href and href != CITYDATA_INDEX_URL:
            full = (
                href
                if href.startswith("http")
                else "https://www.city-data.com" + href
            )
            if full not in sub_links:
                sub_links.append(full)

    if not sub_links:
        sub_links = [CITYDATA_INDEX_URL]

    print(f"  Found {len(sub_links)} sub-pages to scrape")
    for link in sub_links:
        print(f"  → {link}")
        rows = _scrape_citydata_page(link)
        all_rows.extend(rows)
        time.sleep(REQUEST_DELAY)

    if not all_rows:
        print("  ✗ No rows collected from city-data")
        return

    df = pd.DataFrame(all_rows)
    df.columns = [
        re.sub(r"[^a-z0-9]+", "_", c.lower()).strip("_")
        for c in df.columns
    ]

    raw_path = raw_dir / "citydata_indexes.csv"
    proc_path = processed_dir / "citydata_indexes.csv"
    df.to_csv(raw_path, index=False)
    df.to_csv(proc_path, index=False)
    print(f"  ✓ saved {len(df)} city rows → {proc_path}")


# ---------------------------------------------------------------------------
# Summary / merge
# ---------------------------------------------------------------------------


def build_summary(output_dir: Path, processed_dir: Path) -> None:
    """
    Merge Numbeo indices + Census data into master_summary.csv.
    This is the primary data file consumed by the dashboard.
    """
    print("\n=== Building master summary ===")

    idx_path = processed_dir / "numbeo_indices.csv"
    cen_path = processed_dir / "census_places.csv"

    if not idx_path.exists() or not cen_path.exists():
        print("  Skipping — one or more source files are missing")
        return

    numbeo = pd.read_csv(idx_path)
    census = pd.read_csv(cen_path)

    # Normalise city names for fuzzy matching
    numbeo["city_norm"] = numbeo["city"].str.lower().str.replace("-", " ")
    census["city_norm"] = (
        census["place_name"]
        .str.lower()
        .str.replace(r"\s*(city|town|village|cdp|borough).*", "", regex=True)
        .str.strip()
    )

    merged = numbeo.merge(
        census, on="city_norm", how="left", suffixes=("", "_census")
    )

    path = output_dir / "master_summary.csv"
    merged.to_csv(path, index=False)
    print(f"  ✓ saved merged summary ({len(merged)} rows) → {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Post-Grad Lifestyle Planner — data scraper"
    )
    p.add_argument(
        "--cities",
        default=",".join(DEFAULT_CITIES),
        help="Comma-separated list of cities (default: built-in list of 15)",
    )
    p.add_argument(
        "--source",
        choices=["numbeo", "census", "citydata", "all"],
        default="all",
        help="Which data source to scrape (default: all)",
    )
    p.add_argument(
        "--output",
        default="./data",
        help="Output directory for CSV files (default: ./data)",
    )
    # parse_known_args ignores Jupyter/Colab kernel flags so this script
    # can also be run as a cell inside a notebook.
    args, _ = p.parse_known_args()
    return args


def main() -> None:
    args = parse_args()
    cities = [c.strip() for c in args.cities.split(",") if c.strip()]

    output_dir = Path(args.output)
    raw_dir = output_dir / "raw"
    processed_dir = output_dir / "processed"

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(exist_ok=True)
    processed_dir.mkdir(exist_ok=True)

    print(f"Output directory : {output_dir.resolve()}")
    print(f"Cities           : {cities}")
    print(f"Source           : {args.source}")

    if args.source in ("numbeo", "all"):
        scrape_numbeo(cities, raw_dir, processed_dir)

    if args.source in ("census", "all"):
        scrape_census(raw_dir, processed_dir)

    if args.source in ("citydata", "all"):
        scrape_citydata(raw_dir, processed_dir)

    if args.source == "all":
        build_summary(output_dir, processed_dir)

    print("\nDone ✓")


if __name__ == "__main__":
    main()
