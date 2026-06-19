import json
import base64
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------
# Page setup
# --------------------------------
st.set_page_config(
    page_title="TransitIQ Dashboard",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------
# Paths
# --------------------------------
BASE_DIR = Path(__file__).parent
RESULTS_PATH = BASE_DIR / "data" / "outputs" / "processing_layer_results.csv"
TRACTS_PATH = BASE_DIR / "data" / "geospatial" / "franklin_tracts.geojson"
STOPS_PATH = BASE_DIR / "data" / "geospatial" / "cota_stops.geojson"
HERO_BG_PATH = BASE_DIR / "assets" / "hero_bg.png"

# Color palette
# https://coolors.co/palette/d3996b-a57662-94837c-274142-001018
# --------------------------------
SAND = "#D3996B"
CLAY = "#A57662"
TAUPE = "#94837C"
FOREST = "#274142"
INK = "#001018"
WHITE = "#FFFFFF"

MAP_SCALE = [
    [0.00, INK],
    [0.35, FOREST],
    [0.70, CLAY],
    [1.00, SAND],
]

PLOTLY_FONT = "Inter, Segoe UI, Arial, sans-serif"


# --------------------------------

# --------------------------------
# Helper functions
# --------------------------------
def money(value):
    """Format large numbers as readable dollars."""
    if pd.isna(value):
        return "$0"

    value = float(value)

    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.1f}K"

    return f"${value:,.0f}"


def image_to_base64(image_path):
    """Convert a local image to base64 so CSS can use it."""
    if not image_path.exists():
        return None

    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def build_policy_brief(
    delay_years,
    investment_amount,
    delay_cost,
    annual_cost,
    population,
    tract_count,
    avg_hardship,
    delay_cost_per_invested_dollar,
    top_tracts_df,
):
    """Create a downloadable Markdown policy brief."""

    generated_at = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    top_tract_lines = []

    for _, row in top_tracts_df.head(5).iterrows():
        tract = row.get("Tract GEOID", row.get("GEOID", "Unknown"))
        hardship = row.get("Hardship Index", row.get("transit_hardship_index", "N/A"))
        delay_value = row.get(
            f"{delay_years}-Year Delay Cost",
            row.get(f"cumulative_delay_{delay_years}yr_cost", "N/A"),
        )

        top_tract_lines.append(
            f"- Tract {tract}: hardship index {hardship}, estimated {delay_years}-year delay cost {delay_value}"
        )

    if not top_tract_lines:
        top_tract_lines = ["- No tract details available."]

    brief = f"""
# TransitIQ Policy Brief  
## Cost of Doing Nothing Simulator — Columbus, Ohio

Generated: {generated_at}

---

## Executive Summary

TransitIQ estimates that delaying targeted transit investment for **{delay_years} years** exposes selected Columbus census tracts to approximately **{money(delay_cost)}** in compounded social and economic cost.

The current scenario uses a proposed transit investment of **{money(investment_amount)}**. Under this setting, the estimated cost of delay is approximately **${delay_cost_per_invested_dollar:,.2f} per $1 invested**.

---

## Scenario Snapshot

| Metric | Value |
|---|---:|
| Delay period | {delay_years} years |
| Proposed investment | {money(investment_amount)} |
| Annual cost of inaction | {money(annual_cost)} |
| Cumulative delay cost | {money(delay_cost)} |
| Population covered | {population:,.0f} |
| Census tracts included | {tract_count:,} |
| Average Transit Hardship Index | {avg_hardship:.1f} |

---

## Highest-Priority Tracts

The following tracts show the highest hardship in the current filtered view:

{chr(10).join(top_tract_lines)}

---

## Interpretation

The results suggest that delayed transit investment is not cost-neutral. The estimated burden compounds through lost wages, missed healthcare access, environmental costs, education access barriers, and worsening affordability.

TransitIQ should be interpreted as a decision-support tool, not an automatic funding allocation system.

---

## Responsible AI Guardrails

- TransitIQ does **not** make final funding decisions.
- High hardship scores should trigger deeper review, not automatic intervention.
- Results should be reviewed with community stakeholders, planners, legal teams, and budget officials.
- Outputs should be interpreted as scenario estimates, not exact predictions.
- Transit investment should be paired with anti-displacement and affordability safeguards.

---

## Recommended Next Step

Use TransitIQ to identify tracts where delayed investment creates the largest social and economic exposure, then pair the model output with community engagement and implementation feasibility review.
"""

    return brief


@st.cache_data
def load_tract_geojson():
    with open(TRACTS_PATH, "r", encoding="utf-8") as f:
        geojson = json.load(f)
    return geojson


@st.cache_data
def load_bus_stops():
    """Load COTA bus stops from GeoJSON into a simple dataframe."""
    if not STOPS_PATH.exists():
        return pd.DataFrame(columns=["stop_name", "lon", "lat"])

    with open(STOPS_PATH, "r", encoding="utf-8") as f:
        stops_geojson = json.load(f)

    rows = []

    for feature in stops_geojson.get("features", []):
        geometry = feature.get("geometry", {})
        properties = feature.get("properties", {})

        if geometry.get("type") == "Point":
            coordinates = geometry.get("coordinates", [])

            if len(coordinates) >= 2:
                lon = coordinates[0]
                lat = coordinates[1]

                rows.append(
                    {
                        "stop_name": properties.get("stop_name", "COTA stop"),
                        "lon": lon,
                        "lat": lat,
                    }
                )

    return pd.DataFrame(rows)


# --------------------------------
# Hero background image
# --------------------------------
hero_bg_base64 = image_to_base64(HERO_BG_PATH)
hero_bg_display = "block" if hero_bg_base64 else "none"
hero_bg_url = f"data:image/png;base64,{hero_bg_base64}" if hero_bg_base64 else ""


# --------------------------------
# CSS styling
# --------------------------------
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
    --font-body: 'Inter', 'Segoe UI', Arial, sans-serif;
    --font-display: 'Space Grotesk', 'Inter', 'Segoe UI', Arial, sans-serif;
}

