"""
Recommendation engine.

Classifies cities and generates actionable, plain-language advice.
Optionally uses OpenAI for richer explanations; falls back to rule-based text.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .affordability import MonthlyBudget, UserProfile
from .config import (
    SCORE_COMFORTABLE_MIN,
    SCORE_MANAGEABLE_MIN,
    SCORE_TIGHT_MIN,
)

if TYPE_CHECKING:
    pass


# ── Classification ────────────────────────────────────────────────────────────

def classify_city(budget: MonthlyBudget) -> str:
    if budget.affordability_score >= SCORE_MANAGEABLE_MIN:
        return "Strong Match"
    if budget.affordability_score >= SCORE_TIGHT_MIN:
        return "Possible With Adjustments"
    return "Financially Risky"


# ── Rule-based adjustment suggestions ────────────────────────────────────────

def _fmt(n: float) -> str:
    return f"${n:,.0f}"


def generate_adjustments(
    budget: MonthlyBudget, profile: UserProfile
) -> list[str]:
    """Return a short list of actionable suggestions for a given city budget."""
    suggestions: list[str] = []

    # Rent-to-income above 30% threshold (standard financial guideline)
    if budget.rent_to_income_pct > 40:
        if profile.housing_preference == "Alone":
            suggestions.append(
                f"Rent consumes {budget.rent_to_income_pct:.0f}% of net income. "
                "Consider finding a roommate — this alone could free up "
                f"{_fmt(budget.rent * 0.40)}/month."
            )
        else:
            suggestions.append(
                f"Rent is {budget.rent_to_income_pct:.0f}% of net income even with roommates. "
                "Look for neighborhoods just outside the city core."
            )
    elif budget.rent_to_income_pct > 30:
        suggestions.append(
            f"Rent is {budget.rent_to_income_pct:.0f}% of net income — slightly above the "
            "30% guideline. Manageable, but leave room for an emergency fund."
        )

    # Salary gap
    if budget.min_salary_needed > profile.annual_salary:
        gap = budget.min_salary_needed - profile.annual_salary
        suggestions.append(
            f"A salary of {_fmt(budget.min_salary_needed)}/year "
            f"({_fmt(gap)} more than your current offer) would move this city "
            "into the manageable range."
        )

    # Transport
    if profile.transport_preference == "Car" and budget.transport > 650:
        suggestions.append(
            "If this city has reasonable public transit, switching to transit "
            f"could save ~{_fmt(budget.transport - 130)}/month."
        )

    # Savings flexibility
    if budget.disposable_income < 0 and profile.monthly_savings_goal > 200:
        relief = min(profile.monthly_savings_goal - 200, abs(budget.disposable_income))
        suggestions.append(
            f"Temporarily reducing your savings goal by {_fmt(relief)}/month "
            "could make this city work short-term while you grow your income."
        )

    # Lifestyle downgrade
    if budget.disposable_income < 0 and profile.lifestyle == "Comfortable":
        suggestions.append(
            "Dropping to a 'Moderate' lifestyle budget would reduce food and "
            "discretionary costs by roughly "
            f"{_fmt(280 + 325)}/month."
        )

    # Nearby city suggestion (static fallback)
    fallback_neighbors: dict[str, list[str]] = {
        "San-Francisco": ["Oakland", "San Jose", "Berkeley"],
        "New-York": ["Jersey City", "Newark", "Hoboken"],
        "Los-Angeles": ["Long Beach", "Pasadena", "Burbank"],
        "Boston": ["Cambridge", "Somerville", "Quincy"],
        "Seattle": ["Bellevue", "Tacoma", "Redmond"],
        "Miami": ["Fort Lauderdale", "Boca Raton"],
    }
    neighbors = fallback_neighbors.get(budget.city, [])
    if budget.affordability_score < SCORE_TIGHT_MIN and neighbors:
        suggestions.append(
            f"Consider nearby cities like {', '.join(neighbors[:2])} which may "
            "offer lower housing costs while keeping you in the same metro area."
        )

    if not suggestions:
        suggestions.append(
            "Your salary covers all estimated expenses with room to spare. "
            "Focus on building your emergency fund and long-term savings."
        )

    return suggestions


# ── Rule-based summary narrative ─────────────────────────────────────────────

def generate_rule_based_summary(
    budgets: list[MonthlyBudget], profile: UserProfile
) -> str:
    """Generate a plain-text overall summary without calling any external API."""
    top = [b for b in budgets if b.affordability_score >= SCORE_MANAGEABLE_MIN]
    risky = [b for b in budgets if b.affordability_score < SCORE_TIGHT_MIN]
    tight = [
        b for b in budgets
        if SCORE_TIGHT_MIN <= b.affordability_score < SCORE_MANAGEABLE_MIN
    ]

    salary_str = f"${profile.annual_salary:,.0f}"
    savings_str = f"${profile.monthly_savings_goal:,.0f}/month"

    parts: list[str] = [
        f"Based on a salary of {salary_str} with a savings goal of {savings_str} "
        f"({profile.lifestyle.lower()} lifestyle, {profile.housing_preference.lower()} housing):"
    ]

    if top:
        names = ", ".join(b.display_name for b in top[:4])
        parts.append(
            f"{names} {'is' if len(top) == 1 else 'are'} your strongest "
            f"{'match' if len(top) == 1 else 'matches'}, leaving meaningful "
            "disposable income after all expenses."
        )

    if tight:
        names = ", ".join(b.display_name for b in tight[:3])
        parts.append(
            f"{names} {'is' if len(tight) == 1 else 'are'} workable with adjustments — "
            "consider roommates, reduced discretionary spending, or a small salary negotiation."
        )

    if risky:
        names = ", ".join(b.display_name for b in risky[:3])
        parts.append(
            f"{names} {'looks' if len(risky) == 1 else 'look'} financially risky at this "
            "salary because housing costs consume too large a share of net income."
        )

    if not top and not tight:
        parts.append(
            "None of the selected cities appear comfortably affordable at this salary. "
            "Consider negotiating a higher offer or revisiting your savings and lifestyle targets."
        )

    return " ".join(parts)


# ── OpenAI-powered explanation ────────────────────────────────────────────────

def generate_ai_explanation(
    budgets: list[MonthlyBudget], profile: UserProfile
) -> str | None:
    """
    Call OpenAI to produce a richer narrative. Returns None if no API key is set
    or if the call fails, so the caller can fall back gracefully.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=api_key)

        top3 = budgets[:3]
        bottom3 = sorted(budgets, key=lambda b: b.affordability_score)[:3]

        data_summary = "\n".join(
            f"- {b.display_name}: score={b.affordability_score}, "
            f"net_monthly=${b.net_monthly:,.0f}, rent=${b.rent:,.0f}, "
            f"disposable=${b.disposable_income:,.0f}, label={b.score_label}"
            for b in top3 + bottom3
        )

        prompt = f"""
You are a career-services advisor helping a recent college graduate choose where to live.
Do NOT invent numbers. Use only the data below.

User profile:
- Annual salary: ${profile.annual_salary:,.0f}
- Monthly savings goal: ${profile.monthly_savings_goal:,.0f}
- Monthly student loan: ${profile.monthly_student_loan:,.0f}
- Lifestyle: {profile.lifestyle}
- Housing preference: {profile.housing_preference}
- Transport preference: {profile.transport_preference}

Affordability results (top 3 and bottom 3 cities):
{data_summary}

Write 3–4 sentences: explain which cities work and why, which don't and why,
and give one concrete action the student can take. Be direct and encouraging.
        """.strip()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()

    except Exception:
        return None


def get_recommendation_text(
    budgets: list[MonthlyBudget], profile: UserProfile
) -> tuple[str, bool]:
    """
    Returns (recommendation_text, is_ai_generated).
    Tries OpenAI first; falls back to rule-based summary.
    """
    ai_text = generate_ai_explanation(budgets, profile)
    if ai_text:
        return ai_text, True
    return generate_rule_based_summary(budgets, profile), False
