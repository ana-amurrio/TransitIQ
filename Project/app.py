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
    [data-testid="stSidebarNav"] {display: none !important;}
    [data-testid="stSidebarNavItems"] {display: none !important;}
    [data-testid="stSidebarNavSeparator"] {display: none !important;}
    /* Keep sidebar always open — no collapse/expand in demo mode */
    section[data-testid="stSidebar"] {
        transform: translateX(0) !important;
        min-width: 21rem !important;
        width: 21rem !important;
        display: block !important;
    }
    section[data-testid="stSidebar"] > div {
        width: 21rem !important;
    }
    [data-testid="stSidebarCollapseButton"] {display: none !important;}
    [data-testid="stSidebarExpandButton"] {display: none !important;}
    header[data-testid="stHeader"] {display: none !important;}
    /* Hide only the keyboard shortcut text label inside the collapse/expand button,
       NOT the button itself — so the sidebar can still be toggled. */
    [data-testid="stSidebarCollapseButton"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebarExpandButton"] [data-testid="stMarkdownContainer"] {display: none !important;}
    /* Streamlit 1.37+ floating keyboard shortcut hint */
    [data-testid="InputInstructions"] {display: none !important;}
    div[class*="keyboardShortcut"] {display: none !important;}

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


        /* -------------------------------
       Sidebar download button (Export)
       Streamlit renders this as a white-background button. The broad
       "section[data-testid=stSidebar] p/span/div { color: white }" rule
       above was forcing the label text white-on-white, making it
       invisible (only the color emoji survived, since emoji glyphs
       ignore the CSS color property). Style it explicitly instead of
       inheriting the global sidebar text color.
    -------------------------------- */
    section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button {
        background: var(--sand) !important;
        border: none !important;
        border-radius: 10px !important;
        width: 100% !important;
        padding: 0.65rem 1rem !important;
        box-shadow: 0 6px 16px rgba(252, 170, 103, 0.28) !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button p,
    section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button span,
    section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button div {
        color: var(--ink) !important;
        font-weight: 700 !important;
        font-size: 0.92rem !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stDownloadButton"] button:hover {
        background: #ffb87a !important;
        box-shadow: 0 8px 20px rgba(252, 170, 103, 0.4) !important;
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

# Enrich tract_label with neighbourhood names if lookup CSV exists
_names_path = BASE_DIR / "data" / "processed" / "tract_neighborhood_names.csv"
if _names_path.exists():
    _names_df = pd.read_csv(_names_path, dtype={"GEOID": str})
    _names_df["GEOID"] = _names_df["GEOID"].str.zfill(11)
    df["GEOID"] = df["GEOID"].astype(str).str.zfill(11)
    df = df.merge(_names_df[["GEOID", "display_name"]], on="GEOID", how="left")
    # Use neighbourhood display_name where available, fall back to tract_label
    df["tract_label"] = df["display_name"].fillna(df["tract_label"])
    df = df.drop(columns=["display_name"])
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

with st.sidebar.container():
    st.markdown('<div class="sidebar-section-label">Tract focus</div>', unsafe_allow_html=True)

    _tracts_sorted = (
        df[["GEOID", "tract_label", "transit_hardship_index", "vulnerability_segment"]]
        .sort_values("transit_hardship_index", ascending=False)
    )
    _tract_geoid_list = _tracts_sorted["GEOID"].tolist()
    _tract_lookup_sidebar = _tracts_sorted.set_index("GEOID").to_dict("index")

    def _sidebar_tract_label(geoid):
        info = _tract_lookup_sidebar.get(geoid, {})
        name = info.get("tract_label", geoid)
        hardship = info.get("transit_hardship_index", "")
        segment = info.get("vulnerability_segment", "")
        short_seg = segment.split()[0] if segment else ""
        return f"{name}  ·  hardship {hardship:.0f}  ·  {short_seg}" if hardship != "" else name

    selected_tract_geoids = st.multiselect(
        "Focus on specific tracts",
        options=_tract_geoid_list,
        default=[],
        format_func=_sidebar_tract_label,
        placeholder="All tracts shown",
    )
    if selected_tract_geoids:
        st.caption(f"{len(selected_tract_geoids)} tract(s) selected — all other filters still apply.")

with st.sidebar.container():
    st.markdown('<div class="sidebar-section-label">Model assumptions</div>', unsafe_allow_html=True)
    st.caption("Adjust these to test sensitivity. All outputs update live.")

    missed_care_pct = st.slider(
        "Missed care rate (%)",
        min_value=1, max_value=20, value=5, step=1, format="%d%%",
        help="% of transit-dependent residents who miss healthcare per year. Default: 5% (Urban Institute).",
    )
    cost_per_episode = st.slider(
        "Cost per missed care episode ($)",
        min_value=500, max_value=3000, value=1200, step=100, format="$%d",
        help="Average cost of a missed healthcare visit. Default: $1,200.",
    )
    growth_rate_pct = st.slider(
        "Annual growth rate (%)",
        min_value=1, max_value=6, value=3, step=1, format="%d%%",
        help="Blended annual cost growth rate for compounding. Default: 2.5% (BLS/Census trend).",
    )

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

if selected_tract_geoids:
    filtered_df = filtered_df[filtered_df["GEOID"].isin(selected_tract_geoids)]

if filtered_df.empty:
    st.warning("No tracts match the current filters. Adjust the sidebar controls.")
    st.stop()

# --------------------------------
# Apply assumption adjustments (live recompute from sliders)
# --------------------------------
_missed_care_rate = missed_care_pct / 100
_growth_rate = growth_rate_pct / 100

# Scale healthcare by ratio of new assumptions vs defaults (5% rate, $1,200/episode)
_healthcare_scale = (_missed_care_rate / 0.05) * (cost_per_episode / 1200)
filtered_df = filtered_df.copy()
filtered_df["healthcare_annual"] = (filtered_df["healthcare_annual"] * _healthcare_scale).round(2)

# Recompute annual total from adjusted components
_components = ["lost_wages_annual", "healthcare_annual", "environment_annual",
               "education_annual", "forgone_affordability_annual"]
_available_components = [c for c in _components if c in filtered_df.columns]
filtered_df["cost_of_inaction_annual"] = filtered_df[_available_components].sum(axis=1).round(2)

# Recompute cumulative delay costs with adjusted growth rate
_component_rates = {
    "lost_wages_annual": 0.035,
    "healthcare_annual": 0.045,
    "environment_annual": _growth_rate,
    "education_annual": 0.012,
    "forgone_affordability_annual": 0.03,
}
for _dy in (1, 3, 5):
    _cum = pd.Series(0.0, index=filtered_df.index)
    for _yr in range(1, _dy + 1):
        for _comp, _rate in _component_rates.items():
            if _comp in filtered_df.columns:
                _cum += filtered_df[_comp] * (1 + _rate) ** _yr
    filtered_df[f"cumulative_delay_{_dy}yr_cost"] = _cum.round(2)



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
    tab_equity,
    tab_tracts,
    tab_map,
    tab_cost,
    tab_scenario,
    tab_responsible_ai,
) = st.tabs(
    [
        "💰 Cost of Inaction",
        "⚖️ Who Pays?",
        "🎯 Where to Invest First",
        "🗺️ Hardship Map",
        "📊 Cost Trajectory",
        "🏛️ ROI of Acting Now",
        "🛡️ Responsible AI",
    ]
)


# --------------------------------
# Tab 1: Overview
# --------------------------------
with tab_overview:

    # --- Row 1: Current state (doesn't change with delay slider) ---
    st.markdown(
        '<div style="font-size:0.78rem; text-transform:uppercase; letter-spacing:0.12em; '
        'color: var(--taupe); font-weight:700; margin-bottom:8px;">Current state — right now, today</div>',
        unsafe_allow_html=True,
    )
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-top">
                    <div class="metric-icon">▥</div>
                    <div class="metric-label">Annual cost of inaction</div>
                </div>
                <div class="metric-value">{money(annual_cost)}</div>
                <div class="metric-note">Cost per year, right now — the base rate the model compounds forward.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with row1_col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-top">
                    <div class="metric-icon">◉</div>
                    <div class="metric-label">Population at risk</div>
                </div>
                <div class="metric-value">{population:,.0f}</div>
                <div class="metric-note">Residents in selected tracts — same people, however long we wait.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:1.2rem;'></div>", unsafe_allow_html=True)

    # --- Row 2: Scenario outputs (change with delay slider) ---
    st.markdown(
        f'<div style="font-size:0.78rem; text-transform:uppercase; letter-spacing:0.12em; '
        f'color: #b94a48; font-weight:700; margin-bottom:8px;">'
        f'⚠ If we wait — {delay_years}-year delay scenario</div>',
        unsafe_allow_html=True,
    )
    _transit_dep_pop = (
        filtered_df["transit_dependent_population_estimate"].sum()
        if "transit_dependent_population_estimate" in filtered_df.columns
        else filtered_df["total_population"].sum()
    )
    _cost_per_worker = delay_cost / _transit_dep_pop if _transit_dep_pop > 0 else 0
    _delay_yrs_label = "year" if delay_years == 1 else "years"

    st.markdown(
        f"""
        <div style="display:flex;gap:1rem;margin-bottom:1rem;">
            <div class="metric-card" style="flex:1;border-left:4px solid #b94a48;">
                <div class="metric-top">
                    <div class="metric-icon" style="background:rgba(185,74,72,0.10);color:#b94a48;">$</div>
                    <div class="metric-label" style="color:#b94a48;">Compounded delay cost</div>
                </div>
                <div class="metric-value" style="color:#b94a48;">{money(delay_cost)}</div>
                <div class="metric-note">Total cost if investment delayed {delay_years} {_delay_yrs_label}.</div>
            </div>
            <div class="metric-card" style="flex:1;border-left:4px solid #b94a48;">
                <div class="metric-top">
                    <div class="metric-icon" style="background:rgba(185,74,72,0.10);color:#b94a48;">↗</div>
                    <div class="metric-label" style="color:#b94a48;">Delay cost per $1 invested</div>
                </div>
                <div class="metric-value" style="color:#b94a48;">${delay_cost_per_invested_dollar:,.2f}</div>
                <div class="metric-note">Every $1 invested avoids this in social cost.</div>
            </div>
            <div class="metric-card" style="flex:1;border-left:4px solid #b94a48;">
                <div class="metric-top">
                    <div class="metric-icon" style="background:rgba(185,74,72,0.10);color:#b94a48;">▲</div>
                    <div class="metric-label" style="color:#b94a48;">Cost per transit-dependent worker</div>
                </div>
                <div class="metric-value" style="color:#b94a48;">{money(_cost_per_worker)}</div>
                <div class="metric-note">Borne by {_transit_dep_pop:,.0f} transit-dependent residents.</div>
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
            custom_data=[
                "GEOID",
                "tract_label",
                "transit_hardship_index",
                "vulnerability_segment",
                delay_col,
                "cost_of_inaction_annual",
                "total_population",
            ],
        )

        fig_map.update_traces(
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>"
                "<span style='color:#888;font-size:0.82em'>GEOID %{customdata[0]} · Columbus, OH</span><br><br>"
                "<b>Hardship Index:</b> %{customdata[2]:.1f}<br>"
                "<b>Segment:</b> %{customdata[3]}<br>"
                f"<b>{delay_years}-Yr Delay Cost:</b> $%{{customdata[4]:,.0f}}<br>"
                "<b>Annual Cost of Inaction:</b> $%{customdata[5]:,.0f}<br>"
                "<b>Population:</b> %{customdata[6]:,.0f}"
                "<extra></extra>"
            )
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
                    <span style="color: rgba(0,16,24,0.35); font-size: 0.78rem;">Census GEOID {selected_geoid}</span><br>
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
            "Forgone affordability": "#9B8FA8",   # dusty mauve
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
            # Fixed display order — consistent across all tracts
            _fixed_order = ["Lost wages", "Healthcare", "Environment", "Education", "Forgone affordability"]
            tract_component_df = pd.DataFrame(tract_component_rows)
            tract_component_df["_order"] = tract_component_df["Component"].map(
                {c: i for i, c in enumerate(reversed(_fixed_order))}
            )
            tract_component_df = tract_component_df.sort_values("_order").drop(columns=["_order"])

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
            st.caption("% = each component's share of this tract's total annual cost.")

# --------------------------------
# Tab 2: Scenario Compare
# --------------------------------
with tab_scenario:
    st.markdown(
        '<div class="section-title">Invest Now vs. Wait — What Does Delay Actually Cost?</div>',
        unsafe_allow_html=True,
    )

    # ── Pre-compute costs at 1yr / 3yr / 5yr for both charts ──
    _c1 = filtered_df["cumulative_delay_1yr_cost"].sum() if "cumulative_delay_1yr_cost" in filtered_df.columns else 0
    _c3 = filtered_df["cumulative_delay_3yr_cost"].sum() if "cumulative_delay_3yr_cost" in filtered_df.columns else 0
    _c5 = filtered_df["cumulative_delay_5yr_cost"].sum() if "cumulative_delay_5yr_cost" in filtered_df.columns else 0

    # Per-resident figures (based on at-risk population)
    _pop = filtered_df["total_population"].sum()
    _pr1 = _c1 / _pop if _pop > 0 else 0
    _pr3 = _c3 / _pop if _pop > 0 else 0
    _pr5 = _c5 / _pop if _pop > 0 else 0

    # ── Headline callout ──
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

    # ── Per-resident stat row ──
    st.markdown(
        f"""
        <div style="display:flex;gap:1rem;margin:0.75rem 0 1.25rem 0;">
            <div style="flex:1;background:#fff;border:1px solid #e2ddd9;border-radius:10px;padding:1rem 1.2rem;">
                <div style="font-size:0.72rem;color:#888;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Wait 1 year · per resident</div>
                <div style="font-size:1.6rem;font-weight:700;color:{INK};">${_pr1:,.0f}</div>
            </div>
            <div style="flex:1;background:#fff;border:1px solid #e2ddd9;border-radius:10px;padding:1rem 1.2rem;">
                <div style="font-size:0.72rem;color:#888;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Wait 3 years · per resident</div>
                <div style="font-size:1.6rem;font-weight:700;color:#b94a48;">${_pr3:,.0f}</div>
            </div>
            <div style="flex:1;background:#fff;border:1px solid #e2ddd9;border-radius:10px;padding:1rem 1.2rem;">
                <div style="font-size:0.72rem;color:#888;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Wait 5 years · per resident</div>
                <div style="font-size:1.6rem;font-weight:700;color:#b94a48;">${_pr5:,.0f}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── CHART 1: Line chart — compounding gap year by year ──
    st.markdown(
        '<div style="font-size:0.95rem;font-weight:600;color:#444;margin-bottom:0.2rem;">The widening gap: every year of delay adds to total exposure</div>',
        unsafe_allow_html=True,
    )

    # Build year-by-year cumulative cost for the line chart
    _comp_cols = {
        "lost_wages_annual": 0.035,
        "healthcare_annual": 0.045,
        "environment_annual": _growth_rate,
        "education_annual": 0.012,
        "forgone_affordability_annual": 0.03,
    }
    _line_rows = []
    for _yr in range(0, 6):
        _cum = 0.0
        for _col, _rate in _comp_cols.items():
            if _col in filtered_df.columns:
                _cum += sum(filtered_df[_col].sum() * (1 + _rate) ** y for y in range(1, _yr + 1))
        _line_rows.append({"Year": _yr, "Invest Now": investment_amount, "Cost of Waiting": _cum})

    line_df = pd.DataFrame(_line_rows)

    import plotly.graph_objects as go
    fig_line = go.Figure()

    fig_line.add_trace(go.Scatter(
        x=line_df["Year"], y=line_df["Invest Now"],
        mode="lines+markers", name="Invest Now",
        line=dict(color=FOREST, width=3, dash="dash"),
        marker=dict(size=7),
        hovertemplate="Year %{x}: <b>$%{y:,.0f}</b><extra>Invest Now</extra>",
    ))
    fig_line.add_trace(go.Scatter(
        x=line_df["Year"], y=line_df["Cost of Waiting"],
        mode="lines+markers", name="Cumulative cost of delay",
        line=dict(color="#C0392B", width=3),
        marker=dict(size=7),
        hovertemplate="Year %{x}: <b>$%{y:,.0f}</b><extra>Cost of Waiting</extra>",
        fill="tonexty", fillcolor="rgba(192,57,43,0.08)",
    ))

    # Annotate year 5 gap
    fig_line.add_annotation(
        x=5, y=_c5 / 2,
        text=f"<b>{money(_c5)}<br>avoidable cost</b>",
        showarrow=False,
        font=dict(size=12, color="#C0392B", family=PLOTLY_FONT),
        bgcolor="rgba(255,255,255,0.85)",
        bordercolor="#C0392B",
        borderwidth=1,
        borderpad=6,
    )

    fig_line.update_layout(
        height=380,
        xaxis=dict(
            tickmode="array", tickvals=list(range(0, 6)),
            ticktext=["Now", "Yr 1", "Yr 2", "Yr 3", "Yr 4", "Yr 5"],
            title="",
        ),
        yaxis=dict(title="Cumulative cost ($)", tickprefix="$"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=20, r=20, t=40, b=40),
    )

    st.plotly_chart(fig_line, use_container_width=True)

    st.markdown('<div style="margin:1.5rem 0 0.4rem 0;border-top:1px solid #e2ddd9;"></div>', unsafe_allow_html=True)

    # ── CHART 2: Three-scenario stacked bar ──
    st.markdown(
        '<div style="font-size:0.95rem;font-weight:600;color:#444;margin-bottom:0.2rem;">Total exposure by scenario — investment vs. avoidable cost</div>',
        unsafe_allow_html=True,
    )

    bar_rows = []
    for _yrs, _cost in [(1, _c1), (3, _c3), (5, _c5)]:
        lbl = f"Wait {_yrs} yr" if _yrs == 1 else f"Wait {_yrs} yrs"
        bar_rows += [
            {"Scenario": lbl, "Segment": "Investment", "Value": investment_amount},
            {"Scenario": lbl, "Segment": "Avoidable cost of delay", "Value": _cost},
        ]
    bar_df = pd.DataFrame(bar_rows)

    fig_bars = px.bar(
        bar_df,
        x="Scenario",
        y="Value",
        color="Segment",
        barmode="stack",
        category_orders={"Scenario": ["Wait 1 yr", "Wait 3 yrs", "Wait 5 yrs"]},
        color_discrete_map={"Investment": FOREST, "Avoidable cost of delay": "#E67E22"},
    )
    fig_bars.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>%{x}: $%{y:,.0f}<extra></extra>",
    )

    for _yrs, _cost in [(1, _c1), (3, _c3), (5, _c5)]:
        lbl = f"Wait {_yrs} yr" if _yrs == 1 else f"Wait {_yrs} yrs"
        fig_bars.add_annotation(
            x=lbl, y=investment_amount + _cost,
            text=f"<b>{money(_cost)}</b> avoidable",
            showarrow=False, yshift=16,
            font=dict(size=13, color=INK, family=PLOTLY_FONT),
        )

    fig_bars.update_layout(
        height=380,
        xaxis_title="",
        yaxis_title="Total cost exposure ($)",
        yaxis_tickprefix="$",
        legend_title_text="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=20, r=20, t=40, b=40),
    )

    st.plotly_chart(fig_bars, use_container_width=True)

    st.markdown(
        f"""
        <div class="takeaway-box">
            Every year of delay widens the gap. The {money(investment_amount)} investment is the same
            regardless of when it happens — the orange bar is the additional cost borne by
            low-income workers while the city waits. At 5 years that's
            <b>{money(_c5)}</b> in avoidable economic harm, or
            <b>${_pr5:,.0f} per resident</b>.
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
# Tab 5: What's Compounding
# --------------------------------
with tab_cost:

    st.markdown(
        '<div class="section-title">What\'s Compounding — Year-by-Year Cost of Inaction</div>',
        unsafe_allow_html=True,
    )

    # Distinct, readable colors — no two look the same
    component_columns = {
        "Lost wages":           "lost_wages_annual",
        "Healthcare":           "healthcare_annual",
        "Environment":          "environment_annual",
        "Education":            "education_annual",
        "Forgone affordability":"forgone_affordability_annual",
    }
    component_colors = {
        "Lost wages":            "#2C5F6E",   # dark teal
        "Healthcare":            "#C0392B",   # red
        "Environment":           "#27AE60",   # green
        "Education":             "#8E44AD",   # purple
        "Forgone affordability": "#E67E22",   # amber
    }
    component_rates = {
        "Lost wages":            0.035,
        "Healthcare":            0.045,
        "Environment":           _growth_rate,
        "Education":             0.012,
        "Forgone affordability": 0.03,
    }

    available_components = {
        label: col for label, col in component_columns.items()
        if col in filtered_df.columns
    }

    # Build year-by-year rows (years 1-5, cumulative)
    area_rows = []
    for year in range(1, 6):
        for label, col in available_components.items():
            rate = component_rates[label]
            # Cumulative = sum of year 1 .. year N for this component
            cum_value = sum(
                filtered_df[col].sum() * (1 + rate) ** y
                for y in range(1, year + 1)
            )
            area_rows.append({
                "Year": f"Year {year}",
                "Year_num": year,
                "Component": label,
                "Cumulative Cost": cum_value,
            })

    area_df = pd.DataFrame(area_rows)
    total_by_year = area_df.groupby("Year_num")["Cumulative Cost"].sum().reset_index()

    fig_area = px.area(
        area_df,
        x="Year_num",
        y="Cumulative Cost",
        color="Component",
        color_discrete_map=component_colors,
        category_orders={"Component": list(available_components.keys())},
        labels={"Year_num": "Year of delay", "Cumulative Cost": "Cumulative cost ($)"},
        title="Cumulative cost of inaction — compounding year by year",
    )

    fig_area.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>Year %{x}: $%{y:,.0f}<extra></extra>",
    )

    # Annotate the year 5 total
    y5_total = total_by_year[total_by_year["Year_num"] == 5]["Cumulative Cost"].sum()
    fig_area.add_annotation(
        x=5, y=y5_total,
        text=f"<b>{money(y5_total)}</b> after 5 years",
        showarrow=True, arrowhead=2, arrowcolor=INK,
        ax=-80, ay=-40,
        font=dict(size=13, color=INK, family=PLOTLY_FONT),
    )

    fig_area.update_layout(
        height=500,
        xaxis=dict(tickmode="array", tickvals=[1,2,3,4,5],
                   ticktext=["Year 1","Year 2","Year 3","Year 4","Year 5"]),
        yaxis_title="Cumulative cost of delay ($)",
        yaxis_tickprefix="$",
        legend_title_text="Cost component",
        margin=dict(l=20, r=20, t=60, b=40),
    )

    st.plotly_chart(fig_area, use_container_width=True)

    # Dynamic insight line
    largest_component = (
        max({l: filtered_df[c].sum() for l, c in available_components.items()},
            key=lambda k: filtered_df[available_components[k]].sum())
        if available_components else "Lost wages"
    )
    largest_share = (
        filtered_df[available_components[largest_component]].sum()
        / filtered_df[[c for c in available_components.values()]].sum().sum()
        if available_components else 0
    )

    st.markdown(
        f"""
        <div class="takeaway-box">
            <b>Compounding insight:</b> Each year of delay adds to the total — costs don't
            stay flat, they grow. After {delay_years} {"year" if delay_years == 1 else "years"},
            cumulative exposure reaches <b>{money(delay_cost)}</b>.
            <b>{largest_component}</b> is the largest driver at <b>{largest_share:.0%}</b>
            of the annual base — five visible components, not a black-box score.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Stacked area = cumulative cost from year 1 onward. Each band grows at its own rate: "
        "wages at 3.5%, healthcare at 4.5%, education at 1.2%, environment and affordability "
        f"at your selected {growth_rate_pct}% growth rate."
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

    # Fixed Y-axis ceiling — always based on 5-year max so bars grow visually
    # when switching 1yr → 3yr → 5yr instead of rescaling each time.
    _equity_5yr = filtered_df.groupby("vulnerability_segment")["cumulative_delay_5yr_cost"].sum() \
        if "cumulative_delay_5yr_cost" in filtered_df.columns else equity_df["delay_cost"]
    _y_max_total = _equity_5yr.max() * 1.25 if len(_equity_5yr) > 0 else equity_df["delay_cost"].max() * 1.25

    _pop_by_seg = filtered_df.groupby("vulnerability_segment")["total_population"].sum()
    _5yr_per_cap = (_equity_5yr / _pop_by_seg).dropna()
    _y_max_pc = _5yr_per_cap.max() * 1.25 if len(_5yr_per_cap) > 0 else equity_df["delay_cost_per_capita"].max() * 1.25

    # Segment colour map — consistent with map and triage tabs
    _seg_colors = {
        "High-need transit burden":   FOREST,
        "Moderate hardship":          CLAY,
        "Lower-risk, better-served":  TAUPE,
    }
    equity_df["_color"] = equity_df["vulnerability_segment"].map(
        lambda s: _seg_colors.get(s, TAUPE)
    )

    # ── Headline stat cards ──────────────────────────────────────────────────
    burdened_segments = equity_df[equity_df["population"] > 0].copy()
    highest_row = (
        burdened_segments.loc[burdened_segments["delay_cost_per_capita"].idxmax()]
        if not burdened_segments.empty else None
    )

    if highest_row is not None:
        _pos = burdened_segments[burdened_segments["delay_cost_per_capita"] > 0]["delay_cost_per_capita"]
        _multiplier = (highest_row["delay_cost_per_capita"] / _pos.min()) if len(_pos) > 1 and _pos.min() > 0 else None
        _income = highest_row.get("avg_median_income", None)
        _vehicle = highest_row.get("avg_pct_no_vehicle", None)

        _stat2 = f"{_multiplier:.1f}x the burden of the least-affected segment" if _multiplier and _multiplier >= 1.1 else "highest per-resident burden"
        _stat3 = f"Avg household income in this segment: {money(_income)}" if pd.notna(_income) else ""
        _stat4 = f"{_vehicle:.0%} of workers have no vehicle" if _vehicle is not None and pd.notna(_vehicle) else ""

        st.markdown(
            f"""
            <div style="display:flex;gap:1rem;margin:0.5rem 0 1.25rem 0;">
                <div style="flex:1.2;background:#fff;border:1px solid #e2ddd9;border-left:4px solid #C0392B;border-radius:10px;padding:1rem 1.2rem;">
                    <div style="font-size:0.72rem;color:#888;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Highest-burden segment</div>
                    <div style="font-size:1.5rem;font-weight:700;color:{FOREST};">{highest_row['vulnerability_segment']}</div>
                    <div style="font-size:0.82rem;color:#555;margin-top:4px;">{_stat2}</div>
                </div>
                <div style="flex:1;background:#fff;border:1px solid #e2ddd9;border-left:4px solid #C0392B;border-radius:10px;padding:1rem 1.2rem;">
                    <div style="font-size:0.72rem;color:#888;text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">Cost per resident · {delay_years}-yr delay</div>
                    <div style="font-size:1.8rem;font-weight:700;color:#C0392B;">{money(highest_row['delay_cost_per_capita'])}</div>
                    <div style="font-size:0.82rem;color:#555;margin-top:4px;">{_stat3}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Two charts, consistent ordering and colours ──────────────────────────
    left, right = st.columns(2)

    with left:
        # Sort by delay_cost descending — consistent segment order across both charts
        cost_df = equity_df.sort_values("delay_cost", ascending=False)
        fig_equity_cost = px.bar(
            cost_df,
            x="vulnerability_segment",
            y="delay_cost",
            text="delay_cost",
            title=f"Total {delay_years}-year delay cost by segment",
            color="vulnerability_segment",
            color_discrete_map=_seg_colors,
            hover_data={"tracts": True, "population": ":,.0f", "avg_hardship": ":.1f", "delay_cost": ":,.0f"},
        )
        fig_equity_cost.update_traces(texttemplate="$%{text:,.3s}", textposition="outside")
        fig_equity_cost.update_layout(
            height=420, xaxis_title="", yaxis_title=f"{delay_years}-yr delay cost ($)",
            yaxis_tickprefix="$", showlegend=False,
            yaxis_range=[0, _y_max_total],
            margin=dict(l=20, r=40, t=30, b=80),
        )
        st.plotly_chart(fig_equity_cost, use_container_width=True)
        st.caption("Total dollars exposed in each segment.")

    with right:
        # Sort per-capita descending — same segment order as left where possible
        per_capita_df = equity_df.sort_values("delay_cost", ascending=False)
        fig_equity_per_capita = px.bar(
            per_capita_df,
            x="vulnerability_segment",
            y="delay_cost_per_capita",
            text="delay_cost_per_capita",
            title=f"{delay_years}-year delay cost per resident",
            color="vulnerability_segment",
            color_discrete_map=_seg_colors,
            hover_data={"tracts": True, "population": ":,.0f", "avg_hardship": ":.1f", "delay_cost_per_capita": ":,.0f"},
        )
        fig_equity_per_capita.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        fig_equity_per_capita.update_layout(
            height=420, xaxis_title="", yaxis_title="Cost per resident ($)",
            yaxis_tickprefix="$", showlegend=False,
            yaxis_range=[0, _y_max_pc],
            margin=dict(l=20, r=40, t=30, b=80),
        )
        st.plotly_chart(fig_equity_per_capita, use_container_width=True)
        st.caption("Same dollars — but who actually carries it per person.")

    st.caption(
        "Note: this equity lens is built from income, vehicle access, and transit dependency — "
        "not race or ethnicity, which are not in the underlying Census data. "
        "Pair with local demographic context before drawing conclusions about specific communities."
    )

    equity_table = equity_df.drop(columns=["_color"], errors="ignore").copy()

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
# Tab 6: Responsible AI
# --------------------------------
with tab_responsible_ai:
    st.markdown(
        '<div class="section-title">🧭 Responsible AI — When TransitIQ Gets It Wrong</div>',
        unsafe_allow_html=True,
    )

    # ── 3 Failure Mode Cards ──
    st.markdown(
        """
        <div style="display:flex;gap:1rem;margin:1.2rem 0;">

          <!-- Failure 1: Displacement Paradox -->
          <div style="flex:1;background:#fff;border:1px solid #e2ddd9;border-radius:12px;padding:1.2rem 1.4rem;border-top:4px solid #C0392B;">
            <div style="font-size:1rem;font-weight:700;color:#1a1a1a;margin-bottom:8px;">The Displacement Paradox</div>
            <div style="font-size:0.85rem;color:#444;line-height:1.55;margin-bottom:10px;">
              TransitIQ flags a tract as high-need → city invests → rents rise → the residents it was built to help get priced out.
            </div>
            <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;color:#888;margin-bottom:4px;">Who gets harmed</div>
            <div style="font-size:0.85rem;color:#444;margin-bottom:10px;">Transit-dependent renters in the funded tract.</div>
            <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;color:#27AE60;margin-bottom:4px;">Design response</div>
            <div style="font-size:0.85rem;color:#444;">
              Displacement warning fires on <b>every</b> scenario before any recommendation is shown. High-displacement tracts are flagged in the triage table.
            </div>
          </div>

          <!-- Failure 2: Suppressed Data -->
          <div style="flex:1;background:#fff;border:1px solid #e2ddd9;border-radius:12px;padding:1.2rem 1.4rem;border-top:4px solid #E67E22;">
            <div style="font-size:1rem;font-weight:700;color:#1a1a1a;margin-bottom:8px;">Suppressed Data → Wrong Tract</div>
            <div style="font-size:0.85rem;color:#444;line-height:1.55;margin-bottom:10px;">
              Small-population tracts have suppressed ACS values. TransitIQ may score them high-priority using incomplete data, misdirecting funding from genuinely high-need areas.
            </div>
            <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;color:#888;margin-bottom:4px;">Who gets harmed</div>
            <div style="font-size:0.85rem;color:#444;margin-bottom:10px;">Residents of the high-need tract that loses out on funding.</div>
            <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;color:#27AE60;margin-bottom:4px;">Design response</div>
            <div style="font-size:0.85rem;color:#444;">
              Assumptions are live in the sidebar for stress-testing. Per-tract data-quality flagging is a known gap and will be implemented in a future version.
            </div>
          </div>

          <!-- Failure 3: Cluster Flip -->
          <div style="flex:1;background:#fff;border:1px solid #e2ddd9;border-radius:12px;padding:1.2rem 1.4rem;border-top:4px solid #8E44AD;">
            <div style="font-size:1rem;font-weight:700;color:#1a1a1a;margin-bottom:8px;">The Borderline Tract Problem</div>
            <div style="font-size:0.85rem;color:#444;line-height:1.55;margin-bottom:10px;">
              A tract near a cluster boundary can flip from "High-need" to "Moderate" with a small data update, dropping off the investment shortlist entirely.
            </div>
            <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;color:#888;margin-bottom:4px;">Who gets harmed</div>
            <div style="font-size:0.85rem;color:#444;margin-bottom:10px;">Residents of borderline tracts whose segment assignment is unstable.</div>
            <div style="font-size:0.72rem;font-weight:700;text-transform:uppercase;color:#27AE60;margin-bottom:4px;">Design response</div>
            <div style="font-size:0.85rem;color:#444;">
              Priority Score blends hardship index and per-capita delay cost equally, so a segment flip doesn't auto-remove a tract. Raw scores shown alongside labels.
            </div>
          </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Uncertainty band ──
    st.markdown(
        '<div class="section-title" style="margin-top:1.5rem;">Model Uncertainty — A Range, Not a Prediction</div>',
        unsafe_allow_html=True,
    )

    uncertainty_pct_by_horizon = {1: 0.10, 3: 0.15, 5: 0.20}
    uncertainty_pct = uncertainty_pct_by_horizon.get(delay_years, 0.15)
    _unc_low  = delay_cost * (1 - uncertainty_pct)
    _unc_high = delay_cost * (1 + uncertainty_pct)

    st.markdown(
        f"""
        <div style="background:#fff;border:1px solid #e2ddd9;border-radius:12px;padding:1.2rem 1.6rem;margin-bottom:1rem;">
            <div style="display:flex;gap:2rem;align-items:center;">
                <div style="text-align:center;flex:1;">
                    <div style="font-size:0.7rem;color:#888;text-transform:uppercase;letter-spacing:.06em;">Low estimate (−{uncertainty_pct:.0%})</div>
                    <div style="font-size:1.5rem;font-weight:700;color:{TAUPE};">{money(_unc_low)}</div>
                </div>
                <div style="text-align:center;flex:1;border-left:1px solid #e2ddd9;border-right:1px solid #e2ddd9;padding:0 1rem;">
                    <div style="font-size:0.7rem;color:#888;text-transform:uppercase;letter-spacing:.06em;">Base estimate</div>
                    <div style="font-size:1.8rem;font-weight:700;color:{FOREST};">{money(delay_cost)}</div>
                    <div style="font-size:0.75rem;color:#999;">current model output</div>
                </div>
                <div style="text-align:center;flex:1;">
                    <div style="font-size:0.7rem;color:#888;text-transform:uppercase;letter-spacing:.06em;">High estimate (+{uncertainty_pct:.0%})</div>
                    <div style="font-size:1.5rem;font-weight:700;color:#C0392B;">{money(_unc_high)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        f"Uncertainty band widens with the forecast horizon — ±{uncertainty_pct:.0%} for a "
        f"{delay_years}-year projection. This is a simplified sensitivity range, not a statistical "
        "confidence interval. Its purpose: show planners a plausible range instead of a false-precision single number."
    )

    # ── Data sources ──
    st.markdown(
        """
        <div style="background:#fff;border:1px solid #e2ddd9;border-radius:10px;padding:0.9rem 1.2rem;margin:1.2rem 0 0.5rem 0;font-size:0.85rem;color:#555;line-height:1.8;">
            <span style="font-weight:700;color:#1a1a1a;">Data sources: </span>
            ACS 2019–2023 5-Year Estimates &nbsp;·&nbsp;
            BLS OEWS 2024 (Columbus MSA) &nbsp;·&nbsp;
            COTA GTFS 2025 &nbsp;·&nbsp;
            NHTSA FARS 2023 &nbsp;·&nbsp;
            LEHD LODES 2021 &nbsp;·&nbsp;
            EPA Social Cost of Carbon 2023 &nbsp;·&nbsp;
            Urban Institute (missed care rate baseline) &nbsp;·&nbsp;
            H+T Affordability Index (CNT)
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Assumptions table ──
    st.markdown(
        '<div class="section-title" style="margin-top:1.5rem;">Core Model Assumptions</div>',
        unsafe_allow_html=True,
    )

    assumptions_df = pd.DataFrame({
        "Model area": [
            "Transit hardship index",
            "Cost components",
            "Compounding rates",
            "Uncertainty band",
            "Vulnerability segments",
            "Displacement overlay",
        ],
        "Assumption": [
            "Higher score = more transit burden + socioeconomic vulnerability. Weighted composite of 5 ACS/GTFS inputs.",
            "Annual cost = lost wages + healthcare + environment + education + forgone affordability. Each sourced independently (BLS, Urban Institute, EPA).",
            "Wages 3.5%, healthcare 4.5%, education 1.2%, environment and affordability use your selected growth rate slider.",
            "±10% at 1 year, ±15% at 3 years, ±20% at 5 years. Wider band = more honest at longer horizons.",
            "K-means (3 clusters) on hardship index. Borderline tracts may shift with data updates — raw scores shown alongside labels.",
            "Displacement risk is a proxy indicator, not a prediction. Requires separate community and legal review before acting on it.",
        ],
        "What we'd need to tighten it": [
            "Longitudinal ridership data; COTA OD matrices.",
            "Local healthcare cost data; tract-level wage surveys.",
            "CPI sub-index by cost category; local rent trend data.",
            "Monte Carlo simulation with per-variable distributions.",
            "Soft-clustering (fuzzy c-means) to surface borderline confidence.",
            "Parcel-level rent change data; community-based review process.",
        ],
    })

    # Render as HTML table so text wraps naturally
    _rows_html = ""
    for _, row in assumptions_df.iterrows():
        _rows_html += f"""
        <tr>
            <td style="padding:10px 14px;font-weight:600;color:#1a1a1a;white-space:nowrap;vertical-align:top;border-bottom:1px solid #e2ddd9;">{row['Model area']}</td>
            <td style="padding:10px 14px;color:#444;line-height:1.5;vertical-align:top;border-bottom:1px solid #e2ddd9;">{row['Assumption']}</td>
            <td style="padding:10px 14px;color:#666;line-height:1.5;vertical-align:top;border-bottom:1px solid #e2ddd9;">{row["What we'd need to tighten it"]}</td>
        </tr>"""

    st.markdown(
        f"""
        <table style="width:100%;border-collapse:collapse;font-size:0.85rem;background:#fff;border:1px solid #e2ddd9;border-radius:8px;overflow:hidden;">
            <thead>
                <tr style="background:#f5f2ef;">
                    <th style="padding:10px 14px;text-align:left;color:#888;font-size:0.72rem;text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid #e2ddd9;white-space:nowrap;">Model area</th>
                    <th style="padding:10px 14px;text-align:left;color:#888;font-size:0.72rem;text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid #e2ddd9;">Assumption</th>
                    <th style="padding:10px 14px;text-align:left;color:#888;font-size:0.72rem;text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid #e2ddd9;">What we'd need to tighten it</th>
                </tr>
            </thead>
            <tbody>{_rows_html}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )

# --------------------------------
# Tab 3: Where to Invest First
# --------------------------------
with tab_tracts:
    st.markdown(
        '<div class="section-title">🎯 Where to Invest First — Priority Triage</div>',
        unsafe_allow_html=True,
    )

    # Build the working dataframe with raw numbers first
    triage_cols = [
        "GEOID", "tract_label", "transit_hardship_index",
        "vulnerability_segment", "cost_of_inaction_annual",
        delay_col, "total_population",
    ]
    triage_cols = [c for c in triage_cols if c in filtered_df.columns]

    triage_df = (
        filtered_df[triage_cols]
        .sort_values("transit_hardship_index", ascending=False)
        .head(20)
        .copy()
        .reset_index(drop=True)
    )
    triage_df.index = triage_df.index + 1  # Rank starts at 1

    # Compute priority score: equal weight on normalised hardship + normalised per-capita cost
    triage_df["delay_cost_per_resident"] = (
        triage_df[delay_col] / triage_df["total_population"].replace(0, pd.NA)
    ).fillna(0)

    hi_min, hi_max = triage_df["transit_hardship_index"].min(), triage_df["transit_hardship_index"].max()
    pc_min, pc_max = triage_df["delay_cost_per_resident"].min(), triage_df["delay_cost_per_resident"].max()

    triage_df["_norm_hi"] = (triage_df["transit_hardship_index"] - hi_min) / (hi_max - hi_min + 1e-9)
    triage_df["_norm_pc"] = (triage_df["delay_cost_per_resident"] - pc_min) / (pc_max - pc_min + 1e-9)
    triage_df["priority_score"] = ((triage_df["_norm_hi"] + triage_df["_norm_pc"]) / 2 * 100).round(1)

    # ── Bar chart: top 10 by delay cost per resident ──────────────────────
    chart_df = triage_df.nlargest(10, "delay_cost_per_resident").sort_values(
        "delay_cost_per_resident", ascending=True
    )
    segment_colors = {
        "High-need transit burden": FOREST,
        "Moderate hardship": CLAY,
        "Lower-risk, better-served": TAUPE,
    }
    chart_df["color"] = chart_df["vulnerability_segment"].map(segment_colors).fillna(TAUPE)
    chart_df["label"] = chart_df["delay_cost_per_resident"].apply(lambda x: f"${x:,.0f}")

    fig_triage = px.bar(
        chart_df,
        x="delay_cost_per_resident",
        y="tract_label",
        orientation="h",
        text="label",
        title=f"Top 10 tracts — {delay_years}-year delay cost per resident",
        color="vulnerability_segment",
        color_discrete_map=segment_colors,
    )
    fig_triage.update_traces(
        textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Delay cost per resident: $%{x:,.0f}<extra></extra>",
    )
    fig_triage.update_layout(
        height=400,
        xaxis_title="Delay cost per resident ($)",
        yaxis_title="",
        xaxis_tickprefix="$",
        legend_title_text="Segment",
        margin=dict(l=10, r=120, t=60, b=20),
        showlegend=True,
    )
    st.plotly_chart(fig_triage, use_container_width=True)

    # ── Top 3 recommendation callout ──────────────────────────────────────
    top3 = triage_df.nlargest(3, "priority_score").reset_index(drop=True)
    _cards = ""
    for rank, row in top3.iterrows():
        _cards += f"""
        <div style="flex:1;background:#fff;border:1px solid #e2ddd9;border-top:4px solid {FOREST};border-radius:10px;padding:1rem 1.2rem;">
            <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#888;margin-bottom:4px;">#{rank+1} Priority</div>
            <div style="font-size:1rem;font-weight:700;color:{FOREST};margin-bottom:8px;">{row["tract_label"]}</div>
            <div style="font-size:0.82rem;color:#555;line-height:1.7;">
                Priority score: <b>{row["priority_score"]:.0f}/100</b><br>
                Hardship index: <b>{row["transit_hardship_index"]:.1f}</b><br>
                Cost per resident: <b>{money(row["delay_cost_per_resident"])}</b> over {delay_years} yr
            </div>
        </div>"""
    st.markdown(
        f"""
        <div style="margin-top:0.75rem 0 0.25rem 0;">
            <div style="font-size:0.9rem;font-weight:600;color:#444;margin-bottom:0.6rem;">Top investment priorities — highest combined hardship and per-resident delay cost</div>
            <div style="display:flex;gap:1rem;">{_cards}</div>
            <div style="font-size:0.78rem;color:#999;margin-top:8px;">Cross-reference displacement risk before committing funding.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-title" style="margin-top:1.5rem;">Full Priority Table — Top 20 Tracts</div>',
        unsafe_allow_html=True,
    )

    # Format for display
    display_df = triage_df.copy()
    display_df["priority_score"] = display_df["priority_score"].apply(lambda x: f"{x:.0f}/100")
    display_df["transit_hardship_index"] = display_df["transit_hardship_index"].apply(lambda x: f"{x:.1f}")
    display_df["cost_of_inaction_annual"] = display_df["cost_of_inaction_annual"].apply(money)
    display_df[delay_col] = display_df[delay_col].apply(money)
    display_df["delay_cost_per_resident"] = display_df["delay_cost_per_resident"].apply(lambda x: f"${x:,.0f}")
    display_df["total_population"] = display_df["total_population"].apply(lambda x: f"{x:,.0f}")

    display_df = display_df.rename(columns={
        "tract_label": "Tract",
        "transit_hardship_index": "Hardship Index",
        "vulnerability_segment": "Segment",
        "cost_of_inaction_annual": "Annual Cost",
        delay_col: f"{delay_years}-Yr Delay Cost",
        "delay_cost_per_resident": "Cost / Resident",
        "total_population": "Population",
        "priority_score": "Priority Score",
        "GEOID": "GEOID",
    })

    col_order = [
        "Tract", "Priority Score", "Hardship Index", "Segment",
        "Annual Cost", f"{delay_years}-Yr Delay Cost", "Cost / Resident",
        "Population", "GEOID",
    ]
    display_df = display_df[[c for c in col_order if c in display_df.columns]]

    st.dataframe(display_df, use_container_width=True, hide_index=False)

    st.caption(
        "Priority Score = equal-weighted blend of Transit Hardship Index and delay cost per resident, "
        "both normalised to 0–100. Sort by Priority Score or Cost / Resident to find your highest-impact targets."
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