/* Force Streamlit away from Source Sans */
html, body, .stApp, .stApp * {
    font-family: var(--font-body) !important;
}

/* Stronger font for titles, tabs, metric numbers */
h1, h2, h3,
.hero h1,
.section-title,
.metric-value,
.metric-label,
.stTabs [data-baseweb="tab"],
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    font-family: var(--font-display) !important;
    letter-spacing: -0.03em;
}

/* Sidebar labels and controls */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
button, input, textarea, select {
    font-family: var(--font-body) !important;
}

    /* Sidebar fix:
       Do NOT hide the whole Streamlit header.
       The sidebar open/close button lives inside the header.
       We hide the toolbar/menu decoration but keep the sidebar toggle usable. */
    header[data-testid="stHeader"] {
        visibility: visible !important;
        background: transparent !important;
        height: 0px !important;
    }

    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    div[data-testid="stStatusWidget"] {
        visibility: hidden !important;
        height: 0px !important;
        position: fixed !important;
    }

    /* Keep the native Streamlit sidebar visible and styled. */
    section[data-testid="stSidebar"] {
        visibility: visible !important;
        background: #FFFFFF !important;
        border-right: 1px solid #E5E7EB;
        box-shadow: 8px 0 24px rgba(15, 23, 42, 0.06);
    }

    section[data-testid="stSidebar"] * {
        visibility: visible;
    }

    /* Make the collapsed-sidebar button visible if the browser remembers a collapsed state. */
    div[data-testid="stSidebarCollapsedControl"] {
        visibility: visible !important;
        display: block !important;
        z-index: 999999 !important;
    }

    .stApp {
        background: #F8FAFC;
    }


    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    .hero {
        background: white;
        padding: 30px 34px;
        border-radius: 8px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
    }

.hero h1 {
    font-size: 2.55rem;
    margin-bottom: 0.35rem;
    font-weight: 700;
    font-family: var(--font-display) !important;
    letter-spacing: -0.045em;
}

    .hero p {
        font-size: 1.05rem;
        color: #DDEAFE;
        margin-bottom: 0;
        line-height: 1.55;
    }

    .metric-card {
        background: #FFFFFF;
        padding: 22px;
        border-radius: 8px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
        min-height: 135px;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #64748B;
        margin-bottom: 8px;
        font-weight: 600;
    }

.metric-value {
    font-size: 2.1rem;
    font-weight: 700;
    font-family: var(--font-display) !important;
    color: #0F172A;
    margin-bottom: 6px;
    letter-spacing: -0.045em;
}

    .metric-note {
        font-size: 0.82rem;
        color: #64748B;
        line-height: 1.35;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #0F172A;
        margin-top: 16px;
        margin-bottom: 12px;
    }

    .takeaway-box {
        background: #F8FAFC;
        border: 1px solid #CBD5E1;
        padding: 18px;
        border-radius: 8px;
        color: #334155;
        margin-top: 14px;
        margin-bottom: 18px;
        line-height: 1.55;
    }

    .small-note {
        color: #475569;
        font-size: 0.92rem;
        line-height: 1.5;
    }

    /* -------------------------------
   Oslo-style green sidebar
-------------------------------- */

section[data-testid="stSidebar"] {
    background: #1b2f33 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.14) !important;
}

/* Sidebar inner spacing */
section[data-testid="stSidebar"] > div {
    background: #1b2f33 !important;
    padding-top: 2rem;
}

/* Sidebar title */
section[data-testid="stSidebar"] h1 {
    color: #FFF8EA !important;
    font-family: var(--font-display) !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em;
}

/* Sidebar labels */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {
    color: #FFF8EA !important;
}

/* Sidebar helper/caption text */
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: rgba(255, 248, 234, 0.72) !important;
}

/* Divider line */
section[data-testid="stSidebar"] hr {
    border-color: rgba(255, 248, 234, 0.24) !important;
}

/* Inputs/select boxes */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
section[data-testid="stSidebar"] div[data-baseweb="input"] > div {
    background: rgba(255, 248, 234, 0.12) !important;
    border-color: rgba(255, 248, 234, 0.18) !important;
    color: #FFF8EA !important;
}

/* Multiselect selected tags */
section[data-testid="stSidebar"] span[data-baseweb="tag"] {
    background: #FFF8EA !important;
    color: #1b2f33 !important;
    font-weight: 700 !important;
}

/* Radio buttons and checkboxes */
section[data-testid="stSidebar"] input[type="radio"],
section[data-testid="stSidebar"] input[type="checkbox"] {
    accent-color: #FFF8EA !important;
}

/* Slider track/accent */
section[data-testid="stSidebar"] div[data-testid="stSlider"] div[role="slider"] {
    background-color: #FFF8EA !important;
}

/* Sidebar collapse arrows */
button[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarExpandButton"],
div[data-testid="stSidebarCollapsedControl"],
div[data-testid="collapsedControl"] {
    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;
}

/* -------------------------------
   Cleaner structured green sidebar
-------------------------------- */

section[data-testid="stSidebar"] {
    background: #1b2f33 !important;
    border-right: 1px solid rgba(255, 248, 234, 0.18) !important;
    box-shadow: 10px 0 30px rgba(0, 0, 0, 0.10);
}

section[data-testid="stSidebar"] > div {
    background: #1b2f33 !important;
    padding: 2rem 1.35rem 1.5rem 1.35rem;
}

/* Remove default top gap */
section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
    gap: 0.7rem;
}

/* Sidebar custom header */
.sidebar-brand {
    color: rgba(255, 248, 234, 0.72);
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin-bottom: 0.35rem;
}

.sidebar-title {
    color: #FFF8EA;
    font-family: var(--font-display);
    font-size: 1.75rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -0.04em;
    margin-bottom: 0.45rem;
}

.sidebar-subtitle {
    color: rgba(255, 248, 234, 0.72);
    font-size: 0.86rem;
    line-height: 1.45;
    margin-bottom: 1.35rem;
}

