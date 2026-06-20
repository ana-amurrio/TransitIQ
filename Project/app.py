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
SAND = "#fcaa67"
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

# Keep every chart inside the TransitIQ palette.
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = [FOREST, CLAY, SAND, TAUPE, INK]
px.defaults.color_continuous_scale = MAP_SCALE


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


def format_tract_label(geoid):
    """Convert an 11-digit Census GEOID into its standard readable tract name.

    e.g. '39049009323' -> 'Census Tract 93.23' (state 39 = Ohio, county 049 =
    Franklin County, tract code 009323). This is the official Census naming
    convention, not a neighborhood name — there's no neighborhood-level data
    in the current dataset, so this is the most accurate human-readable label
    available without a new data source (see City of Columbus GIS Open Data,
    'Columbus Communities' boundary layer, for a real neighborhood crosswalk).
    """
    geoid = str(geoid).strip()

    if len(geoid) != 11 or not geoid.isdigit():
        return geoid

    tract_code = geoid[5:]
    whole = tract_code[:4].lstrip("0") or "0"
    decimal = tract_code[4:]

    if decimal == "00":
        return f"Census Tract {whole}"

    return f"Census Tract {whole}.{decimal}"


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

    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&family=Material+Symbols+Outlined&display=swap');

    :root {
        --sand: #fcaa67;
        --clay: #A57662;
        --taupe: #94837C;
        --forest: #274142;
        --ink: #001018;
        --white: #FFFFFF;
        --cream: #FFF9F2;
        --page: #FBFAF7;
        --line: rgba(148, 131, 124, 0.26);
        --shadow: 0 14px 34px rgba(0, 16, 24, 0.09);
        --font-body: 'Inter', 'Segoe UI', Arial, sans-serif;
        --font-display: 'Space Grotesk', 'Inter', 'Segoe UI', Arial, sans-serif;
    }

    html, body, .stApp,
    .stApp *:not([data-testid="stSidebarCollapseButton"]):not([data-testid="stSidebarExpandButton"]) {
        font-family: var(--font-body) !important;
    }

    /* The rule above is intentionally broad, but it can also clobber
       Streamlit's built-in Material Symbols icon font (e.g. the sidebar
       collapse arrow), making it render as literal text like
       "keyboard_double_arrow_left" instead of a glyph. This restores the
       icon font for known Streamlit icon patterns; the @import above also
       now loads that font ourselves rather than assuming Streamlit's own
       loading of it is working. */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"] *,
    [data-testid="stSidebarExpandButton"],
    [data-testid="stSidebarExpandButton"] *,
    [data-testid="stIconMaterial"],
    [data-testid*="IconMaterial"],
    [data-testid*="Icon"],
    [translate="no"],
    span[class*="material-icons"],
    span[class*="material-symbols"] {
        font-family: 'Material Symbols Outlined', 'Material Icons', sans-serif !important;
    }

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
        letter-spacing: -0.035em;
    }





    .stApp {
        background: var(--page);
        color: var(--ink);
    }

    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 2.8rem;
        max-width: 1500px;
    }

    /* -------------------------------
       Sidebar
    -------------------------------- */
    section[data-testid="stSidebar"] {
        visibility: visible !important;
        background: linear-gradient(180deg, var(--ink) 0%, var(--forest) 100%) !important;
        border-right: 1px solid rgba(211, 153, 107, 0.22) !important;
        box-shadow: 12px 0 36px rgba(0, 16, 24, 0.18);
    }

    section[data-testid="stSidebar"] * {
        visibility: visible;
    }

    section[data-testid="stSidebar"] > div {
        background: transparent !important;
        padding: 2rem 1.35rem 1.5rem 1.35rem;
    }

    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 0.75rem;
    }

    /* Zero out Streamlit's native per-widget spacing inside the sidebar so
       every gap is governed by ONE value (the flex `gap` above), instead of
       native margins and custom gaps stacking unevenly between different
       widget types — this is what was causing uneven spacing throughout. */
    section[data-testid="stSidebar"] div[data-testid="element-container"] {
        margin: 0 !important;
    }

    .sidebar-brand {
        color: rgba(255, 255, 255, 0.65);
        font-size: 0.72rem;
        font-weight: 900;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    .sidebar-title {
        color: var(--white);
        font-family: var(--font-display);
        font-size: 1.75rem;
        font-weight: 700;
        line-height: 1;
        letter-spacing: -0.04em;
        margin-bottom: 0.55rem;
    }

    .sidebar-subtitle {
        color: rgba(255, 255, 255, 0.70);
        font-size: 1.2rem;
        line-height: 1.45;
        margin-bottom: 2rem;
    }

    .sidebar-section-label {
        color: var(--sand);
        font-size: 1rem;
        font-weight: 800;
        letter-spacing: 0.13em;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }

    /* -------------------------------
       Sidebar control cards
       Targets any stVerticalBlock nested inside another stVerticalBlock
       within the sidebar — i.e. an explicit st.sidebar.container(), not the
       single outermost block Streamlit wraps the whole sidebar in. This
       relies only on the stVerticalBlock test-id, which is already proven
       to work above, rather than guessing at a border-wrapper test-id.
       Shadow + a barely-there background only, no border, per request.
    -------------------------------- */
    section[data-testid="stSidebar"]
        div[data-testid="stVerticalBlock"]
        div[data-testid="stVerticalBlock"] {
        background: rgba(255, 255, 255, 0.05) !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 24px 18px !important;
        margin-bottom: 2px !important;
    }

    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div {
        color: var(--white) !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] label,
    section[data-testid="stSidebar"] label p {
        color: var(--white) !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] {
        margin-bottom: 0.95rem;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
        padding-right: 0.7rem;
    }

    section[data-testid="stSidebar"] input[type="checkbox"],
    section[data-testid="stSidebar"] input[type="radio"] {
        accent-color: var(--sand) !important;
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] > div,
    section[data-testid="stSidebar"] div[data-baseweb="input"] > div {
        background: rgba(255, 255, 255, 0.10) !important;
        border: 1px solid rgba(211, 153, 107, 0.32) !important;
        border-radius: 10px !important;
        min-height: 46px;
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] span,
    section[data-testid="stSidebar"] div[data-baseweb="select"] div {
        color: var(--white) !important;
    }

    section[data-testid="stSidebar"] span[data-baseweb="tag"] {
        background: var(--cream) !important;
        border-radius: 8px !important;
        padding: 0.25rem 0.35rem !important;
        margin: 0.16rem !important;
    }

    section[data-testid="stSidebar"] span[data-baseweb="tag"] *,
    section[data-testid="stSidebar"] span[data-baseweb="tag"] span {
        color: var(--forest) !important;
        font-weight: 800 !important;
    }

    section[data-testid="stSidebar"] input {
        color: var(--white) !important;
    }

    section[data-testid="stSidebar"] svg {
        color: var(--sand) !important;
        fill: var(--sand) !important;
    }

    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.18) !important;
        margin-top: 1.4rem;
        margin-bottom: 1.2rem;
    }

    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: rgba(255, 255, 255, 0.58) !important;
        font-size: 0.85rem !important;
        line-height: 1.5;
    }

