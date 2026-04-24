# Post-Graduation Lifestyle Planner

An interactive dashboard that helps graduating students evaluate whether a job offer's salary is actually livable in a target city — after taxes, rent, food, transportation, student loans, and savings goals.

---

## Business Problem

A $75,000 offer in San Francisco feels very different from a $75,000 offer in Nashville. This tool bridges that gap: it estimates true take-home pay, models city-specific expenses, and produces a clear affordability score (0–100) for every city under consideration.

---

## Features

| Feature | Description |
|---|---|
| Affordability Engine | Net salary → taxes → real expense breakdown → 0–100 score |
| City Ranking | Visual ranking of all selected cities |
| Budget Breakdown | Per-city donut chart + waterfall budget table |
| Salary Gap Analysis | Minimum salary needed to be financially comfortable |
| Rent-to-Income Ratio | Flags cities where housing exceeds the 30% guideline |
| Tax Breakdown | Federal + FICA + state tax comparison by city |
| AI Recommendations | OpenAI-powered (or rule-based) plain-English summary |
| Fallback Data | Embedded 2023–2024 estimates so the app works offline |

---

## Data Sources

- **[Numbeo](https://www.numbeo.com/cost-of-living/)** — cost-of-living indices and itemised prices per city
- **[US Census Bureau ACS 5-Year](https://api.census.gov/data/2022/acs/acs5)** — population, median rent, income, unemployment (no API key required)
- **[City-Data.com](https://www.city-data.com/indexes/cities/)** — composite city index scores

---

## Tech Stack

- **Python 3.11+**
- **Streamlit** — dashboard framework
- **Plotly** — interactive charts
- **Pandas** — data processing
- **BeautifulSoup + lxml** — web scraping
- **OpenAI API** — optional AI recommendation layer

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/judercionhauche/LifestylePlanner.git
cd LifestylePlanner

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Configure environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY if you want AI explanations
```

---

## Running the Dashboard

```bash
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`. It uses built-in city estimates by default — no scraping required to run.

---

## Fetching Live Data

Run the scraper to pull fresh data from Numbeo and the Census API:

```bash
# Scrape all sources (default 15 cities)
python scraper.py

# Custom city list
python scraper.py --cities "Boston,Austin,Seattle,Denver"

# Single source
python scraper.py --source numbeo
python scraper.py --source census

# Custom output directory
python scraper.py --output ./data
```

Scraped data is saved to:
- `data/raw/` — original files as fetched
- `data/processed/` — cleaned files
- `data/master_summary.csv` — merged file used by the dashboard

Once `master_summary.csv` exists, the dashboard loads it automatically.

---

## Project Structure

```
LifestylePlanner/
├── app.py                  Main Streamlit application
├── scraper.py              Data scraper (Numbeo, Census, City-Data)
├── requirements.txt        Python dependencies
├── .env.example            Environment variable template
│
├── src/
│   ├── config.py           Constants, city metadata, cost baselines
│   ├── data_loader.py      CSV loading with embedded fallback data
│   ├── affordability.py    Tax calculations, budget engine, scoring
│   ├── recommendations.py  Classification, adjustments, AI/rule-based summaries
│   └── visualizations.py  Plotly chart builders
│
├── data/
│   ├── raw/                Raw scraped files
│   ├── processed/          Cleaned files
│   └── master_summary.csv  Dashboard data file
│
└── assets/
    └── style.css           Custom CSS
```

---

## Affordability Score Methodology

```
Score 80–100  →  Comfortable      (>30% of net income remains after all expenses)
Score 60–79   →  Manageable       (15–30% remains)
Score 40–59   →  Tight            (5–15% remains)
Score  0–39   →  Financially Risky (<5% or deficit)
```

**Tax estimation** uses 2024 federal progressive brackets + FICA (Social Security 6.2%, Medicare 1.45%) + an approximate state flat rate for each city.

**Rent estimation** uses Census median gross rent as the baseline, then applies a multiplier based on housing preference (alone ×1.15, roommates ×0.65).

**Food and misc** costs scale with each city's Numbeo cost-of-living index.

---

## Deployment

### Streamlit Cloud (recommended)

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → New App → connect your repo.
3. Set `OPENAI_API_KEY` in the Streamlit Cloud secrets panel.

### Cloudflare Pages (static landing page)

For a static marketing landing page, place an `index.html` in a `landing/` folder and deploy it to Cloudflare Pages. The Streamlit app itself runs on Streamlit Cloud and can be embedded via an iframe.

---

## Limitations

- Numbeo data reflects user-contributed prices and may lag real-time conditions.
- Census ACS data is from 2022; rent and income figures may understate 2024 values in fast-growing markets.
- Tax estimates are simplified — does not account for itemized deductions, 401(k) contributions, or city/local taxes (e.g., NYC has an additional city tax).
- City-Data scraping is subject to site structure changes.

---

## Future Improvements

- [ ] Add local/city income tax for NYC, Philadelphia, Detroit
- [ ] Pre-tax 401(k) deduction input
- [ ] Salary negotiation simulator ("what if I counter at $X?")
- [ ] Time-series view of rent trends per city
- [ ] Exportable PDF report
- [ ] Additional cities (international comparison mode)

---

## Contributors

Group 3 — Olivia Xie, Soukeyna Pitroipa, Carina Domat

Dashboard architecture and refactor: Claude Code