/* Small section labels */
.sidebar-section-label {
    color: #BFEFE0;
    font-size: 0.72rem;
    font-weight: 900;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    margin-top: 1.25rem;
    margin-bottom: 0.45rem;
    padding-top: 0.75rem;
    border-top: 1px solid rgba(255, 248, 234, 0.16);
}

/* General sidebar text */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {
    color: #FFF8EA !important;
}

/* Widget labels */
section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] label,
section[data-testid="stSidebar"] label p {
    color: #FFF8EA !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
}

/* Radio row spacing */
section[data-testid="stSidebar"] div[data-testid="stRadio"] {
    margin-bottom: 0.95rem;
}

section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
    padding-right: 0.7rem;
}

/* Checkboxes */
section[data-testid="stSidebar"] div[data-testid="stCheckbox"] {
    margin-top: 0.35rem;
    margin-bottom: 0.45rem;
}

section[data-testid="stSidebar"] input[type="checkbox"],
section[data-testid="stSidebar"] input[type="radio"] {
    accent-color: #BFEFE0 !important;
}

/* Slider */
section[data-testid="stSidebar"] div[data-testid="stSlider"] {
    margin-bottom: 1rem;
}

section[data-testid="stSidebar"] div[data-testid="stSlider"] p {
    color: #FFF8EA !important;
}

/* Select and multiselect containers */
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background: rgba(255, 248, 234, 0.12) !important;
    border: 1px solid rgba(255, 248, 234, 0.22) !important;
    border-radius: px !important;
    min-height: 46px;
}

/* Select text */
section[data-testid="stSidebar"] div[data-baseweb="select"] span,
section[data-testid="stSidebar"] div[data-baseweb="select"] div {
    color: #FFF8EA !important;
}

/* Multiselect selected tags */
section[data-testid="stSidebar"] span[data-baseweb="tag"] {
    background: #FFF8EA !important;
    border-radius: 8px !important;
    padding: 0.25rem 0.35rem !important;
    margin: 0.16rem !important;
}

section[data-testid="stSidebar"] span[data-baseweb="tag"] *,
section[data-testid="stSidebar"] span[data-baseweb="tag"] span {
    color: #1b2f33 !important;
    font-weight: 800 !important;
}

/* Multiselect input area */
section[data-testid="stSidebar"] input {
    color: #FFF8EA !important;
}

/* Dropdown arrow and close icons */
section[data-testid="stSidebar"] svg {
    color: #BFEFE0 !important;
    fill: #BFEFE0 !important;
}

/* Sidebar divider */
section[data-testid="stSidebar"] hr {
    border-color: rgba(255, 248, 234, 0.18) !important;
    margin-top: 1.4rem;
    margin-bottom: 1.2rem;
}

/* Caption / footer note */
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: rgba(255, 248, 234, 0.64) !important;
    font-size: 0.85rem !important;
    line-height: 1.5;
}

