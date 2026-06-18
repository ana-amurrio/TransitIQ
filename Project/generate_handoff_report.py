"""
Generate the Processing Layer handoff PDF for the dashboard team.
Run from the Project/ directory:
    python3 generate_handoff_report.py
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)

OUT_PATH = Path(__file__).resolve().parent / "data" / "outputs" / "processing_layer_handoff.pdf"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Palette ──────────────────────────────────────────────────────────────────
NAVY    = colors.HexColor("#1a2e4a")
TEAL    = colors.HexColor("#1d7a8c")
AMBER   = colors.HexColor("#e8a020")
LIGHT   = colors.HexColor("#f0f4f8")
MID     = colors.HexColor("#dce6f0")
RED_HI  = colors.HexColor("#c0392b")
WHITE   = colors.white
BLACK   = colors.black

# ── Styles ────────────────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def S(name, parent="Normal", **kw):
    s = ParagraphStyle(name, parent=base[parent], **kw)
    return s

TITLE      = S("DocTitle",    "Title",    fontSize=26, textColor=NAVY,  spaceAfter=4, leading=30)
SUBTITLE   = S("DocSub",      "Normal",   fontSize=11, textColor=TEAL,  spaceAfter=2)
DATE_LINE  = S("DateLine",    "Normal",   fontSize=9,  textColor=colors.HexColor("#666666"), spaceAfter=16)
H1         = S("H1",          "Heading1", fontSize=14, textColor=WHITE,  spaceAfter=6, leading=18)
H2         = S("H2",          "Heading2", fontSize=11, textColor=NAVY,   spaceBefore=10, spaceAfter=4)
BODY       = S("Body",        "Normal",   fontSize=9,  leading=14,       spaceAfter=4)
BODY_SMALL = S("BodySm",      "Normal",   fontSize=8,  leading=12,       spaceAfter=3, textColor=colors.HexColor("#333333"))
BOLD_BODY  = S("BoldBody",    "Normal",   fontSize=9,  leading=14,       spaceAfter=4, fontName="Helvetica-Bold")
CODE       = S("Code",        "Code",     fontSize=8,  leading=12,       backColor=LIGHT, borderPadding=4)
BULLET     = S("Bullet",      "Normal",   fontSize=9,  leading=13,       spaceAfter=2, leftIndent=14, bulletIndent=4)
CAPTION    = S("Caption",     "Normal",   fontSize=8,  textColor=colors.HexColor("#555555"), spaceAfter=6, fontName="Helvetica-Oblique")
WARNING    = S("Warning",     "Normal",   fontSize=8.5, textColor=RED_HI, spaceAfter=4, fontName="Helvetica-Bold")

def hr(): return HRFlowable(width="100%", thickness=1, color=MID, spaceAfter=8, spaceBefore=4)

def section_header(text):
    """Colored section banner."""
    data = [[Paragraph(text, H1)]]
    t = Table(data, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    return t

def kv_table(rows, col1=2.5*inch, col2=4.0*inch):
    """Two-column key/value table."""
    data = [[Paragraph(k, BOLD_BODY), Paragraph(v, BODY)] for k, v in rows]
    t = Table(data, colWidths=[col1, col2])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), LIGHT),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("GRID",          (0,0), (-1,-1), 0.5, MID),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [WHITE, LIGHT]),
    ]))
    return t

def data_table(header_row, rows, col_widths=None):
    data = [header_row] + rows
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), TEAL),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0), 8),
        ("FONTSIZE",      (0,1), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT]),
        ("GRID",          (0,0), (-1,-1), 0.4, MID),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("ALIGN",         (1,1), (-1,-1), "RIGHT"),
    ]))
    return t

def highlight_box(text, bg=LIGHT, border=TEAL):
    data = [[Paragraph(text, BODY)]]
    t = Table(data, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("RIGHTPADDING",  (0,0), (-1,-1), 10),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("BOX",           (0,0), (-1,-1), 1.5, border),
    ]))
    return t


def build():
    doc = SimpleDocTemplate(
        str(OUT_PATH),
        pagesize=letter,
        leftMargin=0.85*inch, rightMargin=0.85*inch,
        topMargin=0.85*inch,  bottomMargin=0.85*inch,
        title="TransitIQ Processing Layer — Handoff Report",
        author="TransitIQ USAII Team",
    )
    story = []

    # ── COVER ─────────────────────────────────────────────────────────────────
    story += [
        Spacer(1, 0.3*inch),
        Paragraph("TransitIQ", TITLE),
        Paragraph("Processing Layer — Implementation Handoff", SUBTITLE),
        Paragraph("USAII Hackathon 2026 · Graduate Track · Brief 6A · Columbus, OH", DATE_LINE),
        hr(),
        highlight_box(
            "<b>Purpose of this document:</b> Complete handoff from the Processing Layer "
            "to the Dashboard team. Covers what was built, how it works, what every output "
            "file contains, the assumptions behind the numbers, and exactly what the "
            "dashboard needs to consume."
        ),
        Spacer(1, 0.2*inch),
    ]

    # ── 1. ARCHITECTURE POSITION ──────────────────────────────────────────────
    story += [
        section_header("1.  Where the Processing Layer Sits"),
        Spacer(1, 8),
        Paragraph(
            "TransitIQ has five layers. The Processing Layer sits between the cached "
            "data files and the Cost of Inaction Engine, and produces the tract-level "
            "scores and cost estimates that the dashboard renders.", BODY),
        Spacer(1, 6),
        data_table(
            [Paragraph("Layer", BOLD_BODY), Paragraph("Status", BOLD_BODY), Paragraph("Owner", BOLD_BODY)],
            [
                [Paragraph("1. Data Layer", BODY),       Paragraph("Complete", BODY), Paragraph("collect_*.py scripts", BODY_SMALL)],
                [Paragraph("2. Processing Layer", BODY), Paragraph("<b>Complete — this doc</b>", BOLD_BODY), Paragraph("process_transit_iq.py", BODY_SMALL)],
                [Paragraph("3. Cost of Inaction Engine", BODY), Paragraph("Embedded in Processing Layer", BODY), Paragraph("process_transit_iq.py", BODY_SMALL)],
                [Paragraph("4. Decision Layer", BODY),   Paragraph("Dashboard (next)", BODY), Paragraph("Streamlit app", BODY_SMALL)],
                [Paragraph("5. Dashboard", BODY),        Paragraph("To build", BODY), Paragraph("Streamlit app", BODY_SMALL)],
            ],
            col_widths=[2.0*inch, 2.0*inch, 2.5*inch],
        ),
        Spacer(1, 0.15*inch),
    ]

    # ── 2. SCOPE ──────────────────────────────────────────────────────────────
    story += [
        section_header("2.  Scope"),
        Spacer(1, 8),
        kv_table([
            ("Geography",      "Franklin County, Ohio (Columbus metro). FIPS 39-049."),
            ("Census tracts",  "328 tracts covering all of Franklin County."),
            ("Population",     "1,333,048 residents (ACS 2019-2023 5-year estimates)."),
            ("Data vintage",   "ACS 2019-2023 5-yr · LODES 2021 · FARS 2023 · BLS OEWS 2024 · COTA GTFS 2025"),
            ("Run date",       "June 2026"),
        ]),
        Spacer(1, 0.15*inch),
    ]

    # ── 3. HOW TO RUN ─────────────────────────────────────────────────────────
    story += [
        section_header("3.  How to Run"),
        Spacer(1, 8),
        Paragraph("From the <b>Project/</b> directory:", BODY),
        Spacer(1, 4),
        highlight_box(
            "python3 process_transit_iq.py<br/><br/>"
            "# With custom assumptions:<br/>"
            "python3 process_transit_iq.py \\ <br/>"
            "&nbsp;&nbsp;--missed-care-rate 0.08 \\ <br/>"
            "&nbsp;&nbsp;--cost-per-missed-episode 1500 \\ <br/>"
            "&nbsp;&nbsp;--growth-rate 0.03 \\ <br/>"
            "&nbsp;&nbsp;--average-commute-distance-miles 8",
            bg=colors.HexColor("#1a2e4a"), border=TEAL,
        ),
        Spacer(1, 6),
        Paragraph(
            "The script reads <b>data/outputs/master_tract_data.csv</b> (produced by "
            "create_master.py) and writes seven output files. It has no external API "
            "calls — all computation is local.", BODY),
        Spacer(1, 0.15*inch),
    ]

    # ── 4. OUTPUT FILES ───────────────────────────────────────────────────────
    story += [
        section_header("4.  Output Files"),
        Spacer(1, 8),
        data_table(
            [Paragraph("File", BOLD_BODY), Paragraph("Path", BOLD_BODY), Paragraph("Contents", BOLD_BODY)],
            [
                [Paragraph("processing_layer_results.csv", BODY_SMALL),
                 Paragraph("data/outputs/", BODY_SMALL),
                 Paragraph("Main dashboard feed — 24 columns per tract (see Section 6)", BODY_SMALL)],
                [Paragraph("processing_layer_summary.csv", BODY_SMALL),
                 Paragraph("data/outputs/", BODY_SMALL),
                 Paragraph("3-row segment rollup: tracts, population, avg hardship, costs", BODY_SMALL)],
                [Paragraph("processing_layer_metadata.json", BODY_SMALL),
                 Paragraph("data/outputs/", BODY_SMALL),
                 Paragraph("Assumptions, data quality notes, output paths", BODY_SMALL)],
                [Paragraph("transit_dependency_weights.csv", BODY_SMALL),
                 Paragraph("data/processed/", BODY_SMALL),
                 Paragraph("Per-tract dependency score and multiplier weight", BODY_SMALL)],
                [Paragraph("transit_hardship_index.csv", BODY_SMALL),
                 Paragraph("data/processed/", BODY_SMALL),
                 Paragraph("Commute burden, income/access/rent vulnerability scores, THI", BODY_SMALL)],
                [Paragraph("vulnerability_segments.csv", BODY_SMALL),
                 Paragraph("data/processed/", BODY_SMALL),
                 Paragraph("K-means segment id (0-2) and label per tract", BODY_SMALL)],
                [Paragraph("cost_of_inaction_by_tract.csv", BODY_SMALL),
                 Paragraph("data/processed/", BODY_SMALL),
                 Paragraph("All 5 cost components + year 1-5 forecasts + overlay scores", BODY_SMALL)],
            ],
            col_widths=[2.2*inch, 1.4*inch, 2.9*inch],
        ),
        Spacer(1, 0.15*inch),
    ]

    # ── 5. KEY RESULTS ────────────────────────────────────────────────────────
    story += [
        section_header("5.  Key Results"),
        Spacer(1, 8),
        Paragraph("Cost of Inaction — Franklin County, Columbus OH", H2),
        data_table(
            [Paragraph("Metric", BOLD_BODY), Paragraph("Value", BOLD_BODY)],
            [
                [Paragraph("Annual cost of inaction", BODY),        Paragraph("$178,687,293", BOLD_BODY)],
                [Paragraph("Cumulative cost — 3-year delay", BODY), Paragraph("$569,213,353", BODY)],
                [Paragraph("Cumulative cost — 5-year delay", BODY), Paragraph("$978,083,431", BODY)],
                [Paragraph("Cost per resident per year", BODY),     Paragraph("~$134", BODY)],
            ],
            col_widths=[3.5*inch, 3.0*inch],
        ),
        Spacer(1, 10),
        Paragraph("Annual Cost by Component", H2),
        data_table(
            [Paragraph("Component", BOLD_BODY), Paragraph("Annual Cost", BOLD_BODY), Paragraph("Share", BOLD_BODY), Paragraph("Growth Rate", BOLD_BODY)],
            [
                [Paragraph("Forgone Affordability (H+T burden)", BODY), Paragraph("$130,523,315", BODY), Paragraph("73.0%", BODY), Paragraph("2.5%/yr", BODY)],
                [Paragraph("Lost Wages (commute time cost)",     BODY), Paragraph(" $19,177,224", BODY), Paragraph("10.7%", BODY), Paragraph("3.5%/yr (BLS)", BODY)],
                [Paragraph("Healthcare (missed care)",           BODY), Paragraph(" $10,752,181", BODY), Paragraph(" 6.0%", BODY), Paragraph("4.5%/yr", BODY)],
                [Paragraph("Education (attendance loss)",        BODY), Paragraph("  $8,886,359", BODY), Paragraph(" 5.0%", BODY), Paragraph("1.2%/yr (Census)", BODY)],
                [Paragraph("Environment (excess car VMT)",       BODY), Paragraph("  $9,348,215", BODY), Paragraph(" 5.2%", BODY), Paragraph("2.5%/yr", BODY)],
            ],
            col_widths=[2.8*inch, 1.5*inch, 0.8*inch, 1.4*inch],
        ),
        Spacer(1, 10),
        Paragraph("Vulnerability Segments (K-means, k=3)", H2),
        data_table(
            [Paragraph("Segment", BOLD_BODY), Paragraph("Tracts", BOLD_BODY),
             Paragraph("Population", BOLD_BODY), Paragraph("Avg Hardship", BOLD_BODY),
             Paragraph("Annual Cost", BOLD_BODY), Paragraph("5-yr Delay Cost", BOLD_BODY)],
            [
                [Paragraph("Lower-risk, better-served", BODY), Paragraph("48",  BODY),
                 Paragraph("202,751",  BODY), Paragraph("39.1", BODY),
                 Paragraph("$3.5M",  BODY), Paragraph("$18.9M",  BODY)],
                [Paragraph("Moderate hardship",          BODY), Paragraph("173", BODY),
                 Paragraph("760,811",  BODY), Paragraph("48.9", BODY),
                 Paragraph("$25.1M", BODY), Paragraph("$137.3M", BODY)],
                [Paragraph("High-need transit burden",   BODY), Paragraph("107", BODY),
                 Paragraph("369,486",  BODY), Paragraph("57.5", BODY),
                 Paragraph("$150.0M",BODY), Paragraph("$821.9M", BODY)],
            ],
            col_widths=[2.0*inch, 0.6*inch, 1.0*inch, 1.0*inch, 1.0*inch, 0.9*inch],
        ),
        Spacer(1, 0.1*inch),
        Paragraph(
            "89.8% of the annual cost is concentrated in the 151 High-need tracts "
            "(558,226 residents — 42% of the county population).", CAPTION),
        Spacer(1, 4),
        highlight_box(
            "<b>Clustering note for the dashboard team:</b> sklearn k-means++ (random_state=42, "
            "n_init=10) consistently produces a 2-tract 'Lower-risk' cluster regardless of seed. "
            "This reflects the real shape of the data — Franklin County has almost no "
            "well-served transit areas. This is a valid and compelling finding. "
            "If the map needs more balanced color distribution, consider supplementing "
            "with a continuous Transit Hardship Index choropleth rather than relying "
            "solely on the 3-segment classification.",
            bg=colors.HexColor("#fff8e1"), border=AMBER,
        ),
        Spacer(1, 0.15*inch),
    ]

    story.append(PageBreak())

    # ── 6. COLUMN REFERENCE ───────────────────────────────────────────────────
    story += [
        section_header("6.  Column Reference — processing_layer_results.csv"),
        Spacer(1, 8),
        Paragraph(
            "This is the primary file the dashboard should load. One row per census tract.", BODY),
        Spacer(1, 6),
        data_table(
            [Paragraph("Column", BOLD_BODY), Paragraph("Type", BOLD_BODY), Paragraph("Description", BOLD_BODY)],
            [
                [Paragraph("GEOID", BODY_SMALL),                          Paragraph("str(11)", BODY_SMALL), Paragraph("Census tract FIPS, zero-padded to 11 chars", BODY_SMALL)],
                [Paragraph("median_income", BODY_SMALL),                  Paragraph("float", BODY_SMALL),   Paragraph("ACS median household income (USD)", BODY_SMALL)],
                [Paragraph("total_population", BODY_SMALL),               Paragraph("int",   BODY_SMALL),   Paragraph("ACS total tract population", BODY_SMALL)],
                [Paragraph("total_households", BODY_SMALL),               Paragraph("int",   BODY_SMALL),   Paragraph("ACS total household count", BODY_SMALL)],
                [Paragraph("transit_score", BODY_SMALL),                  Paragraph("float", BODY_SMALL),   Paragraph("COTA GTFS-derived access score (0-1, higher = better served)", BODY_SMALL)],
                [Paragraph("is_transit_desert", BODY_SMALL),              Paragraph("bool",  BODY_SMALL),   Paragraph("True if transit_score = 0 (no stops in tract); 46 of 328 tracts", BODY_SMALL)],
                [Paragraph("transit_dependency_score", BODY_SMALL),       Paragraph("float", BODY_SMALL),   Paragraph("0-1 composite of no-vehicle, disability, elderly, single-parent rates", BODY_SMALL)],
                [Paragraph("transit_dependency_weight", BODY_SMALL),      Paragraph("float", BODY_SMALL),   Paragraph("1 + dependency_score; multiplier applied to cost components (range 1.0-1.71)", BODY_SMALL)],
                [Paragraph("transit_hardship_index", BODY_SMALL),         Paragraph("float", BODY_SMALL),   Paragraph("0-100 composite hardship score (mean 50.2, max 70.9)", BODY_SMALL)],
                [Paragraph("vulnerability_segment", BODY_SMALL),          Paragraph("str",   BODY_SMALL),   Paragraph("'Lower-risk, better-served' / 'Moderate hardship' / 'High-need transit burden'", BODY_SMALL)],
                [Paragraph("affected_workers_estimate", BODY_SMALL),      Paragraph("float", BODY_SMALL),   Paragraph("max(transit commuters, no-vehicle workers) — overlap-adjusted", BODY_SMALL)],
                [Paragraph("transit_dependent_pop_estimate", BODY_SMALL), Paragraph("float", BODY_SMALL),   Paragraph("max(no-vehicle hh population, transit commuters)", BODY_SMALL)],
                [Paragraph("forced_drive_commuters_estimate", BODY_SMALL),Paragraph("float", BODY_SMALL),   Paragraph("Non-transit commuters scaled by access gap — VMT basis", BODY_SMALL)],
                [Paragraph("ht_burdened_households_estimate", BODY_SMALL),Paragraph("float", BODY_SMALL),   Paragraph("max(rent-burdened hh, no-vehicle hh) — H+T affordability basis", BODY_SMALL)],
                [Paragraph("lost_wages_annual", BODY_SMALL),              Paragraph("float", BODY_SMALL),   Paragraph("USD: excess commute time x wage x affected workers", BODY_SMALL)],
                [Paragraph("healthcare_annual", BODY_SMALL),              Paragraph("float", BODY_SMALL),   Paragraph("USD: transit-dependent pop x missed-care rate x cost/episode", BODY_SMALL)],
                [Paragraph("environment_annual", BODY_SMALL),             Paragraph("float", BODY_SMALL),   Paragraph("USD: excess car VMT x EPA carbon price ($190/ton)", BODY_SMALL)],
                [Paragraph("education_annual", BODY_SMALL),               Paragraph("float", BODY_SMALL),   Paragraph("USD: annual school cohort in access-deficient tracts x earnings impact", BODY_SMALL)],
                [Paragraph("forgone_affordability_annual", BODY_SMALL),   Paragraph("float", BODY_SMALL),   Paragraph("USD: H+T-burdened hh x income x excess over 45% threshold", BODY_SMALL)],
                [Paragraph("cost_of_inaction_annual", BODY_SMALL),        Paragraph("float", BODY_SMALL),   Paragraph("USD: sum of all 5 components", BODY_SMALL)],
                [Paragraph("cumulative_delay_1yr_cost", BODY_SMALL),      Paragraph("float", BODY_SMALL),   Paragraph("USD: compounded total if investment delayed 1 year", BODY_SMALL)],
                [Paragraph("cumulative_delay_3yr_cost", BODY_SMALL),      Paragraph("float", BODY_SMALL),   Paragraph("USD: compounded total if investment delayed 3 years", BODY_SMALL)],
                [Paragraph("cumulative_delay_5yr_cost", BODY_SMALL),      Paragraph("float", BODY_SMALL),   Paragraph("USD: compounded total if investment delayed 5 years", BODY_SMALL)],
                [Paragraph("safety_warning_score", BODY_SMALL),           Paragraph("float", BODY_SMALL),   Paragraph("0-100: FARS crash density x dependency score — not summed into dollar cost", BODY_SMALL)],
                [Paragraph("displacement_risk_score", BODY_SMALL),        Paragraph("float", BODY_SMALL),   Paragraph("0-100: rent burden + income vulnerability + hardship — overlay only", BODY_SMALL)],
            ],
            col_widths=[2.2*inch, 0.75*inch, 3.55*inch],
        ),
        Spacer(1, 0.15*inch),
    ]

    # ── 7. CALCULATION NOTES ──────────────────────────────────────────────────
    story += [
        section_header("7.  Calculation Notes & Assumptions"),
        Spacer(1, 8),
        Paragraph("Transit Dependency Weight", H2),
        Paragraph(
            "Scales the affected-population term in every cost component so tracts "
            "with more transit-dependent residents register higher costs. "
            "Formula: <b>weight = 1 + normalized_sum(no_vehicle [50%] + disability [25%] + "
            "elderly_65+ [15%] + single_parent_hh [10%])</b>. "
            "Range: 1.00 to 1.71 (mean 1.25 across Franklin County tracts).", BODY),
        Spacer(1, 6),
        Paragraph("Overlap Adjustments", H2),
        Paragraph(
            "ACS groups overlap (a person can be both a transit commuter and a no-vehicle "
            "worker). All affected-population estimates use <b>max()</b> or <b>min()</b> "
            "proxies rather than addition to avoid double-counting. See metadata.json for "
            "the full overlap_adjustment note.", BODY),
        Spacer(1, 6),
        Paragraph("Forecasting Method", H2),
        Paragraph(
            "Each cost component compounds at its own rate — not a single blended rate. "
            "Lost wages use BLS wage inflation (3.5%/yr); healthcare uses 4.5%/yr; "
            "education uses Census population growth (1.2%/yr); environment and "
            "affordability use the blended rate (2.5%/yr).", BODY),
        Spacer(1, 6),
        Paragraph("Education Component", H2),
        Paragraph(
            "Annual framing: each year of inaction permanently affects one new entering "
            "school cohort (school_age_pop / 13). Applied only to tracts where "
            "transit_access_gap_score &gt; 0.5 (meaningfully access-deficient). "
            "Coefficient: 3% attendance loss (Chetty proxy) x $14,000 discounted "
            "lifetime earnings impact (Opportunity Insights).", BODY),
        Spacer(1, 6),
        Paragraph("Adjustable Assumptions (CLI flags)", H2),
        kv_table([
            ("--missed-care-rate",              "Default 0.05 (5%). Urban Institute baseline; rises to 0.20 for no-vehicle households."),
            ("--cost-per-missed-episode",       "Default $1,200 per missed care episode."),
            ("--growth-rate",                   "Default 0.025 (2.5%) blended compounding rate."),
            ("--average-commute-distance-miles","Default 7.5 miles (Columbus local commute proxy for VMT)."),
        ]),
        Spacer(1, 0.15*inch),
    ]

    story.append(PageBreak())

    # ── 8. DATA QUALITY ───────────────────────────────────────────────────────
    story += [
        section_header("8.  Data Quality Notes"),
        Spacer(1, 8),
        highlight_box(
            "<b>All three issues below have been resolved</b> by running "
            "collect_acs_supplement.py, which patches acs_tracts.csv and "
            "master_tract_data.csv in place.",
            bg=colors.HexColor("#eaf7ea"), border=colors.HexColor("#27ae60"),
        ),
        Spacer(1, 8),
        data_table(
            [Paragraph("Issue", BOLD_BODY), Paragraph("Status", BOLD_BODY), Paragraph("Resolution", BOLD_BODY)],
            [
                [Paragraph("ACS B18101 pulled as universe total, not disabled population", BODY_SMALL),
                 Paragraph("Fixed", BODY_SMALL),
                 Paragraph("Supplement pulls individual with-disability cells; disability_actual now in master", BODY_SMALL)],
                [Paragraph("Elderly population (65+) not in initial ACS pull", BODY_SMALL),
                 Paragraph("Fixed", BODY_SMALL),
                 Paragraph("B01001 age bands summed to elderly_65plus; wired into dependency weight", BODY_SMALL)],
                [Paragraph("Single-parent households not in initial ACS pull", BODY_SMALL),
                 Paragraph("Fixed", BODY_SMALL),
                 Paragraph("B11003_010E + B11003_016E summed to single_parent_hh; wired into dependency weight", BODY_SMALL)],
            ],
            col_widths=[2.5*inch, 0.75*inch, 3.25*inch],
        ),
        Spacer(1, 0.15*inch),
    ]

    # ── 9. WHAT THE DASHBOARD NEEDS ───────────────────────────────────────────
    story += [
        section_header("9.  What the Dashboard Needs to Build"),
        Spacer(1, 8),
        Paragraph("Primary data file to load:", BOLD_BODY),
        highlight_box("<b>data/outputs/processing_layer_results.csv</b> — one row per tract, "
                      "24 columns (see Section 6). This is the single source of truth for "
                      "the dashboard. Do not re-derive any scores from raw data."),
        Spacer(1, 8),
        Paragraph("Geospatial join:", BOLD_BODY),
        Paragraph(
            "Join results.csv to the Franklin County tract shapefile "
            "(<b>data/geospatial/franklin_tracts.geojson</b>) on <b>GEOID</b> (11-char string). "
            "Use geopandas or pydeck for map rendering.", BODY),
        Spacer(1, 8),
        Paragraph("Four dashboard tabs (per architecture spec):", BOLD_BODY),
        Spacer(1, 4),
        data_table(
            [Paragraph("Tab", BOLD_BODY), Paragraph("Key Columns", BOLD_BODY), Paragraph("Notes", BOLD_BODY)],
            [
                [Paragraph("1. Map", BODY_SMALL),
                 Paragraph("transit_hardship_index, safety_warning_score, displacement_risk_score", BODY_SMALL),
                 Paragraph("Color tracts by THI; toggle safety/displacement overlays; click tract for cost breakdown", BODY_SMALL)],
                [Paragraph("2. Cost of Inaction", BODY_SMALL),
                 Paragraph("cost_of_inaction_annual, annual_cost_year_1..5 (in costs CSV), cumulative_delay_*yr_cost", BODY_SMALL),
                 Paragraph("Headline number + stacked bar of 5 components compounding over years 1-5", BODY_SMALL)],
                [Paragraph("3. Equity", BODY_SMALL),
                 Paragraph("vulnerability_segment, transit_dependency_score, median_income", BODY_SMALL),
                 Paragraph("Bar charts by K-means segment; show who bears the cost", BODY_SMALL)],
                [Paragraph("4. Scenario Compare", BODY_SMALL),
                 Paragraph("cumulative_delay_1yr_cost, _3yr_cost, _5yr_cost", BODY_SMALL),
                 Paragraph("Side-by-side: invest now vs. delay 1/3/5 yr; show cost avoided", BODY_SMALL)],
            ],
            col_widths=[0.9*inch, 2.5*inch, 3.1*inch],
        ),
        Spacer(1, 8),
        Paragraph("Sidebar controls to wire up:", BOLD_BODY),
        Spacer(1, 4),
        Paragraph("- <b>Delay scenario selector:</b> Now / 1 yr / 3 yr / 5 yr — drives which cumulative column is shown", BULLET),
        Paragraph("- <b>Missed-care rate slider:</b> 0.05 to 0.20 — re-run process_transit_iq.py or scale healthcare_annual in-browser", BULLET),
        Paragraph("- <b>Cost per episode slider:</b> $800 to $2,000", BULLET),
        Paragraph("- <b>Target tracts:</b> multi-select or map click — filter results to selected GEOIDs", BULLET),
        Paragraph("- <b>Investment amount:</b> dollar slider — show how much of the annual cost is offset", BULLET),
        Spacer(1, 8),
        Paragraph("Export:", BOLD_BODY),
        Paragraph(
            "Architecture calls for a one-page PDF policy brief from the footer. "
            "Use reportlab (same library as this report) to generate it on demand "
            "from the sidebar. Include: selected tracts, delay scenario, headline cost, "
            "component breakdown, and the visible assumptions.", BODY),
        Spacer(1, 0.15*inch),
    ]

    # ── 10. RESPONSIBLE AI ────────────────────────────────────────────────────
    story += [
        section_header("10.  Responsible AI Requirements (Judges Weight This)"),
        Spacer(1, 8),
        Paragraph(
            "The architecture doc specifies four responsible-AI requirements. "
            "These must be visible in the dashboard UI:", BODY),
        Spacer(1, 4),
        kv_table([
            ("Human decides, not AI",
             "State explicitly in the UI that the tool surfaces costs and tradeoffs; "
             "the planner makes the funding call. AI never auto-allocates."),
            ("False positive risk",
             "Show a data-quality indicator per tract (e.g. flag low-population tracts "
             "where ACS margins of error are high). Require planner review before "
             "any allocation action."),
            ("Visible assumptions",
             "Every slider value (missed-care rate, cost/episode, growth rate) must be "
             "shown in the UI and in any exported brief — never hidden."),
            ("Displacement honesty",
             "Display the displacement_risk_score overlay and a warning that investment "
             "can price out the residents it aims to help. Frame it as a tradeoff, not "
             "a pure win."),
        ]),
        Spacer(1, 0.15*inch),
    ]

    # ── 11. FILE STRUCTURE ────────────────────────────────────────────────────
    story += [
        section_header("11.  Project File Structure"),
        Spacer(1, 8),
        highlight_box(
            "Project/<br/>"
            "&nbsp;&nbsp;process_transit_iq.py &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; # Main processing script<br/>"
            "&nbsp;&nbsp;collect_acs_supplement.py &nbsp; # Fetches missing ACS fields (run once)<br/>"
            "&nbsp;&nbsp;config.py &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; # All constants (wages, EPA, thresholds)<br/>"
            "&nbsp;&nbsp;create_master.py &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; # Joins all processed CSVs into master<br/>"
            "&nbsp;&nbsp;data/<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;outputs/ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; # Dashboard reads from here<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;master_tract_data.csv<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;processing_layer_results.csv &nbsp; # PRIMARY DASHBOARD FILE<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;processing_layer_summary.csv<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;processing_layer_metadata.json<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;processed/ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; # Component-level detail files<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;geospatial/ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; # franklin_tracts.geojson (GEOID join)<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;transit/ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; # COTA GTFS files<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;raw/ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; # Original downloads",
        ),
        Spacer(1, 0.15*inch),
    ]

    # ── FOOTER NOTE ───────────────────────────────────────────────────────────
    story += [
        hr(),
        Paragraph(
            "TransitIQ · USAII Hackathon 2026 · Graduate Track · Brief 6A — "
            "Cost of Doing Nothing Simulator · Columbus, OH · "
            "Processing layer implemented June 2026.",
            CAPTION,
        ),
    ]

    doc.build(story)
    print(f"Report written to: {OUT_PATH}")


if __name__ == "__main__":
    build()
