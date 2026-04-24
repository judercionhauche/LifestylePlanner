"""
Plotly chart builders for the Lifestyle Planner dashboard.
All functions return a plotly Figure object ready to pass to st.plotly_chart().
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from .affordability import MonthlyBudget
from .config import SCORE_COLORS, CLASSIFICATION_COLORS

# ── Shared theme ─────────────────────────────────────────────────────────────

_FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"
_BG = "rgba(0,0,0,0)"       # transparent (respects Streamlit theme)
_GRID_COLOR = "#e8ecf0"

_LAYOUT_BASE = dict(
    font=dict(family=_FONT_FAMILY, size=13, color="#2d3748"),
    paper_bgcolor=_BG,
    plot_bgcolor=_BG,
    margin=dict(t=50, l=0, r=10, b=20),
    hoverlabel=dict(
        bgcolor="#1e3a5f",
        font_color="white",
        font_family=_FONT_FAMILY,
        bordercolor="transparent",
    ),
)


def _score_color(score: float) -> str:
    for label, color in SCORE_COLORS.items():
        if label == "Comfortable" and score >= 80:
            return color
        if label == "Manageable" and 60 <= score < 80:
            return color
        if label == "Tight" and 40 <= score < 60:
            return color
        if label == "Financially Risky" and score < 40:
            return color
    return "#95a5a6"


# ── 1. Affordability Ranking ──────────────────────────────────────────────────

def plot_affordability_ranking(budgets: list[MonthlyBudget]) -> go.Figure:
    """Horizontal bar chart — cities ranked by affordability score."""
    sorted_budgets = sorted(budgets, key=lambda b: b.affordability_score)
    cities = [b.display_name for b in sorted_budgets]
    scores = [b.affordability_score for b in sorted_budgets]
    colors = [_score_color(s) for s in scores]
    labels = [b.score_label for b in sorted_budgets]

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=cities,
            orientation="h",
            marker_color=colors,
            text=[f"{s:.0f}" for s in scores],
            textposition="outside",
            customdata=labels,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Score: %{x:.1f}<br>"
                "Rating: %{customdata}<extra></extra>"
            ),
        )
    )
    fig.add_vline(x=80, line_dash="dot", line_color="#27ae60", line_width=1.5,
                  annotation_text="Comfortable", annotation_position="top right",
                  annotation_font_color="#27ae60", annotation_font_size=11)
    fig.add_vline(x=60, line_dash="dot", line_color="#f39c12", line_width=1.5,
                  annotation_text="Manageable", annotation_position="top right",
                  annotation_font_color="#f39c12", annotation_font_size=11)

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="City Affordability Ranking", font_size=16, x=0),
        xaxis=dict(
            range=[0, 110],
            title="Affordability Score (0–100)",
            gridcolor=_GRID_COLOR,
            showline=False,
        ),
        yaxis=dict(showgrid=False, showline=False),
        height=max(300, len(budgets) * 38),
    )
    return fig


# ── 2. Monthly Budget Breakdown ───────────────────────────────────────────────

def plot_budget_breakdown(budget: MonthlyBudget) -> go.Figure:
    """Donut chart showing how net monthly income is allocated."""
    categories = ["Rent", "Food", "Transport", "Utilities",
                   "Student Loan", "Savings", "Misc"]
    values = [
        budget.rent, budget.food, budget.transport, budget.utilities,
        budget.student_loan, budget.savings, budget.misc,
    ]
    palette = [
        "#1e3a5f", "#2980b9", "#27ae60", "#8e44ad",
        "#e74c3c", "#f39c12", "#95a5a6",
    ]

    # If disposable > 0, show it; otherwise cap at 0
    if budget.disposable_income > 0:
        categories.append("Disposable")
        values.append(budget.disposable_income)
        palette.append("#d5e8d4")

    fig = go.Figure(
        go.Pie(
            labels=categories,
            values=values,
            hole=0.55,
            marker_colors=palette,
            textinfo="label+percent",
            textfont_size=12,
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f}/month<extra></extra>",
        )
    )

    deficit_note = (
        f"<b style='color:#e74c3c'>Deficit: ${abs(budget.disposable_income):,.0f}</b>"
        if budget.disposable_income < 0
        else f"<b>Disposable: ${budget.disposable_income:,.0f}</b>"
    )

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(
            text=f"Monthly Budget — {budget.display_name}",
            font_size=16,
            x=0,
        ),
        annotations=[
            dict(
                text=f"Net<br><b>${budget.net_monthly:,.0f}</b>",
                x=0.5, y=0.5,
                font_size=14,
                showarrow=False,
            )
        ],
        legend=dict(orientation="v", x=1.02, y=0.5),
        height=400,
    )
    return fig


# ── 3. Salary Needed by City ─────────────────────────────────────────────────

def plot_salary_needed(
    budgets: list[MonthlyBudget], current_salary: float
) -> go.Figure:
    """Bar chart showing minimum salary needed vs. user's current salary."""
    sorted_b = sorted(budgets, key=lambda b: b.min_salary_needed)
    cities = [b.display_name for b in sorted_b]
    needed = [b.min_salary_needed for b in sorted_b]
    colors = [
        "#27ae60" if n <= current_salary else "#e74c3c"
        for n in needed
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=cities,
            y=needed,
            name="Min Salary Needed",
            marker_color=colors,
            text=[f"${n / 1000:.0f}k" for n in needed],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Min Needed: $%{y:,.0f}<extra></extra>",
        )
    )
    fig.add_hline(
        y=current_salary,
        line_dash="dash",
        line_color="#1e3a5f",
        line_width=2,
        annotation_text=f"Your Salary: ${current_salary / 1000:.0f}k",
        annotation_position="top right",
        annotation_font_color="#1e3a5f",
    )

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="Minimum Salary Needed per City", font_size=16, x=0),
        xaxis=dict(title="City", showgrid=False, tickangle=-30),
        yaxis=dict(
            title="Annual Salary ($)",
            gridcolor=_GRID_COLOR,
            tickformat="$,.0f",
        ),
        showlegend=False,
        height=420,
    )
    return fig