/* Keep sidebar open and hide collapse button */
button[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarExpandButton"],
div[data-testid="stSidebarCollapsedControl"],
div[data-testid="collapsedControl"],
button[title="Close sidebar"],
button[title="Open sidebar"] {
    display: none !important;
    visibility: hidden !important;
    pointer-events: none !important;
}
    </style>
    """,
    unsafe_allow_html=True,
)

# Extra hero layout: elegant rectangular image behind centered hero box.
st.markdown(
    f"""
    <style>
    .hero-stage {{
        position: relative;
        min-height: 260px;
        margin-bottom: 30px;
        padding: 26px 36px;
        border-radius: 12px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #274142;
        box-shadow: 0 18px 42px rgba(0, 16, 24, 0.16);
    }}

    .hero-image-rect {{
        display: {hero_bg_display};
        position: absolute;
        inset: 0;
        z-index: 0;
        border-radius: 24px;
        background:
            linear-gradient(
                90deg,
                rgba(0, 16, 24, 0.78) 0%,
                rgba(39, 65, 66, 0.62) 48%,
                rgba(211, 153, 107, 0.22) 100%
            ),
            url("{hero_bg_url}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }} 



    .hero-stage .hero {{
        position: relative;
        z-index: 1;
        width: min(88%, 1120px);
        margin: 0 auto;
        padding: 42px 48px;
        border-radius: 8px;
        border: 1px solid rgba(211, 153, 107, 0.38);
        background:
            linear-gradient(
                135deg,
                rgba(0, 16, 24, 0.88) 0%,
                rgba(39, 65, 66, 0.84) 100%
            ) !important;
        color: #D3996B !important;
        box-shadow: 0 14px 34px rgba(0, 16, 24, 0.28);
        backdrop-filter: blur(2px);
    }}

    .hero-stage .hero h1 {{
        color: #D3996B !important;
        font-size: 2.65rem;
        line-height: 1.08;
        margin-bottom: 1rem;
        letter-spacing: -0.035em;
    }}

    .hero-stage .hero p {{
        color: #D3996B !important;
        max-width: 960px;
        font-size: 1.05rem;
        line-height: 1.65;
        opacity: 0.92;
    }}

    .hero-stage .hero b {{
        color: #D3996B !important;
        font-weight: 800;
    }}

    @media (max-width: 900px) {{
        .hero-stage {{
            min-height: 250px;
            padding: 18px;
        }}

        .hero-stage .hero {{
            width: 100%;
            padding: 30px 26px;
        }}

        .hero-stage .hero h1 {{
            font-size: 2rem;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------
# Data loading functions
# --------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(RESULTS_PATH, dtype={"GEOID": str})
    return df


@st.cache_data
def load_tract_geojson():
    with open(TRACTS_PATH, "r", encoding="utf-8") as f:
        geojson = json.load(f)
    return geojson


# --------------------------------
# Load data
# --------------------------------
if not RESULTS_PATH.exists():
    st.error(f"Could not find file: {RESULTS_PATH}")
    st.stop()

if not TRACTS_PATH.exists():
    st.error(f"Could not find map file: {TRACTS_PATH}")
    st.stop()

df = load_data()
tract_geojson = load_tract_geojson()
bus_stops_df = load_bus_stops()


# --------------------------------
# Sidebar controls
# --------------------------------
st.sidebar.markdown(
    """
    <div class="sidebar-brand">TransitIQ</div>
    <div class="sidebar-title">Planner Controls</div>
    <div class="sidebar-subtitle">Test delay, investment, equity filters, and map layers.</div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown('<div class="sidebar-section-label">Scenario setup</div>', unsafe_allow_html=True)

delay_years = st.sidebar.radio(
    "Delay scenario",
    options=[1, 3, 5],
    index=2,
    horizontal=True,
)

investment_amount = st.sidebar.slider(
    "Proposed transit investment",
    min_value=1_000_000,
    max_value=100_000_000,
    value=25_000_000,
    step=1_000_000,
    format="$%d",
)

st.sidebar.markdown('<div class="sidebar-section-label">Equity filters</div>', unsafe_allow_html=True)
show_transit_deserts_only = st.sidebar.checkbox(
    "Show transit deserts only",
    value=False,
)

# Vulnerability segment filter
if "vulnerability_segment" in df.columns:
    available_segments = sorted(df["vulnerability_segment"].dropna().unique().tolist())

    selected_segments = st.sidebar.multiselect(
        "Vulnerability segments",
        options=available_segments,
        default=available_segments,
    )
else:
    selected_segments = []

# Map layer selector
map_layer_options = {
    "Transit Hardship Index": "transit_hardship_index",
}

if "safety_warning_score" in df.columns:
    map_layer_options["Safety Warning Score"] = "safety_warning_score"

if "displacement_risk_score" in df.columns:
    map_layer_options["Displacement Risk Score"] = "displacement_risk_score"

st.sidebar.markdown('<div class="sidebar-section-label">Map options</div>', unsafe_allow_html=True)
map_layer_label = st.sidebar.selectbox(
    "Map layer",
    options=list(map_layer_options.keys()),
)

map_color_col = map_layer_options[map_layer_label]

show_bus_stops = st.sidebar.checkbox(
    "Show COTA bus stops",
    value=False,
)

st.sidebar.divider()

st.sidebar.caption(
    "Use these controls to test how delayed investment changes cost exposure."
)


# --------------------------------
# Filter data
# --------------------------------
filtered_df = df.copy()

if selected_segments and "vulnerability_segment" in filtered_df.columns:
    filtered_df = filtered_df[
        filtered_df["vulnerability_segment"].isin(selected_segments)
    ]

if show_transit_deserts_only and "is_transit_desert" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["is_transit_desert"] == True]

if filtered_df.empty:
    st.warning("No tracts match the current filters. Adjust the sidebar controls.")
    st.stop()


# --------------------------------
# Choose correct delay cost column
# --------------------------------
delay_col = f"cumulative_delay_{delay_years}yr_cost"

if delay_col not in filtered_df.columns:
    st.error(
        f"Could not find expected delay cost column: {delay_col}. "
        "Please send me a screenshot of the dataframe columns."
    )
    st.stop()


# --------------------------------
# Main calculations
# --------------------------------
annual_cost = filtered_df["cost_of_inaction_annual"].sum()
delay_cost = filtered_df[delay_col].sum()
tract_count = len(filtered_df)
population = filtered_df["total_population"].sum()
avg_hardship = filtered_df["transit_hardship_index"].mean()

avg_safety = (
    filtered_df["safety_warning_score"].mean()
    if "safety_warning_score" in filtered_df.columns
    else None
)

avg_displacement = (
    filtered_df["displacement_risk_score"].mean()
    if "displacement_risk_score" in filtered_df.columns
    else None
)

safety_text = f"{avg_safety:.1f}/100" if avg_safety is not None else "Not available"
displacement_text = (
    f"{avg_displacement:.1f}/100" if avg_displacement is not None else "Not available"
)

delay_cost_per_invested_dollar = (
    delay_cost / investment_amount if investment_amount > 0 else 0
)

# --------------------------------
# Hero section
# --------------------------------
st.markdown(
    f"""
    <div class="hero-stage">
        <div class="hero-image-rect"></div>
        <div class="hero">
            <h1>TransitIQ — Cost of Doing Nothing Simulator</h1>
            <p>
                If Columbus delays targeted transit investment for <b>{delay_years} years</b>,
                selected census tracts face an estimated <b>{money(delay_cost)}</b>
                in compounded social and economic cost.
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------
# Tabs
# --------------------------------
(
    tab_overview,
    tab_map,
    tab_scenario,
    tab_cost,
    tab_equity,
    tab_responsible_ai,
    tab_export,
    tab_tracts,
) = st.tabs(
    [
        "🏠 Overview",
        "🗺️ Map",
        "🏛️ Scenario Compare",
        "📊 Cost Breakdown",
        "⚖️ Equity Impact",
        "🧭 Assumptions & Responsible AI",
        "📄 Export Brief",
        "🔥 High-Hardship Tracts",
    ]
)


# --------------------------------
# Tab 1: Overview
# --------------------------------
with tab_overview:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Compounded delay cost</div>
                <div class="metric-value">{money(delay_cost)}</div>
                <div class="metric-note">Estimated cost if intervention is delayed {delay_years} years.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Annual cost of inaction</div>
                <div class="metric-value">{money(annual_cost)}</div>
                <div class="metric-note">Lost wages, healthcare, environment, education, and affordability.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Population covered</div>
                <div class="metric-value">{population:,.0f}</div>
                <div class="metric-note">Residents in the selected Columbus census tracts.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Delay cost per $1 invested</div>
                <div class="metric-value">${delay_cost_per_invested_dollar:,.2f}</div>
                <div class="metric-note">Compares delay exposure against the selected investment amount.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="takeaway-box">
            <b>Demo takeaway:</b> This is not just a transit map. It is a policy simulator.
            A planner can adjust the delay period and investment amount, then see how the cost
            of waiting compounds across neighborhoods.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="small-note">
            Current view includes <b>{tract_count}</b> census tracts with an average Transit Hardship Index
            of <b>{avg_hardship:.1f}</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
    <div class="takeaway-box">
        <b>Planning risk overlays:</b><br>
        Average safety warning score: <b>{safety_text}</b><br>
        Average displacement risk score: <b>{displacement_text}</b><br><br>
        These scores should not automatically decide investment priority. They should trigger deeper planner review.
    </div>
    """,
        unsafe_allow_html=True,
    )

# --------------------------------
# Tab 2: Map
# --------------------------------
with tab_map:
    st.markdown(
        '<div class="section-title">Columbus Transit Hardship Map</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.6, 1])

    with left:
        fig_map = px.choropleth_mapbox(
            filtered_df,
            geojson=tract_geojson,
            locations="GEOID",
            featureidkey="properties.GEOID",
            color=map_color_col,
            color_continuous_scale="YlOrRd",
            mapbox_style="carto-positron",
            zoom=9.4,
            center={"lat": 39.9612, "lon": -82.9988},
            opacity=0.72,
            custom_data=["GEOID"],
            hover_name="GEOID",
            hover_data={
                "GEOID": True,
                "transit_hardship_index": ":.1f",
                "vulnerability_segment": True,
                delay_col: ":,.0f",
                "cost_of_inaction_annual": ":,.0f",
                "total_population": ":,.0f",
            },
        )

        fig_map.update_layout(
            height=620,
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(
                title=map_layer_label,
                thickness=14,
                len=0.75,
            ),
        )

        if show_bus_stops and not bus_stops_df.empty:
            fig_map.add_scattermapbox(
                lat=bus_stops_df["lat"],
                lon=bus_stops_df["lon"],
                mode="markers",
                marker=dict(
                    size=5,
                    color="#2563EB",
                    opacity=0.65,
                ),
                text=bus_stops_df["stop_name"],
                hovertemplate="<b>%{text}</b><extra></extra>",
                name="COTA bus stops",
            )

        map_event = st.plotly_chart(
            fig_map,
            use_container_width=True,
            key="hardship_map",
            on_select="rerun",
            selection_mode="points",
        )

        st.caption(
            "Tip: click a tract on the map to update the drilldown panel. "
            "Use the dropdown if clicking is not available during the demo."
        )

    with right:
        st.markdown(
            '<div class="section-title">Tract Drilldown</div>', unsafe_allow_html=True
        )

        sorted_tracts = (
            filtered_df.sort_values("transit_hardship_index", ascending=False)["GEOID"]
            .astype(str)
            .tolist()
        )

        clicked_geoid = None

        try:
            selected_points = map_event["selection"]["points"]
            if selected_points:
                clicked_geoid = selected_points[0]["customdata"][0]
        except Exception:
            clicked_geoid = None

        default_index = 0

        if clicked_geoid in sorted_tracts:
            default_index = sorted_tracts.index(clicked_geoid)

        selected_geoid = st.selectbox(
            "Choose a tract",
            options=sorted_tracts,
            index=default_index,
            help="Click a tract on the map or choose one manually.",
        )

        selected_row = filtered_df[filtered_df["GEOID"] == selected_geoid].iloc[0]

        safety_line = ""
        displacement_line = ""

        if "safety_warning_score" in selected_row.index:
            safety_line = (
                f'<b>Safety warning:</b> {selected_row["safety_warning_score"]:.1f}/100<br>'
            )

        if "displacement_risk_score" in selected_row.index:
            displacement_line = (
                f'<b>Displacement risk:</b> {selected_row["displacement_risk_score"]:.1f}/100<br>'
            )

        segment_value = (
            selected_row["vulnerability_segment"]
            if "vulnerability_segment" in selected_row.index
            else "Not available"
        )

        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Selected tract</div>
                <div class="metric-value">{selected_geoid}</div>
                <div class="metric-note">
                    <b>Segment:</b> {segment_value}<br>
                    <b>Hardship index:</b> {selected_row["transit_hardship_index"]:.1f}<br>
                    <b>Annual cost:</b> {money(selected_row["cost_of_inaction_annual"])}<br>
                    <b>{delay_years}-year delay cost:</b> {money(selected_row[delay_col])}<br>
                    <b>Population:</b> {selected_row["total_population"]:,.0f}<br>
                    {safety_line}
                    {displacement_line}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tract_component_rows = []

        component_columns = {
            "Lost wages": "lost_wages_annual",
            "Healthcare": "healthcare_annual",
            "Environment": "environment_annual",
            "Education": "education_annual",
            "Forgone affordability": "forgone_affordability_annual",
        }

        for label, column in component_columns.items():
            if column in selected_row.index:
                tract_component_rows.append(
                    {
                        "Component": label,
                        "Annual cost": selected_row[column],
                    }
                )

        if tract_component_rows:
            tract_component_df = pd.DataFrame(tract_component_rows).sort_values(
                "Annual cost",
                ascending=True,
            )
            fig_tract = px.bar(
                tract_component_df,
                x="Annual cost",
                y="Component",
                orientation="h",
                text="Annual cost",
                title="Selected tract annual cost breakdown",
            )
            fig_tract.update_traces(
                texttemplate="$%{text:,.0f}",
                textposition="auto",
                cliponaxis=False,
            )
            fig_tract.update_layout(
                height=380,
                xaxis_title="Annual cost",
                yaxis_title="",
                xaxis_tickprefix="$",
                showlegend=False,
                margin=dict(l=10, r=90, t=60, b=20),
            )
            st.plotly_chart(fig_tract, use_container_width=True)

        st.markdown(
            """
            <div class="takeaway-box">
                <b>How to demo this:</b> Hover over the map to show neighborhood-level hardship.
                Toggle COTA bus stops in the sidebar, then click or select a high-hardship tract
                to explain the cost breakdown.
            </div>
            """,
            unsafe_allow_html=True,
        )

# --------------------------------
# Tab 2: Scenario Compare
# --------------------------------
with tab_scenario:
    st.markdown(
        '<div class="section-title">Invest Now vs. Wait Scenario</div>',
        unsafe_allow_html=True,
    )

    scenario_df = pd.DataFrame(
        {
            "Scenario": [
                "Invest now",
                f"Wait {delay_years} years",
            ],
            "Total exposure": [
                investment_amount,
                investment_amount + delay_cost,
            ],
            "Explanation": [
                "Transit investment made now",
                "Investment plus estimated cost of delayed action",
            ],
        }
    )

    fig_scenario = px.bar(
        scenario_df,
        x="Scenario",
        y="Total exposure",
        text="Total exposure",
        hover_data=["Explanation"],
        title=f"Scenario comparison: fund now vs. delay {delay_years} years",
    )

    fig_scenario.update_traces(
        texttemplate="$%{text:,.0f}",
        textposition="outside",
    )

    fig_scenario.update_layout(
        height=500,
        yaxis_title="Total cost exposure",
        xaxis_title="",
        yaxis_tickprefix="$",
        showlegend=False,
        margin=dict(l=20, r=20, t=70, b=40),
    )

    st.plotly_chart(fig_scenario, use_container_width=True)

    st.markdown(
        f"""
        <div class="takeaway-box">
            <b>Scenario insight:</b> With a proposed investment of <b>{money(investment_amount)}</b>,
            waiting <b>{delay_years} years</b> creates about <b>{money(delay_cost)}</b>
            in additional social and economic exposure.
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------
# Tab 3: Cost Breakdown
# --------------------------------
with tab_cost:

    st.markdown(
        '<div class="section-title">How Delay Costs Compound Over Time</div>',
        unsafe_allow_html=True,
    )

    timeline_rows = []

    for years in [1, 3, 5]:
        col_name = f"cumulative_delay_{years}yr_cost"

        if col_name in filtered_df.columns:
            timeline_rows.append(
                {
                    "Delay years": years,
                    "Cumulative cost": filtered_df[col_name].sum(),
                    "Scenario": (
                        f"Wait {years} year" if years == 1 else f"Wait {years} years"
                    ),
                }
            )

    timeline_df = pd.DataFrame(timeline_rows)

    fig_timeline = px.line(
        timeline_df,
        x="Delay years",
        y="Cumulative cost",
        markers=True,
        text="Cumulative cost",
        title="Cumulative cost of delayed transit investment",
        hover_data={
            "Delay years": True,
            "Cumulative cost": ":,.0f",
            "Scenario": True,
        },
    )

    fig_timeline.update_traces(
        texttemplate="$%{text:,.0f}",
        textposition="top center",
        line=dict(width=4),
        marker=dict(size=12),
    )

    fig_timeline.update_layout(
        height=430,
        xaxis_title="Delay period",
        yaxis_title="Cumulative cost",
        yaxis_tickprefix="$",
        xaxis=dict(
            tickmode="array",
            tickvals=[1, 3, 5],
            ticktext=["1 year", "3 years", "5 years"],
        ),
        margin=dict(l=20, r=40, t=70, b=40),
    )

    st.plotly_chart(fig_timeline, use_container_width=True)

    st.markdown(
        f"""
        <div class="takeaway-box">
            <b>Compounding insight:</b> The longer the city waits, the more costs accumulate.
            At the current filter setting, a <b>{delay_years}-year</b> delay creates about
            <b>{money(delay_cost)}</b> in cumulative exposure.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-title">What Makes Up the Annual Cost?</div>',
        unsafe_allow_html=True,
    )

    component_columns = {
        "Lost wages": "lost_wages_annual",
        "Healthcare": "healthcare_annual",
        "Environment": "environment_annual",
        "Education": "education_annual",
        "Forgone affordability": "forgone_affordability_annual",
    }

    component_rows = []

    for label, column in component_columns.items():
        if column in filtered_df.columns:
            component_rows.append(
                {
                    "Component": label,
                    "Annual cost": filtered_df[column].sum(),
                }
            )

    component_df = pd.DataFrame(component_rows).sort_values(
        "Annual cost",
        ascending=True,
    )

    fig_components = px.bar(
        component_df,
        x="Annual cost",
        y="Component",
        orientation="h",
        text="Annual cost",
        title="Annual cost of inaction by component",
    )

    fig_components.update_traces(
        texttemplate="$%{text:,.0f}",
        textposition="outside",
    )

    fig_components.update_layout(
        height=500,
        xaxis_title="Annual cost",
        yaxis_title="",
        xaxis_tickprefix="$",
        showlegend=False,
        margin=dict(l=20, r=100, t=70, b=40),
    )

    st.plotly_chart(fig_components, use_container_width=True)

    st.markdown(
        f"""
        <div class="takeaway-box">
            <b>Model transparency:</b> The annual cost of inaction is not a single black-box score.
            It is built from five interpretable components: lost wages, healthcare access,
            environmental burden, education access, and forgone affordability.
        </div>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------
# Tab 5: Equity Impact
# --------------------------------
with tab_equity:
    st.markdown(
        '<div class="section-title">Equity Impact by Vulnerability Segment</div>',
        unsafe_allow_html=True,
    )

    equity_df = filtered_df.groupby("vulnerability_segment", as_index=False).agg(
        tracts=("GEOID", "count"),
        population=("total_population", "sum"),
        avg_hardship=("transit_hardship_index", "mean"),
        annual_cost=("cost_of_inaction_annual", "sum"),
        delay_cost=(delay_col, "sum"),
    )

    if "transit_dependent_population_estimate" in filtered_df.columns:
        dependent_pop = filtered_df.groupby(
            "vulnerability_segment", as_index=False
        ).agg(
            transit_dependent_population=(
                "transit_dependent_population_estimate",
                "sum",
            )
        )

        equity_df = equity_df.merge(
            dependent_pop,
            on="vulnerability_segment",
            how="left",
        )
    else:
        equity_df["transit_dependent_population"] = 0

    equity_df = equity_df.sort_values("delay_cost", ascending=False)

    left, right = st.columns(2)

    with left:
        fig_equity_cost = px.bar(
            equity_df,
            x="vulnerability_segment",
            y="delay_cost",
            text="delay_cost",
            title=f"{delay_years}-year delay cost by vulnerability segment",
            hover_data={
                "tracts": True,
                "population": ":,.0f",
                "avg_hardship": ":.1f",
                "delay_cost": ":,.0f",
            },
        )

        fig_equity_cost.update_traces(
            texttemplate="$%{text:,.0f}",
            textposition="outside",
        )

        fig_equity_cost.update_layout(
            height=460,
            xaxis_title="Vulnerability segment",
            yaxis_title=f"{delay_years}-year delay cost",
            yaxis_tickprefix="$",
            margin=dict(l=20, r=40, t=70, b=80),
        )

        st.plotly_chart(fig_equity_cost, use_container_width=True)

    with right:
        fig_equity_pop = px.bar(
            equity_df,
            x="vulnerability_segment",
            y="population",
            text="population",
            title="Population covered by vulnerability segment",
            hover_data={
                "tracts": True,
                "avg_hardship": ":.1f",
                "population": ":,.0f",
            },
        )

        fig_equity_pop.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside",
        )

        fig_equity_pop.update_layout(
            height=460,
            xaxis_title="Vulnerability segment",
            yaxis_title="Population",
            margin=dict(l=20, r=40, t=70, b=80),
        )

        st.plotly_chart(fig_equity_pop, use_container_width=True)

    st.markdown(
        """
        <div class="takeaway-box">
            <b>Equity insight:</b> TransitIQ separates total cost from distributional burden.
            This helps planners see whether delayed investment falls most heavily on high-need,
            transit-dependent, or already burdened neighborhoods.
        </div>
        """,
        unsafe_allow_html=True,
    )

    equity_table = equity_df.copy()

    equity_table["annual_cost"] = equity_table["annual_cost"].map(
        lambda x: f"${x:,.0f}"
    )
    equity_table["delay_cost"] = equity_table["delay_cost"].map(lambda x: f"${x:,.0f}")
    equity_table["avg_hardship"] = equity_table["avg_hardship"].map(
        lambda x: f"{x:.1f}"
    )
    equity_table["population"] = equity_table["population"].map(lambda x: f"{x:,.0f}")
    equity_table["transit_dependent_population"] = equity_table[
        "transit_dependent_population"
    ].map(lambda x: f"{x:,.0f}")

    equity_table = equity_table.rename(
        columns={
            "vulnerability_segment": "Vulnerability Segment",
            "tracts": "Tracts",
            "population": "Population",
            "avg_hardship": "Avg Hardship Index",
            "annual_cost": "Annual Cost",
            "delay_cost": f"{delay_years}-Year Delay Cost",
            "transit_dependent_population": "Transit-Dependent Population",
        }
    )

    st.dataframe(
        equity_table,
        use_container_width=True,
        hide_index=True,
    )

# --------------------------------
# Tab 6: Assumptions & Responsible AI
# --------------------------------
with tab_responsible_ai:
    st.markdown(
        '<div class="section-title">Assumptions, Uncertainty, and Responsible AI Guardrails</div>',
        unsafe_allow_html=True,
    )

    uncertainty_df = pd.DataFrame(
        {
            "Estimate": ["Low estimate", "Base estimate", "High estimate"],
            "Cumulative delay cost": [
                delay_cost * 0.85,
                delay_cost,
                delay_cost * 1.15,
            ],
            "Explanation": [
                "15% below base estimate",
                "Current model estimate",
                "15% above base estimate",
            ],
        }
    )

    fig_uncertainty = px.bar(
        uncertainty_df,
        x="Estimate",
        y="Cumulative delay cost",
        text="Cumulative delay cost",
        hover_data=["Explanation"],
        title=f"Uncertainty range for {delay_years}-year delay scenario",
    )

    fig_uncertainty.update_traces(
        texttemplate="$%{text:,.0f}",
        textposition="outside",
    )

    fig_uncertainty.update_layout(
        height=440,
        yaxis_title="Cumulative delay cost",
        xaxis_title="",
        yaxis_tickprefix="$",
        margin=dict(l=20, r=40, t=70, b=40),
        showlegend=False,
    )

    st.plotly_chart(fig_uncertainty, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div class="takeaway-box">
                <b>What TransitIQ is for:</b><br>
                TransitIQ is a decision-support simulator for city planners.
                It helps compare delayed transit investment scenarios, surface
                neighborhood-level burden, and make tradeoffs visible.
                <br><br>
                <b>Human-in-the-loop rule:</b><br>
                The dashboard does not decide which neighborhoods receive funding.
                It provides evidence for planners, community stakeholders, and budget teams.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="takeaway-box">
                <b>When not to use this tool alone:</b><br>
                Do not use TransitIQ as the only basis for final funding allocation.
                Do not use it without community review, local context, engineering feasibility,
                legal review, and anti-displacement planning.
                <br><br>
                <b>Misuse risk:</b><br>
                A high hardship score should trigger deeper review, not automatic intervention.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="section-title">Core Model Assumptions</div>',
        unsafe_allow_html=True,
    )

    assumptions_df = pd.DataFrame(
        {
            "Model Area": [
                "Transit hardship",
                "Delay scenarios",
                "Cost components",
                "Uncertainty",
                "Equity interpretation",
                "Safety and displacement",
            ],
            "Assumption": [
                "Higher hardship means a tract has more transit access burden and socioeconomic vulnerability.",
                "The dashboard compares 1, 3, and 5-year delay scenarios using precomputed cost outputs.",
                "Annual cost includes lost wages, healthcare, environment, education, and forgone affordability.",
                "Displayed uncertainty range uses a simple ±15% sensitivity band around the base estimate.",
                "Segment-level results are used to show distributional burden, not to rank people or assign blame.",
                "Safety and displacement indicators are warning overlays that require separate policy review.",
            ],
            "Dashboard Use": [
                "Color the map and identify high-need tracts.",
                "Show how cost exposure changes when intervention is delayed.",
                "Explain where the annual cost of inaction comes from.",
                "Avoid presenting model outputs as exact predictions.",
                "Help planners understand who may be most affected.",
                "Prevent transit investment from being interpreted without broader planning safeguards.",
            ],
        }
    )

    st.dataframe(
        assumptions_df,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        """
        <div class="takeaway-box">
            <b>Judge-facing explanation:</b> TransitIQ intentionally shows assumptions,
            uncertainty, and limitations inside the dashboard. This makes the system more
            transparent and reduces the risk that a policy model is treated as a perfect prediction.
        </div>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------
# Tab 7: Export Brief
# --------------------------------
with tab_export:
    st.markdown(
        '<div class="section-title">Export Decision Brief</div>', unsafe_allow_html=True
    )

    export_cols = [
        "GEOID",
        "transit_hardship_index",
        "vulnerability_segment",
        "cost_of_inaction_annual",
        delay_col,
        "total_population",
    ]

    available_export_cols = [col for col in export_cols if col in filtered_df.columns]

    export_top_tracts = (
        filtered_df[available_export_cols]
        .sort_values("transit_hardship_index", ascending=False)
        .head(10)
        .copy()
    )

    export_top_tracts = export_top_tracts.rename(
        columns={
            "GEOID": "Tract GEOID",
            "transit_hardship_index": "Hardship Index",
            "vulnerability_segment": "Vulnerability Segment",
            "cost_of_inaction_annual": "Annual Cost",
            delay_col: f"{delay_years}-Year Delay Cost",
            "total_population": "Population",
        }
    )

    # Format selected dollar fields for the brief
    formatted_export_top_tracts = export_top_tracts.copy()

    if "Annual Cost" in formatted_export_top_tracts.columns:
        formatted_export_top_tracts["Annual Cost"] = formatted_export_top_tracts[
            "Annual Cost"
        ].map(lambda x: f"${x:,.0f}")

    delay_display_col = f"{delay_years}-Year Delay Cost"

    if delay_display_col in formatted_export_top_tracts.columns:
        formatted_export_top_tracts[delay_display_col] = formatted_export_top_tracts[
            delay_display_col
        ].map(lambda x: f"${x:,.0f}")

    if "Hardship Index" in formatted_export_top_tracts.columns:
        formatted_export_top_tracts["Hardship Index"] = formatted_export_top_tracts[
            "Hardship Index"
        ].map(lambda x: f"{x:.1f}")

    if "Population" in formatted_export_top_tracts.columns:
        formatted_export_top_tracts["Population"] = formatted_export_top_tracts[
            "Population"
        ].map(lambda x: f"{x:,.0f}")

    policy_brief = build_policy_brief(
        delay_years=delay_years,
        investment_amount=investment_amount,
        delay_cost=delay_cost,
        annual_cost=annual_cost,
        population=population,
        tract_count=tract_count,
        avg_hardship=avg_hardship,
        delay_cost_per_invested_dollar=delay_cost_per_invested_dollar,
        top_tracts_df=formatted_export_top_tracts,
    )

    st.markdown(
        """
        <div class="takeaway-box">
            <b>What this does:</b> Generate a short policy brief from the current dashboard settings.
            Change the delay period, investment amount, or filters, then return here to export the updated version.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.download_button(
        label="Download Policy Brief",
        data=policy_brief,
        file_name=f"TransitIQ_policy_brief_{delay_years}yr_delay.md",
        mime="text/markdown",
    )

    st.markdown('<div class="section-title">Preview</div>', unsafe_allow_html=True)

    st.markdown(policy_brief)

    st.markdown(
        '<div class="section-title">Top Tracts Included in Brief</div>',
        unsafe_allow_html=True,
    )

    st.dataframe(
        formatted_export_top_tracts,
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------
# Tab 4: High-Hardship Tracts
# --------------------------------
with tab_tracts:
    st.markdown(
        '<div class="section-title">Highest Hardship Tracts</div>',
        unsafe_allow_html=True,
    )

    display_cols = [
        "GEOID",
        "transit_hardship_index",
        "vulnerability_segment",
        "cost_of_inaction_annual",
        delay_col,
        "total_population",
    ]

    available_cols = [col for col in display_cols if col in filtered_df.columns]

    top_tracts = (
        filtered_df[available_cols]
        .sort_values("transit_hardship_index", ascending=False)
        .head(15)
        .copy()
    )

    rename_map = {
        "GEOID": "Tract GEOID",
        "transit_hardship_index": "Hardship Index",
        "vulnerability_segment": "Vulnerability Segment",
        "cost_of_inaction_annual": "Annual Cost",
        delay_col: f"{delay_years}-Year Delay Cost",
        "total_population": "Population",
    }

    top_tracts = top_tracts.rename(columns=rename_map)

    st.dataframe(
        top_tracts,
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Developer check: raw processed data"):
        st.write(f"Rows loaded: {len(df)}")
        st.write(f"Columns loaded: {len(df.columns)}")
        st.dataframe(df.head(20), use_container_width=True)

# --------------------------------
# Footer
# --------------------------------
st.markdown(
    """
    <div style="
        margin-top: 36px;
        padding: 18px 22px;
        border-top: 1px solid #CBD5E1;
        color: #64748B;
        font-size: 0.9rem;
        line-height: 1.5;
    ">
        <b>TransitIQ</b> is a human-in-the-loop decision-support prototype.
        It estimates the cost of delayed transit investment using public tract-level data,
        scenario modeling, and transparent assumptions. Outputs are intended to support
        planner review, not replace community engagement or policy judgment.
    </div>
    """,
    unsafe_allow_html=True,
)