/* ==================================
   SIDEBAR TOGGLE BUTTON - VISIBLE
================================== */

/* Make collapse button visible */
button[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarExpandButton"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;

    background: rgba(252,170,103,.15) !important;
    border: 1px solid rgba(252,170,103,.35) !important;
    border-radius: 10px !important;
}

/* Icon color */
button[data-testid="stSidebarCollapseButton"] svg,
button[data-testid="stSidebarExpandButton"] svg {
    fill: #fcaa67 !important;
    color: #fcaa67 !important;
}

/* Hover state */
button[data-testid="stSidebarCollapseButton"]:hover,
button[data-testid="stSidebarExpandButton"]:hover {
    background: rgba(252,170,103,.25) !important;
}

    /* -------------------------------
       Hero section with background image
    -------------------------------- */
    .hero-stage {
        position: relative;
        min-height: 245px;
        margin-bottom: 1.75rem;
        padding: 46px 52px;
        border-radius: 16px;
        overflow: hidden;
        display: flex;
        align-items: center;
        background: linear-gradient(135deg, var(--ink) 0%, var(--forest) 100%);
    }

    .hero-image-rect {
        position: absolute;
        inset: 0;
        z-index: 0;
        background:
            linear-gradient(
                90deg,
                rgba(0, 16, 24, 0.86) 0%,
                rgba(0, 16, 24, 0.82) 42%,
                rgba(39, 65, 66, 0.65) 68%,
                rgba(211, 153, 107, 0.22) 100%
            ),
            url("HERO_BG_URL_PLACEHOLDER");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }

    .hero-image-rect::after {
        content: "";
        position: absolute;
        inset: 0;
        background:
            radial-gradient(circle at 85% 110%, rgba(211, 153, 107, 0.34) 0%, rgba(211, 153, 107, 0.12) 34%, transparent 58%);
        z-index: 1;
    }

    .hero-stage .hero {
        position: relative;
        z-index: 2;
        margin: 0;
        padding: 0;
        border: 0;
        background: transparent;
        box-shadow: none !important;
        color: var(--white) !important;
    }

    .hero-stage .hero h1 {
        color: var(--white) !important;
        font-size: clamp(2.1rem, 4vw, 3.45rem);
        line-height: 1.04;
        font-weight: 700;
        margin: 0 0 1rem 0;
        letter-spacing: -0.03em;
    }

    .hero-stage .hero p {
        color: rgba(255, 255, 255, 0.86) !important;
        max-width: 940px;
        font-size: 1.08rem;
        line-height: 1.65;
        margin: 0;
    }

    .hero-stage .hero b {
        color: var(--sand) !important;
        font-weight: 850;
    }

    /* -------------------------------
       Tabs
    -------------------------------- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.35rem;
        margin-bottom: 0px;
    }

    .stTabs [data-baseweb="tab"] {
        height: auto;
        padding: 0.88rem 0.88rem 0.78rem 0.88rem;
        border-radius: 8px 8px 0 0;
        color: rgba(0, 16, 24, 0.72);
        font-size: 0.92rem;
        font-weight: 700;
        background: transparent;
    }

    .stTabs [data-baseweb="tab"] p {
        color: inherit !important;
        margin: 0;
    }

    .stTabs [aria-selected="true"] {
        color: var(--forest) !important;
        background: rgba(39, 65, 66, 0.06) !important;
    }

    /* -------------------------------
       Overview cards and content blocks
    -------------------------------- */
    .metric-card {
        background: linear-gradient(180deg, var(--white) 0%, #FFFDF9 100%);
        padding: 24px 24px 22px 24px;
        border-radius: 16px;
        border: 1px solid rgba(148, 131, 124, 0.22);
        box-shadow: 0 10px 28px rgba(0, 16, 24, 0.06);
        min-height: 168px;
        transition: transform 120ms ease, box-shadow 120ms ease;
    }

    .metric-top {
        display: flex;
        align-items: center;
        gap: 13px;
        margin-bottom: 12px;
    }

    .metric-icon {
        width: 46px;
        height: 46px;
        min-width: 46px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        background: rgba(39, 65, 66, 0.10);
        color: var(--forest);
        font-size: 1.28rem;
        font-weight: 800;
    }

    .metric-label {
        font-size: 0.94rem;
        color: var(--forest);
        margin: 0;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .metric-value {
        font-size: 44px;
        font-weight: 800;
        font-family: var(--font-display) !important;
        color: var(--ink);
        margin: 2px 0 9px 0;
        letter-spacing: -0.055em;
    }

    .metric-note {
        font-size: 0.88rem;
        color: rgba(0, 16, 24, 0.62);
        line-height: 1.45;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: var(--ink);
        margin-top: 16px;
        margin-bottom: 12px;
    }

    .takeaway-box,
    .callout-box {
        background: linear-gradient(90deg, rgba(39, 65, 66, 0.07), rgba(211, 153, 107, 0.07));
        border: 1px solid rgba(39, 65, 66, 0.18);
        padding: 18px 20px;
        border-radius: 16px;
        color: var(--forest);
        margin-top: 1.25rem;
        margin-bottom: 1.25rem;
        line-height: 1.55;
    }

    .callout-box {
        display: flex;
        align-items: center;
        gap: 18px;
        padding: 20px 22px;
    }

    .callout-icon {
        width: 48px;
        height: 48px;
        min-width: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        background: var(--forest);
        color: var(--white);
        font-size: 1.35rem;
    }

    .callout-box b,
    .takeaway-box b {
        color: var(--ink);
    }

    .small-note {
        color: var(--forest);
        font-size: 0.96rem;
        line-height: 1.55;
        margin: 1.05rem 0 1.15rem 0;
    }

    .small-note-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border-radius: 999px;
        margin-right: 8px;
        background: rgba(39, 65, 66, 0.10);
        color: var(--forest);
        font-size: 0.88rem;
    }

    .risk-card {
        display: grid;
        grid-template-columns: 240px 1fr 1fr;
        gap: 24px;
        align-items: center;
        background: var(--white);
        border: 1px solid rgba(148, 131, 124, 0.22);
        border-radius: 16px;
        padding: 22px 26px;
        box-shadow: 0 10px 28px rgba(0, 16, 24, 0.055);
        margin-top: 0.8rem;
    }

    .risk-title-wrap {
        display: flex;
        align-items: center;
        gap: 14px;
    }

    .risk-icon {
        width: 48px;
        height: 48px;
        border-radius: 999px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(39, 65, 66, 0.10);
        color: var(--forest);
        font-size: 1.3rem;
    }

    .risk-title {
        font-weight: 800;
        color: var(--forest);
        font-size: 1rem;
    }

    .risk-item {
        border-left: 1px solid rgba(148, 131, 124, 0.25);
        padding-left: 26px;
    }

    .risk-label {
        color: rgba(0, 16, 24, 0.62);
        font-size: 0.88rem;
        margin-bottom: 4px;
    }

    .risk-value {
        color: var(--ink);
        font-family: var(--font-display);
        font-weight: 800;
        font-size: 1.25rem;
        letter-spacing: -0.035em;
    }

    /* Lightly polish default Streamlit blocks */
    div[data-testid="stDataFrame"],
    div[data-testid="stPlotlyChart"] {
        border-radius: 16px;
    }

    @media (max-width: 1100px) {
        .hero-stage {
            padding: 34px 32px;
        }

        .hero-stage .hero {
            width: min(100%, 820px);
        }

        .hero-stage::before,
        .hero-stage::after {
            opacity: 0.38;
        }

        .risk-card {
            grid-template-columns: 1fr;
            gap: 14px;
        }

        .risk-item {
            border-left: 0;
            border-top: 1px solid rgba(148, 131, 124, 0.25);
            padding-left: 0;
            padding-top: 14px;
        }
    }
    </style>
    """.replace("HERO_BG_URL_PLACEHOLDER", hero_bg_url),
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
df["tract_label"] = df["GEOID"].apply(format_tract_label)
tract_geojson = load_tract_geojson()
bus_stops_df = load_bus_stops()


# --------------------------------
# Sidebar controls
# --------------------------------
st.sidebar.markdown(
    """
    <div class="sidebar-title">Planner Controls</div>
    <div class="sidebar-subtitle">To test delay, investment, equity filters, and map layers.</div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar.container():
    st.markdown('<div class="sidebar-section-label">Scenario setup</div>', unsafe_allow_html=True)

    delay_years = st.radio(
        "Delay scenario (in years)",
        options=[1, 3, 5],
        index=2,
        horizontal=True,
    )

    investment_amount = st.slider(
        "Proposed transit investment",
        min_value=1_000_000,
        max_value=100_000_000,
        value=25_000_000,
        step=1_000_000,
        format="%d",
    )

    st.markdown(
        f"""
        <div style="
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 1.3rem;
            color: var(--sand);
            letter-spacing: -0.02em;
        ">
            ${investment_amount:,}
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.sidebar.container():
    st.markdown('<div class="sidebar-section-label">Equity filters</div>', unsafe_allow_html=True)

    show_transit_deserts_only = st.checkbox(
        "Show transit deserts only",
        value=False,
    )

    # Vulnerability segment filter
    if "vulnerability_segment" in df.columns:
        available_segments = sorted(df["vulnerability_segment"].dropna().unique().tolist())

        selected_segments = st.multiselect(
            "Vulnerability segments",
            options=available_segments,
            default=available_segments,
        )
    else:
        selected_segments = []

# Map layer selector (data prep only — not rendered)
map_layer_options = {
    "Transit Hardship Index": "transit_hardship_index",
}

if "safety_warning_score" in df.columns:
    map_layer_options["Safety Warning Score"] = "safety_warning_score"

if "displacement_risk_score" in df.columns:
    map_layer_options["Displacement Risk Score"] = "displacement_risk_score"

with st.sidebar.container():
    st.markdown('<div class="sidebar-section-label">Map options</div>', unsafe_allow_html=True)

    map_layer_label = st.selectbox(
        "Map layer",
        options=list(map_layer_options.keys()),
    )

    show_bus_stops = st.checkbox(
        "Show COTA bus stops",
        value=False,
    )

map_color_col = map_layer_options[map_layer_label]


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
# Sidebar: Export policy brief
# --------------------------------
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

with st.sidebar.container():
    st.markdown('<div class="sidebar-section-label">Export</div>', unsafe_allow_html=True)
    st.caption(
        "Download a one-page policy brief built from the current scenario and filters."
    )
    st.download_button(
        label="📄 Download Policy Brief",
        data=policy_brief,
        file_name=f"TransitIQ_policy_brief_{delay_years}yr_delay.md",
        mime="text/markdown",
    )

# --------------------------------
# Hero section
# --------------------------------
st.markdown(
    f"""
    <div class="hero-stage">
        <div class="hero-image-rect"></div>
        <div class="hero">
            <h1>TransitIQ: The Price of Delayed Transit</h1>
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
    tab_tracts,
) = st.tabs(
    [
        "🏠 Overview",
        "🗺️ Map",
        "🏛️ Scenario Compare",
        "📊 Cost Breakdown",
        "⚖️ Equity Impact",
        "🧭 Assumptions & Responsible AI",
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
                <div class="metric-top">
                    <div class="metric-icon">$</div>
                    <div class="metric-label">Compounded delay cost</div>
                </div>
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
                <div class="metric-top">
                    <div class="metric-icon">▥</div>
                    <div class="metric-label">Annual cost of inaction</div>
                </div>
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
                <div class="metric-top">
                    <div class="metric-icon">◉</div>
                    <div class="metric-label">Population covered</div>
                </div>
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
                <div class="metric-top">
                    <div class="metric-icon">↗</div>
                    <div class="metric-label">Delay cost per $1 invested</div>
                </div>
                <div class="metric-value">${delay_cost_per_invested_dollar:,.2f}</div>
                <div class="metric-note">Compares delay exposure against the selected investment amount.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="callout-box">
            <div class="callout-icon">☼</div>
            <div>
                <b>What you're looking at:</b> not just a transit map, but a policy simulator.
                Adjust the delay period and investment amount in the sidebar to see how the cost
                of waiting compounds across neighborhoods.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="small-note">
            <span class="small-note-icon">●</span>
            Current view includes <b>{tract_count}</b> census tracts with an average Transit Hardship Index
            of <b>{avg_hardship:.1f}</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="risk-card">
            <div class="risk-title-wrap">
                <div class="risk-icon">◇</div>
                <div class="risk-title">Planning risk overlays</div>
            </div>
            <div class="risk-item">
                <div class="risk-label">Average safety warning score</div>
                <div class="risk-value">{safety_text}</div>
            </div>
            <div class="risk-item">
                <div class="risk-label">Average displacement risk score</div>
                <div class="risk-value">{displacement_text}</div>
            </div>
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
            color_continuous_scale=MAP_SCALE,
            mapbox_style="carto-positron",
            zoom=9.4,
            center={"lat": 39.9612, "lon": -82.9988},
            opacity=0.72,
            custom_data=["GEOID"],
            hover_name="tract_label",
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
                    color=FOREST,
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
            "Tip: click a tract on the map to update the drilldown panel, or use the "
            "dropdown — tracts are listed by name, not by raw ID number."
        )

    with right:
        st.markdown(
            '<div class="section-title">Tract Drilldown</div>', unsafe_allow_html=True
        )

        sorted_tracts_df = filtered_df.sort_values(
            "transit_hardship_index", ascending=False
        )
        sorted_tracts = sorted_tracts_df["GEOID"].astype(str).tolist()

        tract_lookup = sorted_tracts_df.set_index("GEOID")[
            ["tract_label", "transit_hardship_index"]
        ].to_dict("index")

        def _format_tract_option(geoid):
            info = tract_lookup.get(geoid)
            if not info:
                return geoid
            return f"{info['tract_label']} (hardship {info['transit_hardship_index']:.0f})"

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
            format_func=_format_tract_option,
            help=(
                "Click a tract on the map or choose one manually. Sorted by hardship, "
                "highest first."
            ),
        )

        selected_row = filtered_df[filtered_df["GEOID"] == selected_geoid].iloc[0]
        selected_label = selected_row.get("tract_label", selected_geoid)

        safety_line = ""
        displacement_line = ""

        if "safety_warning_score" in selected_row.index:
            safety_line = (
                f'<b>Safety warning:</b> {selected_row["safety_warning_score"]:.1f}/100 '
                f'<span style="color: rgba(0,16,24,0.55); font-weight: 400;">'
                f"(0 = no concern, 100 = highest)</span><br>"
            )

        if "displacement_risk_score" in selected_row.index:
            displacement_line = (
                f'<b>Displacement risk:</b> {selected_row["displacement_risk_score"]:.1f}/100 '
                f'<span style="color: rgba(0,16,24,0.55); font-weight: 400;">'
                f"(0 = low risk, 100 = high risk)</span><br>"
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
                <div class="metric-value" style="font-size: 30px;">{selected_label}</div>
                <div class="metric-note">
                    <span style="color: rgba(0,16,24,0.5);">GEOID {selected_geoid}</span><br>
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

        component_columns = {
            "Lost wages": "lost_wages_annual",
            "Healthcare": "healthcare_annual",
            "Environment": "environment_annual",
            "Education": "education_annual",
            "Forgone affordability": "forgone_affordability_annual",
        }

        component_colors = {
            "Lost wages": FOREST,
            "Healthcare": CLAY,
            "Environment": SAND,
            "Education": TAUPE,
            "Forgone affordability": INK,
        }

        tract_component_rows = []

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

            tract_total = tract_component_df["Annual cost"].sum()

            tract_component_df["Label"] = tract_component_df["Annual cost"].apply(
                lambda v: (
                    f"${v:,.0f} ({v / tract_total:.0%})" if tract_total > 0 else f"${v:,.0f}"
                )
            )

            fig_tract = px.bar(
                tract_component_df,
                x="Annual cost",
                y="Component",
                orientation="h",
                text="Label",
                title="Selected tract annual cost breakdown",
            )
            fig_tract.update_traces(
                marker_color=[
                    component_colors[c] for c in tract_component_df["Component"]
                ],
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
            st.caption(
                "Percentages show each component's share of this tract's total annual "
                "cost — useful when one driver dominates, as it often does in severely "
                "rent-burdened tracts."
            )

        st.markdown(
            """
            <div class="takeaway-box">
                <b>How to use this map:</b> Hover over a tract to see its hardship score,
                toggle COTA bus stops in the sidebar, and click any tract — or pick it from the
                dropdown — to open its cost breakdown.
            </div>
            """,
            unsafe_allow_html=True,
        )

# --------------------------------
# Tab 2: Scenario Compare
# --------------------------------
with tab_scenario:
    st.markdown(
        '<div class="section-title">Invest Now vs. Wait — What Does Delay Actually Cost?</div>',
        unsafe_allow_html=True,
    )

    scenario_label = f"Wait {delay_years} year" if delay_years == 1 else f"Wait {delay_years} years"

    # Headline number: this is the comparison judges and planners actually want —
    # not two raw totals, but the cost AVOIDED by acting now.
    st.markdown(
        f"""
        <div class="callout-box">
            <div class="callout-icon">↻</div>
            <div>
                <b>Cost avoided by investing now: {money(delay_cost)}.</b>
                Both paths eventually require the same {money(investment_amount)} investment —
                waiting {delay_years} {"year" if delay_years == 1 else "years"} just adds this
                much social and economic cost on top of it before the investment happens.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Stacked bars: the "Investment" segment is identical in both bars (same base
    # spend either way). Only the "Wait" bar carries the extra "Cost of waiting"
    # segment — that segment IS the cost avoided, made visible rather than implied.
    scenario_rows = [
        {"Scenario": "Invest now", "Segment": "Investment", "Value": investment_amount},
        {"Scenario": "Invest now", "Segment": "Cost of waiting", "Value": 0},
        {"Scenario": scenario_label, "Segment": "Investment", "Value": investment_amount},
        {"Scenario": scenario_label, "Segment": "Cost of waiting", "Value": delay_cost},
    ]
    scenario_df = pd.DataFrame(scenario_rows)

    fig_scenario = px.bar(
        scenario_df,
        x="Scenario",
        y="Value",
        color="Segment",
        category_orders={"Scenario": ["Invest now", scenario_label]},
        color_discrete_map={"Investment": FOREST, "Cost of waiting": SAND},
    )

    fig_scenario.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>%{x}: $%{y:,.0f}<extra></extra>",
    )

    fig_scenario.update_layout(
        height=500,
        barmode="stack",
        yaxis_title="Total cost exposure",
        xaxis_title="",
        yaxis_tickprefix="$",
        legend_title_text="",
        margin=dict(l=20, r=20, t=50, b=40),
    )

    total_wait = investment_amount + delay_cost

    fig_scenario.add_annotation(
        x="Invest now",
        y=investment_amount,
        text=f"<b>{money(investment_amount)}</b>",
        showarrow=False,
        yshift=18,
        font=dict(size=15, color=INK, family=PLOTLY_FONT),
    )
    fig_scenario.add_annotation(
        x=scenario_label,
        y=total_wait,
        text=f"<b>{money(total_wait)}</b>",
        showarrow=False,
        yshift=18,
        font=dict(size=15, color=INK, family=PLOTLY_FONT),
    )

    st.plotly_chart(fig_scenario, use_container_width=True)

    st.markdown(
        f"""
        <div class="takeaway-box">
            <b>How to read this:</b> the dark segment is the {money(investment_amount)} transit
            investment — it's spent either way. The highlighted segment on the right bar is the
            extra cost the city absorbs simply by waiting {delay_years}
            {"year" if delay_years == 1 else "years"} instead of funding now.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="callout-box">
            <div class="callout-icon">⚠</div>
            <div>
                <b>Displacement risk warning:</b> Average displacement risk for the selected
                tracts is <b>{displacement_text}</b>. Investing now removes the cost of waiting,
                but new transit access can also raise rents and price out the residents it's
                meant to help. Pair any funded scenario with affordable housing safeguards and
                review the displacement overlay before finalizing tracts.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------
# Tab 3: Cost Breakdown
# --------------------------------
with tab_cost:

    st.markdown(
        '<div class="section-title">The Cost of Doing Nothing — Compounding by Component</div>',
        unsafe_allow_html=True,
    )

    component_columns = {
        "Lost wages": "lost_wages_annual",
        "Healthcare": "healthcare_annual",
        "Environment": "environment_annual",
        "Education": "education_annual",
        "Forgone affordability": "forgone_affordability_annual",
    }

    component_colors = {
        "Lost wages": FOREST,
        "Healthcare": CLAY,
        "Environment": SAND,
        "Education": TAUPE,
        "Forgone affordability": INK,
    }

    available_components = {
        label: column
        for label, column in component_columns.items()
        if column in filtered_df.columns
    }

    # Current annual mix per component (this year's actual figures)
    component_annual_totals = {
        label: filtered_df[column].sum() for label, column in available_components.items()
    }
    annual_component_total = sum(component_annual_totals.values())

    component_shares = (
        {
            label: value / annual_component_total
            for label, value in component_annual_totals.items()
        }
        if annual_component_total > 0
        else {label: 0 for label in component_annual_totals}
    )

    scenario_order = [
        f"Wait {y} year" if y == 1 else f"Wait {y} years" for y in [1, 3, 5]
    ]

    # Apportion each year's known TOTAL cumulative cost across components,
    # holding each component's share of the mix constant — the same uniform
    # growth assumption the cost engine itself uses (cost(year N) = sum of
    # components x growth factor), just rendered component-by-component.
    stacked_rows = []

    for years in [1, 3, 5]:
        col_name = f"cumulative_delay_{years}yr_cost"

        if col_name not in filtered_df.columns:
            continue

        year_total = filtered_df[col_name].sum()
        scenario_label = f"Wait {years} year" if years == 1 else f"Wait {years} years"

        for label, share in component_shares.items():
            stacked_rows.append(
                {
                    "Delay years": years,
                    "Scenario": scenario_label,
                    "Component": label,
                    "Cost": year_total * share,
                }
            )

    stacked_df = pd.DataFrame(stacked_rows)

    fig_compounding = px.bar(
        stacked_df,
        x="Scenario",
        y="Cost",
        color="Component",
        category_orders={
            "Component": list(available_components.keys()),
            "Scenario": scenario_order,
        },
        color_discrete_map=component_colors,
    )

    fig_compounding.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>%{x}: $%{y:,.0f}<extra></extra>",
    )

    fig_compounding.update_layout(
        height=540,
        barmode="stack",
        xaxis_title="",
        yaxis_title="Cumulative cost of delay",
        yaxis_tickprefix="$",
        legend_title_text="Cost component",
        margin=dict(l=20, r=20, t=50, b=40),
    )

    # Bold total label above each stacked bar
    year_totals = stacked_df.groupby("Scenario", as_index=False)["Cost"].sum()

    for _, row in year_totals.iterrows():
        fig_compounding.add_annotation(
            x=row["Scenario"],
            y=row["Cost"],
            text=f"<b>{money(row['Cost'])}</b>",
            showarrow=False,
            yshift=20,
            font=dict(size=15, color=INK, family=PLOTLY_FONT),
        )

    st.plotly_chart(fig_compounding, use_container_width=True)

    largest_component = (
        max(component_annual_totals, key=component_annual_totals.get)
        if component_annual_totals
        else None
    )
    largest_share = (
        component_shares.get(largest_component, 0) if largest_component else 0
    )

    st.markdown(
        f"""
        <div class="takeaway-box">
            <b>Compounding insight:</b> Waiting <b>{delay_years} years</b> instead of investing now
            creates about <b>{money(delay_cost)}</b> in cumulative exposure across the selected tracts.
            <b>{largest_component or "Lost wages"}</b> is the single largest driver, making up about
            <b>{largest_share:.0%}</b> of the annual cost of inaction — not a single black-box score,
            but five interpretable components.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "Each bar's component mix is held at its current proportion and scaled with the cost "
        "engine's compounding growth rate for years 1, 3, and 5 — the same uniform growth "
        "assumption used to compute total exposure. This is a visualization simplification, "
        "not a separate model; exact per-component figures by year are in the underlying data."
    )

# --------------------------------
# Tab 5: Equity Impact
# --------------------------------
with tab_equity:
    st.markdown(
        '<div class="section-title">Who Bears the Cost of Waiting?</div>',
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

    # Demographic context, where the processing layer carries these columns
    # through — this is what lets us NAME who a segment represents instead of
    # leaving it as an abstract cluster label.
    demographic_aggs = {}

    if "median_income" in filtered_df.columns:
        demographic_aggs["avg_median_income"] = ("median_income", "mean")

    if "pct_no_vehicle" in filtered_df.columns:
        demographic_aggs["avg_pct_no_vehicle"] = ("pct_no_vehicle", "mean")

    if demographic_aggs:
        demo_df = filtered_df.groupby("vulnerability_segment", as_index=False).agg(
            **demographic_aggs
        )
        equity_df = equity_df.merge(demo_df, on="vulnerability_segment", how="left")

    # The actual equity question isn't "which segment has the most people" —
    # it's "which segment carries the heaviest burden per resident." Compute
    # that directly instead of making the viewer divide two separate charts.
    equity_df["delay_cost_per_capita"] = (
        equity_df["delay_cost"]
        / equity_df["population"].where(equity_df["population"] > 0, other=pd.NA)
    ).fillna(0)

    equity_df = equity_df.sort_values("delay_cost", ascending=False)

    left, right = st.columns(2)

    with left:
        fig_equity_cost = px.bar(
            equity_df,
            x="vulnerability_segment",
            y="delay_cost",
            text="delay_cost",
            title=f"Total {delay_years}-year delay cost by segment",
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
            marker_color=FOREST,
        )

        fig_equity_cost.update_layout(
            height=460,
            xaxis_title="",
            yaxis_title=f"{delay_years}-year delay cost",
            yaxis_tickprefix="$",
            margin=dict(l=20, r=40, t=70, b=80),
        )

        st.plotly_chart(fig_equity_cost, use_container_width=True)
        st.caption("Scale: total dollars exposed in each segment.")

    with right:
        per_capita_df = equity_df.sort_values(
            "delay_cost_per_capita", ascending=False
        )

        fig_equity_per_capita = px.bar(
            per_capita_df,
            x="vulnerability_segment",
            y="delay_cost_per_capita",
            text="delay_cost_per_capita",
            title=f"{delay_years}-year delay cost PER RESIDENT by segment",
            hover_data={
                "tracts": True,
                "population": ":,.0f",
                "avg_hardship": ":.1f",
                "delay_cost_per_capita": ":,.0f",
            },
        )

        fig_equity_per_capita.update_traces(
            texttemplate="$%{text:,.0f}",
            textposition="outside",
            marker_color=SAND,
        )

        fig_equity_per_capita.update_layout(
            height=460,
            xaxis_title="",
            yaxis_title="Delay cost per resident",
            yaxis_tickprefix="$",
            margin=dict(l=20, r=40, t=70, b=80),
        )

        st.plotly_chart(fig_equity_per_capita, use_container_width=True)
        st.caption("Concentration: same dollars, but who actually carries it per person.")

    # Build a dynamic, data-driven callout instead of a static generic blurb —
    # this is what "names the disproportionately affected groups" means in
    # practice: an actual segment name and an actual number, not a category.
    burdened_segments = equity_df[equity_df["population"] > 0]

    if not burdened_segments.empty:
        highest_row = burdened_segments.loc[
            burdened_segments["delay_cost_per_capita"].idxmax()
        ]
        positive_per_capita = burdened_segments[
            burdened_segments["delay_cost_per_capita"] > 0
        ]["delay_cost_per_capita"]

        multiplier_text = ""
        if len(positive_per_capita) > 1:
            lowest_value = positive_per_capita.min()
            if lowest_value > 0 and highest_row["delay_cost_per_capita"] > lowest_value:
                multiplier = highest_row["delay_cost_per_capita"] / lowest_value
                if multiplier >= 1.1:
                    multiplier_text = f", about {multiplier:.1f}x the burden of the least-affected segment"

        income_text = ""
        if "avg_median_income" in highest_row.index and pd.notna(
            highest_row.get("avg_median_income")
        ):
            income_text = (
                f" Average median household income there is "
                f"{money(highest_row['avg_median_income'])}."
            )

        vehicle_text = ""
        if "avg_pct_no_vehicle" in highest_row.index and pd.notna(
            highest_row.get("avg_pct_no_vehicle")
        ):
            vehicle_text = (
                f" About {highest_row['avg_pct_no_vehicle']:.0%} of workers there "
                f"have no vehicle."
            )

        st.markdown(
            f"""
            <div class="takeaway-box">
                <b>Who's disproportionately affected:</b> the
                <b>{highest_row['vulnerability_segment']}</b> segment carries the highest cost
                per resident — about <b>{money(highest_row['delay_cost_per_capita'])} per
                person</b>{multiplier_text}.{income_text}{vehicle_text}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="callout-box">
            <div class="callout-icon">ⓘ</div>
            <div>
                <b>What this view leaves out:</b> the underlying Census pull does not include
                race or ethnicity, so this equity lens is built from income, vehicle access,
                and transit dependency — not race. Treat "disproportionately affected" as
                economic and access-based, and pair this view with local demographic context
                before drawing conclusions about specific communities.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    equity_table = equity_df.copy()

    equity_table["annual_cost"] = equity_table["annual_cost"].map(
        lambda x: f"${x:,.0f}"
    )
    equity_table["delay_cost"] = equity_table["delay_cost"].map(lambda x: f"${x:,.0f}")
    equity_table["delay_cost_per_capita"] = equity_table["delay_cost_per_capita"].map(
        lambda x: f"${x:,.0f}"
    )
    equity_table["avg_hardship"] = equity_table["avg_hardship"].map(
        lambda x: f"{x:.1f}"
    )
    equity_table["population"] = equity_table["population"].map(lambda x: f"{x:,.0f}")
    equity_table["transit_dependent_population"] = equity_table[
        "transit_dependent_population"
    ].map(lambda x: f"{x:,.0f}")

    rename_map = {
        "vulnerability_segment": "Vulnerability Segment",
        "tracts": "Tracts",
        "population": "Population",
        "avg_hardship": "Avg Hardship Index",
        "annual_cost": "Annual Cost",
        "delay_cost": f"{delay_years}-Year Delay Cost",
        "delay_cost_per_capita": f"{delay_years}-Year Cost Per Resident",
        "transit_dependent_population": "Transit-Dependent Population",
    }

    if "avg_median_income" in equity_table.columns:
        equity_table["avg_median_income"] = equity_table["avg_median_income"].map(
            lambda x: money(x) if pd.notna(x) else "N/A"
        )
        rename_map["avg_median_income"] = "Avg Median Income"

    if "avg_pct_no_vehicle" in equity_table.columns:
        equity_table["avg_pct_no_vehicle"] = equity_table["avg_pct_no_vehicle"].map(
            lambda x: f"{x:.0%}" if pd.notna(x) else "N/A"
        )
        rename_map["avg_pct_no_vehicle"] = "Avg % No Vehicle"

    equity_table = equity_table.rename(columns=rename_map)

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

    # Uncertainty widens with the forecast horizon instead of one flat
    # percentage — a 5-year projection genuinely carries more uncertainty
    # than a 1-year one, so the displayed range should reflect that rather
    # than reusing the same ±15% regardless of how far out the estimate reaches.
    uncertainty_pct_by_horizon = {1: 0.10, 3: 0.15, 5: 0.20}
    uncertainty_pct = uncertainty_pct_by_horizon.get(delay_years, 0.15)

    uncertainty_df = pd.DataFrame(
        {
            "Estimate": ["Low estimate", "Base estimate", "High estimate"],
            "Cumulative delay cost": [
                delay_cost * (1 - uncertainty_pct),
                delay_cost,
                delay_cost * (1 + uncertainty_pct),
            ],
            "Explanation": [
                f"{uncertainty_pct:.0%} below base estimate",
                "Current model estimate",
                f"{uncertainty_pct:.0%} above base estimate",
            ],
        }
    )

    fig_uncertainty = px.bar(
        uncertainty_df,
        x="Estimate",
        y="Cumulative delay cost",
        text="Cumulative delay cost",
        hover_data=["Explanation"],
        color="Estimate",
        category_orders={"Estimate": ["Low estimate", "Base estimate", "High estimate"]},
        color_discrete_map={
            "Low estimate": TAUPE,
            "Base estimate": FOREST,
            "High estimate": SAND,
        },
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
        margin=dict(l=20, r=40, t=50, b=40),
        showlegend=False,
    )

    st.plotly_chart(fig_uncertainty, use_container_width=True)

    st.caption(
        f"The band widens with the forecast horizon — ±{uncertainty_pct:.0%} for a "
        f"{delay_years}-year projection — rather than one flat percentage regardless of "
        "how far out the estimate reaches. This is a simplified sensitivity range, not a "
        "statistical confidence interval; its purpose is to show planners a range instead "
        "of a single number."
    )

    st.markdown(
        '<div class="section-title">Human-in-the-Loop Design</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div class="takeaway-box">
                <b>What the AI does not decide:</b><br>
                TransitIQ never allocates funding. It estimates cost exposure, clusters
                tracts into vulnerability segments, and surfaces tradeoffs. A human planner
                always makes the final call on which tracts get funded.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
            <div class="takeaway-box">
                <b>Decisions requiring two review cycles:</b><br>
                Any recommendation touching a tract with an elevated displacement-risk
                score, or that would commit significant funding, should pass through two
                independent reviews — one by the planning team validating the underlying
                data, one by a community or equity reviewer assessing displacement and
                fairness — before going to council.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
            <div class="takeaway-box">
                <b>When not to use this tool alone:</b><br>
                Not without community review, local context, engineering feasibility,
                legal review, and anti-displacement planning. A high hardship score should
                trigger deeper review, not automatic intervention.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="section-title">Primary Risk &amp; Mitigation</div>',
        unsafe_allow_html=True,
    )

    risk_col, mitigation_col = st.columns(2)

    with risk_col:
        st.markdown(
            """
            <div class="takeaway-box">
                <b>Risk — false positives:</b><br>
                A tract flagged "high-need" could misdirect funding toward the wrong
                neighborhood if the underlying data is incomplete, stale, or drawn from a
                small or suppressed-population tract.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with mitigation_col:
        st.markdown(
            """
            <div class="takeaway-box">
                <b>Mitigation:</b><br>
                Require planner review before any funding decision; never auto-allocate.
                Per-tract data-quality flagging (e.g. surfacing which tracts have
                suppressed or imputed Census values) is identified as a v1.5 priority and
                is not yet implemented in this dataset — stated here rather than implied.
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
                "The uncertainty range widens with the forecast horizon (±10% at 1 year, ±15% at 3 years, ±20% at 5 years) around the base estimate.",
                "Segment-level results are used to show distributional burden, not to rank people or assign blame. Built from income, vehicle access, and transit dependency — not race, which isn't in the underlying data.",
                "Safety and displacement indicators are warning overlays that require separate policy review.",
            ],
            "Dashboard Use": [
                "Color the map and identify high-need tracts.",
                "Show how cost exposure changes when intervention is delayed.",
                "Explain where the annual cost of inaction comes from.",
                "Avoid presenting model outputs as exact predictions.",
                "Help planners understand who may be most affected, and by what measures.",
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
            <b>Why this matters:</b> TransitIQ intentionally shows its assumptions,
            uncertainty, and limitations inside the dashboard itself. That transparency is what
            keeps a policy model from being mistaken for a perfect prediction.
        </div>
        """,
        unsafe_allow_html=True,
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