# ── 4. Rent-to-Income Ratio ──────────────────────────────────────────────────

def plot_rent_to_income(budgets: list[MonthlyBudget]) -> go.Figure:
    """Horizontal bar chart of rent as % of net monthly income."""
    sorted_b = sorted(budgets, key=lambda b: b.rent_to_income_pct)
    cities = [b.display_name for b in sorted_b]
    pcts = [b.rent_to_income_pct for b in sorted_b]
    colors = [
        "#27ae60" if p <= 30 else ("#f39c12" if p <= 40 else "#e74c3c")
        for p in pcts
    ]

    fig = go.Figure(
        go.Bar(
            x=pcts,
            y=cities,
            orientation="h",
            marker_color=colors,
            text=[f"{p:.0f}%" for p in pcts],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Rent/Income: %{x:.1f}%<extra></extra>",
        )
    )
    fig.add_vline(
        x=30,
        line_dash="dot",
        line_color="#27ae60",
        line_width=1.5,
        annotation_text="30% guideline",
        annotation_position="top right",
        annotation_font_color="#27ae60",
        annotation_font_size=11,
    )

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="Rent-to-Net-Income Ratio", font_size=16, x=0),
        xaxis=dict(
            title="Rent as % of Net Monthly Income",
            gridcolor=_GRID_COLOR,
            ticksuffix="%",
        ),
        yaxis=dict(showgrid=False),
        height=max(300, len(budgets) * 38),
    )
    return fig


# ── 5. Disposable Income Comparison ─────────────────────────────────────────

def plot_disposable_income(budgets: list[MonthlyBudget]) -> go.Figure:
    """Bar chart of monthly disposable income after all expenses."""
    sorted_b = sorted(budgets, key=lambda b: b.disposable_income, reverse=True)
    cities = [b.display_name for b in sorted_b]
    disposable = [b.disposable_income for b in sorted_b]
    colors = [
        "#27ae60" if d >= 0 else "#e74c3c"
        for d in disposable
    ]

    fig = go.Figure(
        go.Bar(
            x=cities,
            y=disposable,
            marker_color=colors,
            text=[f"${d:,.0f}" for d in disposable],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Disposable: $%{y:,.0f}/month<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_color="#2d3748", line_width=1)

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="Monthly Disposable Income After All Expenses", font_size=16, x=0),
        xaxis=dict(title="City", showgrid=False, tickangle=-30),
        yaxis=dict(
            title="Disposable Income ($/month)",
            gridcolor=_GRID_COLOR,
            tickformat="$,.0f",
        ),
        showlegend=False,
        height=420,
    )
    return fig


# ── 6. Tax Burden Comparison ─────────────────────────────────────────────────

def plot_tax_breakdown(budgets: list[MonthlyBudget]) -> go.Figure:
    """Stacked bar: federal + FICA + state tax per city."""
    sorted_b = sorted(budgets, key=lambda b: (
        b.federal_tax_monthly + b.fica_monthly + b.state_tax_monthly
    ))
    cities = [b.display_name for b in sorted_b]
    federal = [b.federal_tax_monthly for b in sorted_b]
    fica = [b.fica_monthly for b in sorted_b]
    state = [b.state_tax_monthly for b in sorted_b]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Federal Income Tax",
        x=cities, y=federal,
        marker_color="#1e3a5f",
        hovertemplate="Federal: $%{y:,.0f}/month<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="FICA (SS + Medicare)",
        x=cities, y=fica,
        marker_color="#2980b9",
        hovertemplate="FICA: $%{y:,.0f}/month<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="State Income Tax",
        x=cities, y=state,
        marker_color="#5dade2",
        hovertemplate="State: $%{y:,.0f}/month<extra></extra>",
    ))

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="Monthly Tax Burden by City", font_size=16, x=0),
        barmode="stack",
        xaxis=dict(title="City", showgrid=False, tickangle=-30),
        yaxis=dict(
            title="Monthly Tax ($)",
            gridcolor=_GRID_COLOR,
            tickformat="$,.0f",
        ),
        legend=dict(orientation="h", y=-0.25),
        height=420,
    )
    return fig
