"""Central configuration for the Post-Graduation Lifestyle Planner."""

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

APP_TITLE = "Post-Graduation Lifestyle Planner"
APP_SUBTITLE = (
    "Compare cities, stress-test job offers, and decide where your salary "
    "actually works for the life you want."
)

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

CITY_DISPLAY_NAMES: dict[str, str] = {
    "New-York": "New York",
    "San-Francisco": "San Francisco",
    "Los-Angeles": "Los Angeles",
}


def get_display_name(city: str) -> str:
    return CITY_DISPLAY_NAMES.get(city, city.replace("-", " ").title())


CITY_REGIONS: dict[str, str] = {
    "Boston": "Northeast",
    "New-York": "Northeast",
    "San-Francisco": "West",
    "Austin": "South",
    "Seattle": "West",
    "Chicago": "Midwest",
    "Denver": "West",
    "Atlanta": "South",
    "Miami": "South",
    "Los-Angeles": "West",
    "Dallas": "South",
    "Portland": "West",
    "Nashville": "South",
    "Phoenix": "West",
    "Minneapolis": "Midwest",
}

# Approximate effective state income tax rate for the $60k–$120k income band
CITY_STATE_TAX_RATES: dict[str, float] = {
    "Boston": 0.0500,
    "New-York": 0.0685,
    "San-Francisco": 0.0930,
    "Austin": 0.0000,
    "Seattle": 0.0000,
    "Chicago": 0.0495,
    "Denver": 0.0455,
    "Atlanta": 0.0549,
    "Miami": 0.0000,
    "Los-Angeles": 0.0930,
    "Dallas": 0.0000,
    "Portland": 0.0990,
    "Nashville": 0.0000,
    "Phoenix": 0.0250,
    "Minneapolis": 0.0985,
}

# Cities with strong public-transit systems (lowers effective transit cost)
TRANSIT_FRIENDLY_CITIES: set[str] = {
    "New-York",
    "Boston",
    "Chicago",
    "San-Francisco",
    "Seattle",
    "Washington",
}

# ── Monthly cost baselines ──────────────────────────────────────────────────

LIFESTYLE_FOOD_COST: dict[str, float] = {
    "Budget": 320,
    "Moderate": 520,
    "Comfortable": 800,
}

LIFESTYLE_MISC_COST: dict[str, float] = {
    "Budget": 175,
    "Moderate": 375,
    "Comfortable": 700,
}

TRANSPORT_MONTHLY_COST: dict[str, float] = {
    "Car": 750,
    "Public Transit": 130,
    "Flexible": 340,
}

UTILITIES_MONTHLY_BASE: float = 150.0

# ── Scoring thresholds ──────────────────────────────────────────────────────

SCORE_COMFORTABLE_MIN = 80
SCORE_MANAGEABLE_MIN = 60
SCORE_TIGHT_MIN = 40

SCORE_LABEL_MAP: list[tuple[int, int, str]] = [
    (80, 100, "Comfortable"),
    (60, 80, "Manageable"),
    (40, 60, "Tight"),
    (0, 40, "Financially Risky"),
]

SCORE_COLORS: dict[str, str] = {
    "Comfortable": "#27ae60",
    "Manageable": "#f39c12",
    "Tight": "#e67e22",
    "Financially Risky": "#e74c3c",
}

CLASSIFICATION_COLORS: dict[str, str] = {
    "Strong Match": "#27ae60",
    "Possible With Adjustments": "#f39c12",
    "Financially Risky": "#e74c3c",
}
