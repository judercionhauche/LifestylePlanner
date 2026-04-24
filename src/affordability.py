"""
Affordability calculation engine.

Produces a monthly budget breakdown and a 0–100 affordability score for each
city based on user inputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from .config import (
    LIFESTYLE_FOOD_COST,
    LIFESTYLE_MISC_COST,
    TRANSPORT_MONTHLY_COST,
    UTILITIES_MONTHLY_BASE,
    TRANSIT_FRIENDLY_CITIES,
    SCORE_LABEL_MAP,
)

# ── 2024 Federal income tax brackets (single filer) ─────────────────────────
_STANDARD_DEDUCTION = 14_600.0
_FEDERAL_BRACKETS = [
    (11_600, 0.10),
    (35_550, 0.12),   # 47_150 - 11_600
    (53_375, 0.22),   # 100_525 - 47_150
    (91_425, 0.24),   # 191_950 - 100_525
    (51_775, 0.32),   # 243_725 - 191_950
    (365_625, 0.35),  # 609_350 - 243_725
    (math.inf, 0.37),
]

# Social Security wage base 2024
_SS_WAGE_BASE = 168_600.0


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class UserProfile:
    annual_salary: float
    monthly_savings_goal: float
    monthly_student_loan: float
    lifestyle: str          # "Budget" | "Moderate" | "Comfortable"
    housing_preference: str # "Alone" | "Roommates" | "Flexible"
    transport_preference: str  # "Car" | "Public Transit" | "Flexible"


@dataclass
class MonthlyBudget:
    city: str
    display_name: str

    gross_monthly: float = 0.0
    federal_tax_monthly: float = 0.0
    state_tax_monthly: float = 0.0
    fica_monthly: float = 0.0
    net_monthly: float = 0.0

    rent: float = 0.0
    food: float = 0.0
    transport: float = 0.0
    utilities: float = 0.0
    student_loan: float = 0.0
    savings: float = 0.0
    misc: float = 0.0

    total_expenses: float = 0.0
    disposable_income: float = 0.0
    affordability_score: float = 0.0
    score_label: str = ""

    rent_to_income_pct: float = 0.0
    min_salary_needed: float = 0.0


# ── Tax helpers ──────────────────────────────────────────────────────────────

def _federal_income_tax(annual_gross: float) -> float:
    """Progressive 2024 federal income tax for a single filer."""
    taxable = max(0.0, annual_gross - _STANDARD_DEDUCTION)
    tax = 0.0
    for bracket_size, rate in _FEDERAL_BRACKETS:
        if taxable <= 0:
            break
        chunk = min(taxable, bracket_size)
        tax += chunk * rate
        taxable -= chunk
    return tax


def _fica_tax(annual_gross: float) -> float:
    """Social Security (6.2%) + Medicare (1.45% + 0.9% over $200k)."""
    ss = min(annual_gross, _SS_WAGE_BASE) * 0.062
    medicare = annual_gross * 0.0145
    if annual_gross > 200_000:
        medicare += (annual_gross - 200_000) * 0.009
    return ss + medicare


def _state_income_tax(annual_gross: float, rate: float) -> float:
    return annual_gross * rate


# ── Rent estimation ──────────────────────────────────────────────────────────

def _estimate_rent(
    median_gross_rent: float,
    housing_preference: str,
    col_index: float | None = None,
) -> float:
    """
    Estimate monthly rent from Census median rent, adjusted for housing choice.

    Census median_gross_rent represents a typical unit. We scale it:
    - Alone:     full unit (1BR in city centre ≈ 1.15× Census median)
    - Roommates: split 2BR by 2 (≈ 0.65× Census median)
    - Flexible:  average of above
    """
    base = float(median_gross_rent) if median_gross_rent and not pd.isna(median_gross_rent) else 1_600.0
    multipliers = {"Alone": 1.15, "Roommates": 0.65, "Flexible": 0.90}
    return base * multipliers.get(housing_preference, 0.90)


# ── Food/misc cost scaling ───────────────────────────────────────────────────

def _scale_by_col(base_cost: float, col_index: float | None) -> float:
    """Scale a baseline monthly cost by Numbeo CoL index (NYC = 100)."""
    if col_index is None or pd.isna(col_index) or col_index <= 0:
        return base_cost
    return base_cost * (col_index / 73.0)  # 73 ≈ average across our city list


def _transport_cost(city: str, preference: str, col_index: float | None) -> float:
    base = TRANSPORT_MONTHLY_COST.get(preference, 340.0)
    if preference == "Public Transit" and city in TRANSIT_FRIENDLY_CITIES:
        base *= 0.85  # slight discount for cities with better transit coverage
    elif preference == "Car":
        if col_index and not pd.isna(col_index):
            gas_scale = 1.0 + (col_index - 73) / 250
            base = base * max(0.8, min(1.3, gas_scale))
    return base


# ── Affordability score ──────────────────────────────────────────────────────

def _score(remaining: float, net_monthly: float) -> float:
    """Map remaining disposable income ratio to a 0–100 score."""
    if net_monthly <= 0:
        return 0.0
    ratio = remaining / net_monthly
    if remaining < 0:
        deficit = abs(remaining) / net_monthly
        return max(0.0, 20.0 - deficit * 25.0)
    if ratio >= 0.30:
        return min(100.0, 80.0 + (ratio - 0.30) * 67.0)
    if ratio >= 0.15:
        return 60.0 + (ratio - 0.15) / 0.15 * 20.0
    if ratio >= 0.05:
        return 40.0 + (ratio - 0.05) / 0.10 * 20.0
    return 20.0 + ratio / 0.05 * 20.0


def _score_label(score: float) -> str:
    for lo, hi, label in SCORE_LABEL_MAP:
        if lo <= score <= hi:
            return label
    return "Financially Risky"


# ── Minimum salary estimator ─────────────────────────────────────────────────

def _minimum_salary_for_manageable(
    city_row: pd.Series, profile: UserProfile
) -> float:
    """
    Binary-search the annual salary at which affordability_score >= 60.
    Returns the salary rounded up to the nearest $1,000.
    """
    lo, hi = 20_000.0, 500_000.0
    for _ in range(40):
        mid = (lo + hi) / 2
        test_profile = UserProfile(
            annual_salary=mid,
            monthly_savings_goal=profile.monthly_savings_goal,
            monthly_student_loan=profile.monthly_student_loan,
            lifestyle=profile.lifestyle,
            housing_preference=profile.housing_preference,
            transport_preference=profile.transport_preference,
        )
        budget = calculate_city_budget(city_row, test_profile)
        if budget.affordability_score >= 60:
            hi = mid
        else:
            lo = mid
    return math.ceil(hi / 1_000) * 1_000


# ── Main calculation ─────────────────────────────────────────────────────────

def calculate_city_budget(
    city_row: pd.Series, profile: UserProfile
) -> MonthlyBudget:
    """Produce a complete MonthlyBudget for a single city and user profile."""
    city = str(city_row.get("city", "Unknown"))
    display_name = str(city_row.get("display_name", city))
    col_index = city_row.get("cost_of_living_index")
    state_rate = float(city_row.get("state_tax_rate", 0.05))

    gross = profile.annual_salary
    gross_monthly = gross / 12.0

    federal_tax = _federal_income_tax(gross)
    fica = _fica_tax(gross)
    state_tax = _state_income_tax(gross, state_rate)
    total_tax = federal_tax + fica + state_tax
    net_annual = gross - total_tax
    net_monthly = net_annual / 12.0

    rent = _estimate_rent(
        city_row.get("median_gross_rent"), profile.housing_preference, col_index
    )
    food = _scale_by_col(LIFESTYLE_FOOD_COST[profile.lifestyle], col_index)
    transport = _transport_cost(city, profile.transport_preference, col_index)
    utilities = UTILITIES_MONTHLY_BASE
    misc = _scale_by_col(LIFESTYLE_MISC_COST[profile.lifestyle], col_index)
    student_loan = profile.monthly_student_loan
    savings = profile.monthly_savings_goal

    total_expenses = rent + food + transport + utilities + misc + student_loan + savings
    disposable = net_monthly - total_expenses
    score = round(_score(disposable, net_monthly), 1)

    budget = MonthlyBudget(
        city=city,
        display_name=display_name,
        gross_monthly=round(gross_monthly, 2),
        federal_tax_monthly=round(federal_tax / 12, 2),
        state_tax_monthly=round(state_tax / 12, 2),
        fica_monthly=round(fica / 12, 2),
        net_monthly=round(net_monthly, 2),
        rent=round(rent, 2),
        food=round(food, 2),
        transport=round(transport, 2),
        utilities=utilities,
        student_loan=round(student_loan, 2),
        savings=round(savings, 2),
        misc=round(misc, 2),
        total_expenses=round(total_expenses, 2),
        disposable_income=round(disposable, 2),
        affordability_score=score,
        score_label=_score_label(score),
        rent_to_income_pct=round(rent / net_monthly * 100, 1) if net_monthly > 0 else 0,
    )
    return budget


def analyze_all_cities(
    df: pd.DataFrame, profile: UserProfile
) -> list[MonthlyBudget]:
    """Compute budgets for every city in the DataFrame."""
    budgets = []
    for _, row in df.iterrows():
        b = calculate_city_budget(row, profile)
        b.min_salary_needed = _minimum_salary_for_manageable(row, profile)
        budgets.append(b)
    return sorted(budgets, key=lambda b: b.affordability_score, reverse=True)


def budgets_to_dataframe(budgets: list[MonthlyBudget]) -> pd.DataFrame:
    """Convert a list of MonthlyBudget objects to a display-ready DataFrame."""
    rows = []
    for b in budgets:
        rows.append(
            {
                "City": b.display_name,
                "city_key": b.city,
                "Score": b.affordability_score,
                "Rating": b.score_label,
                "Net Monthly": b.net_monthly,
                "Rent": b.rent,
                "Food": b.food,
                "Transport": b.transport,
                "Utilities": b.utilities,
                "Student Loan": b.student_loan,
                "Savings": b.savings,
                "Misc": b.misc,
                "Total Expenses": b.total_expenses,
                "Disposable": b.disposable_income,
                "Rent/Income %": b.rent_to_income_pct,
                "Min Salary Needed": b.min_salary_needed,
            }
        )
    return pd.DataFrame(rows)
