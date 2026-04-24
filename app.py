"""
Post-Graduation Lifestyle Planner
Streamlit dashboard — entry point.

Run: streamlit run app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.config import (
    APP_SUBTITLE,
    APP_TITLE,
    DEFAULT_CITIES,
    CLASSIFICATION_COLORS,
    SCORE_COLORS,
    get_display_name,
)
from src.data_loader import filter_by_region, load_city_data
from src.affordability import (
    MonthlyBudget,
    UserProfile,
    analyze_all_cities,
    budgets_to_dataframe,
)
from src.recommendations import (
    classify_city,
    generate_adjustments,
    get_recommendation_text,
)
from src.visualizations import (
    plot_affordability_ranking,
    plot_budget_breakdown,
    plot_disposable_income,
    plot_rent_to_income,
    plot_salary_needed,
    plot_tax_breakdown,
)

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="assets/favicon.png" if Path("assets/favicon.png").exists() else "🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

_CSS_PATH = Path("assets/style.css")
if _CSS_PATH.exists():
    with open(_CSS_PATH) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_usd(n: float) -> str:
    return f"${n:,.0f}"


def _badge(label: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:white;padding:3px 10px;'
        f'border-radius:12px;font-size:0.78rem;font-weight:600;">{label}</span>'
    )


def _score_badge(score: float, label: str) -> str:
    color = SCORE_COLORS.get(label, "#95a5a6")
    return (
        f'<div style="display:inline-flex;align-items:center;gap:8px;">'
        f'<span style="font-size:1.6rem;font-weight:700;color:{color};">'
        f'{score:.0f}</span>'
        f'<span style="background:{color};color:white;padding:2px 8px;'
        f'border-radius:10px;font-size:0.75rem;font-weight:600;">{label}</span>'
        f'</div>'
    )


@st.cache_data(ttl=3600, show_spinner=False)
def _load_data():
    return load_city_data()


# ── Landing header ────────────────────────────────────────────────────────────

def render_header():
    st.markdown(
        f"""
        <div class="planner-header">
            <h1>{APP_TITLE}</h1>
            <p class="subtitle">{APP_SUBTITLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Sidebar inputs ────────────────────────────────────────────────────────────

def render_sidebar() -> UserProfile | None:
    st.sidebar.markdown(
        '<div class="sidebar-section-title">Your Profile</div>',
        unsafe_allow_html=True,
    )

    salary = st.sidebar.number_input(
        "Expected Annual Salary ($)",
        min_value=25_000,
        max_value=500_000,
        value=75_000,
        step=1_000,
        format="%d",
        help="Your gross annual salary from your job offer.",
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<div class="sidebar-section-title">Monthly Commitments</div>',
        unsafe_allow_html=True,
    )

    savings_goal = st.sidebar.slider(
        "Monthly Savings Goal ($)",
        min_value=0,
        max_value=3_000,
        value=500,
        step=50,
        help="How much you want to save each month for emergency fund, retirement, or goals.",
    )

    student_loan = st.sidebar.slider(
        "Monthly Student Loan Payment ($)",
        min_value=0,
        max_value=2_000,
        value=300,
        step=25,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<div class="sidebar-section-title">Lifestyle Preferences</div>',
        unsafe_allow_html=True,
    )

    lifestyle = st.sidebar.select_slider(
        "Lifestyle Level",
        options=["Budget", "Moderate", "Comfortable"],
        value="Moderate",
        help=(
            "Budget: cook at home, minimal extras. "
            "Moderate: mix of eating out, occasional travel. "
            "Comfortable: dining out regularly, experiences, hobbies."
        ),
    )

    housing = st.sidebar.radio(
        "Housing Preference",
        options=["Alone", "Roommates", "Flexible"],
        index=2,
        horizontal=True,
        help=(
            "Alone: private 1BR. Roommates: shared apartment (split rent). "
            "Flexible: weighted average."
        ),
    )

    transport = st.sidebar.radio(
        "Transportation",
        options=["Public Transit", "Car", "Flexible"],
        index=0,
        horizontal=True,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<div class="sidebar-section-title">City Filters</div>',
        unsafe_allow_html=True,
    )

    region_filter = st.sidebar.selectbox(
        "Preferred Region",
        options=["Any", "Northeast", "South", "Midwest", "West"],
        index=0,
    )

    city_options = [get_display_name(c) for c in DEFAULT_CITIES]
    city_map = {get_display_name(c): c for c in DEFAULT_CITIES}

    selected_display = st.sidebar.multiselect(
        "Cities to Compare",
        options=city_options,
        default=city_options,
        help="Select which cities to include in the analysis.",
    )

    if not selected_display:
        st.sidebar.warning("Select at least one city.")
        return None

    selected_cities = [city_map[d] for d in selected_display]

    st.sidebar.markdown("---")
    run = st.sidebar.button(
        "Calculate Affordability",
        type="primary",
        use_container_width=True,
    )

    if not run and "last_profile" not in st.session_state:
        st.sidebar.caption("Adjust inputs above and click Calculate.")
        return None

    profile = UserProfile(
        annual_salary=float(salary),
        monthly_savings_goal=float(savings_goal),
        monthly_student_loan=float(student_loan),
        lifestyle=lifestyle,
        housing_preference=housing,
        transport_preference=transport,
    )

    # Store in session so results persist without re-clicking
    if run:
        st.session_state["last_profile"] = profile
        st.session_state["last_cities"] = selected_cities
        st.session_state["last_region"] = region_filter

    return profile, selected_cities, region_filter


# ── Top match cards ───────────────────────────────────────────────────────────

def render_top_cards(budgets: list[MonthlyBudget]):
    top3 = [b for b in budgets if b.affordability_score >= 60][:3]
    if not top3:
        top3 = budgets[:3]

    st.markdown("### Top Matches for Your Profile")
    cols = st.columns(len(top3))

    for col, b in zip(cols, top3):
        classification = classify_city(b)
        c_color = CLASSIFICATION_COLORS.get(classification, "#95a5a6")
        with col:
            st.markdown(
                f"""
                <div class="city-card">
                    <div class="card-city-name">{b.display_name}</div>
                    {_badge(classification, c_color)}
                    <div class="card-score">{_score_badge(b.affordability_score, b.score_label)}</div>
                    <div class="card-stats">
                        <div><span class="stat-label">Net Monthly</span>
                             <span class="stat-value">{_fmt_usd(b.net_monthly)}</span></div>
                        <div><span class="stat-label">Est. Rent</span>
                             <span class="stat-value">{_fmt_usd(b.rent)}</span></div>
                        <div><span class="stat-label">Disposable</span>
                             <span class="stat-value" style="color:{'#27ae60' if b.disposable_income >= 0 else '#e74c3c'};">
                             {_fmt_usd(b.disposable_income)}</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ── Budget detail panel ───────────────────────────────────────────────────────

def render_budget_detail(budgets: list[MonthlyBudget]):
    st.markdown("---")
    st.markdown("### Detailed Budget Breakdown")

    display_names = [b.display_name for b in budgets]
    selected = st.selectbox("Select a city to explore:", display_names, index=0)
    budget = next(b for b in budgets if b.display_name == selected)

    left, right = st.columns([1, 1])

    with left:
        st.plotly_chart(
            plot_budget_breakdown(budget),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    with right:
        st.markdown(f"#### Budget Summary — {budget.display_name}")
        rows = {
            "Gross Monthly": budget.gross_monthly,
            "Federal Tax": -budget.federal_tax_monthly,
            "FICA": -budget.fica_monthly,
            "State Tax": -budget.state_tax_monthly,
            "**Net Monthly**": budget.net_monthly,
            "Rent": -budget.rent,
            "Food": -budget.food,
            "Transport": -budget.transport,
            "Utilities": -budget.utilities,
            "Student Loan": -budget.student_loan,
            "Savings Goal": -budget.savings,
            "Misc / Discretionary": -budget.misc,
            "**Disposable Income**": budget.disposable_income,
        }

        for label, value in rows.items():
            is_total = label.startswith("**")
            clean_label = label.replace("**", "")
            val_str = _fmt_usd(abs(value))
            sign = "+" if value >= 0 else "−"
            color = "#2d3748"
            if is_total and "Net" in clean_label:
                color = "#1e3a5f"
            if is_total and "Disposable" in clean_label:
                color = "#27ae60" if value >= 0 else "#e74c3c"
            weight = "700" if is_total else "400"
            border = "border-top:2px solid #e2e8f0;" if is_total else ""
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:4px 0;{border}font-weight:{weight};">'
                f'<span>{clean_label}</span>'
                f'<span style="color:{color};">{sign}{val_str}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        classification = classify_city(budget)
        adjustments = generate_adjustments(budget, st.session_state["last_profile"])
        st.markdown(f"**Suggestions for {budget.display_name}**")
        for tip in adjustments:
            st.markdown(f"- {tip}")


# ── All cities table ──────────────────────────────────────────────────────────

def render_city_table(budgets: list[MonthlyBudget]):
    st.markdown("---")
    st.markdown("### All Cities at a Glance")

    df = budgets_to_dataframe(budgets)
    display_df = df[[
        "City", "Score", "Rating", "Net Monthly", "Rent",
        "Food", "Transport", "Disposable", "Rent/Income %", "Min Salary Needed",
    ]].copy()

    for col in ["Net Monthly", "Rent", "Food", "Transport", "Disposable", "Min Salary Needed"]:
        display_df[col] = display_df[col].map(lambda x: _fmt_usd(x))

    display_df["Rent/Income %"] = display_df["Rent/Income %"].map(lambda x: f"{x:.1f}%")
    display_df["Score"] = display_df["Score"].map(lambda x: f"{x:.1f}")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=min(600, (len(display_df) + 1) * 40),
    )


# ── Charts section ────────────────────────────────────────────────────────────

def render_charts(budgets: list[MonthlyBudget], profile: UserProfile):
    st.markdown("---")
    st.markdown("### Interactive Comparisons")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Affordability Ranking",
        "Salary Needed",
        "Rent-to-Income",
        "Disposable Income",
        "Tax Burden",
    ])

    with tab1:
        st.plotly_chart(
            plot_affordability_ranking(budgets),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    with tab2:
        st.plotly_chart(
            plot_salary_needed(budgets, profile.annual_salary),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    with tab3:
        st.plotly_chart(
            plot_rent_to_income(budgets),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    with tab4:
        st.plotly_chart(
            plot_disposable_income(budgets),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    with tab5:
        st.plotly_chart(
            plot_tax_breakdown(budgets),
            use_container_width=True,
            config={"displayModeBar": False},
        )


# ── AI Recommendations section ────────────────────────────────────────────────

def render_recommendations(budgets: list[MonthlyBudget], profile: UserProfile):
    st.markdown("---")
    st.markdown("### Recommendation Summary")

    text, is_ai = get_recommendation_text(budgets, profile)
    source_label = "AI-Powered" if is_ai else "Rule-Based"
    source_color = "#1e3a5f" if is_ai else "#718096"

    st.markdown(
        f'<span style="background:{source_color};color:white;padding:2px 8px;'
        f'border-radius:10px;font-size:0.72rem;font-weight:600;">{source_label}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="recommendation-box">{text}</div>',
        unsafe_allow_html=True,
    )

    if not is_ai:
        st.caption(
            "Add an OPENAI_API_KEY to your .env file to unlock AI-powered explanations."
        )


# ── Data source banner ────────────────────────────────────────────────────────

def render_data_banner(source: str):
    if source == "scraped":
        st.success(
            "Using freshly scraped data from Numbeo and US Census Bureau.",
            icon="✓",
        )
    else:
        st.info(
            "Using built-in estimates (2023–2024 public data). "
            "Run `python scraper.py` to fetch live data.",
            icon="ℹ",
        )


# ── Main app ──────────────────────────────────────────────────────────────────

def main():
    render_header()

    result = render_sidebar()

    # Load city data once (cached)
    all_city_df, data_source = _load_data()

    # Show placeholder state before user clicks Calculate
    if result is None or not isinstance(result, tuple):
        st.markdown(
            """
            <div class="welcome-panel">
                <h3>How it works</h3>
                <ol>
                    <li>Enter your expected salary and monthly commitments in the sidebar.</li>
                    <li>Choose your lifestyle level and housing / transport preferences.</li>
                    <li>Select the cities you are considering.</li>
                    <li>Click <strong>Calculate Affordability</strong> to see your personalized results.</li>
                </ol>
                <p>The tool estimates your net income after taxes, then compares it against
                real cost-of-living data for each city to produce a 0–100 affordability score.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_data_banner(data_source)
        return

    profile, selected_cities, region_filter = result
    # Persist for adjustment suggestions
    st.session_state["last_profile"] = profile

    # Filter dataframe to selected cities and region
    city_df = all_city_df[all_city_df["city"].isin(selected_cities)].copy()
    if region_filter != "Any":
        city_df = filter_by_region(city_df, region_filter)

    if city_df.empty:
        st.warning("No cities match your current filters. Adjust the region or city selection.")
        return

    render_data_banner(data_source)

    # Run affordability calculations
    with st.spinner("Calculating affordability for selected cities..."):
        budgets = analyze_all_cities(city_df, profile)

    if not budgets:
        st.error("Could not calculate budgets. Please check your inputs.")
        return

    # Render dashboard sections
    render_top_cards(budgets)
    render_budget_detail(budgets)
    render_city_table(budgets)
    render_charts(budgets, profile)
    render_recommendations(budgets, profile)

    # Footer
    st.markdown("---")
    st.caption(
        "Data sources: Numbeo Cost of Living, US Census Bureau ACS 5-Year Estimates. "
        "Estimates are for planning purposes only. Consult a financial advisor for personalised advice."
    )


if __name__ == "__main__":
    main()
