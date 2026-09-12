"""QEVN INTELLIGENCE — Command Center."""

import asyncio
import sys
from pathlib import Path

# Ensure project root and src/ are in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
for p in (str(SRC_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st
from pytablericons import OutlineIcon, TablerIcons

try:
    from app.components.agent_activity import render_agent_activity
    from app.components.diagnostics import render_diagnostics
    from app.components.opportunity_card import render_opportunity_card
except ModuleNotFoundError:
    from components.agent_activity import render_agent_activity  # type: ignore[no-redef]
    from components.diagnostics import render_diagnostics  # type: ignore[no-redef]
    from components.opportunity_card import render_opportunity_card  # type: ignore[no-redef]

from app.utils.icons import get_icon_svg
from linkedin_intelligence.config.settings import get_settings
from linkedin_intelligence.db.repository import get_lead_repository
from linkedin_intelligence.main import run_discovery

# Page configuration
icon_img = TablerIcons.load(OutlineIcon.BOLT)
st.set_page_config(
    page_title="QEVN INTELLIGENCE | Command Center",
    page_icon=icon_img,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load theme CSS
css_path = Path(__file__).resolve().parent / "styles" / "theme.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Initialize session state keys
if "last_state" not in st.session_state:
    st.session_state["last_state"] = None
if "is_running" not in st.session_state:
    st.session_state["is_running"] = False

# Sidebar Branding & Quick Stats
with st.sidebar:
    bolt_icon_side = get_icon_svg("bolt", size=20, color="#818cf8")
    st.markdown(f"### {bolt_icon_side} QEVN INTELLIGENCE", unsafe_allow_html=True)
    st.caption("Autonomous LinkedIn Public Signal Engine")
    st.markdown("---")

    settings = get_settings()
    st.markdown("**System Status:**")
    st.write(f"• LLM Model: `{settings.llm_model}`")
    st.write(f"• Apify Status: `{settings.get_masked_dict()['apify_configured']}`")
    st.write(f"• Qualify Threshold: `{settings.qualification_threshold}`")
    st.markdown("---")
    st.markdown(
        "Transforming public LinkedIn hiring activity into evidence-backed commercial opportunities."
    )

# Header Section
bolt_header = get_icon_svg("bolt", size=32, color="#818cf8")
st.markdown(f'<div class="qevn-brand">{bolt_header} QEVN INTELLIGENCE</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="qevn-subhead">Autonomous discovery engine turning public LinkedIn hiring signals into qualified, actionable business opportunities.</div>',
    unsafe_allow_html=True,
)

# Command Center Input Form in an elegant container card
with st.container(border=True):
    target_icon = get_icon_svg("target", size=18, color="#818cf8")
    st.markdown(f"#### {target_icon} Natural Language Discovery Query", unsafe_allow_html=True)
    current_prompt_val = st.session_state.get(
        "saved_prompt",
        "Find clinics and healthcare companies hiring dentists during the last 7 days.",
    )
    user_prompt = st.text_area(
        "Target Objective & Query",
        value=current_prompt_val,
        height=90,
        placeholder="e.g. Find clinics and healthcare companies hiring dentists in the last 7 days...",
        label_visibility="collapsed",
        help="Describe what opportunities or signals you are seeking in natural language.",
    )

    # Filter Controls in 4 clean, balanced columns
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        signal_type = st.selectbox("Signal Type", ["Hiring", "Urgent Hiring", "Expansion", "All"])
    with f2:
        geography = st.selectbox("Target Geography", ["Any / Global", "India", "US / North America", "UK / Europe", "Australia", "Remote"])
    with f3:
        freshness = st.selectbox("Freshness Window", ["Last 7 Days", "Last 14 Days", "Last 30 Days", "Last 24 Hours"])
    with f4:
        company_size = st.selectbox("Practice / Entity Size", ["Any Size", "Solo / Small Practice (1-10)", "Group Practice (11-50)", "Healthcare Network (50+)"])

    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

    # High-impact full-width Launch Button
    run_clicked = st.button("EXECUTE MULTI-AGENT INTELLIGENCE DISCOVERY", type="primary", use_container_width=True)

# Handle Execution
if run_clicked and user_prompt.strip():
    st.session_state["saved_prompt"] = user_prompt.strip()
    st.session_state["is_running"] = True
    with st.spinner("Executing live LinkedIn search & multi-agent intelligence..."):
        augmented_prompt = f"{user_prompt} [Geography: {geography}, Freshness: {freshness}, Signal: {signal_type}]"
        result_state = asyncio.run(run_discovery(augmented_prompt))
        st.session_state["last_state"] = result_state
        st.session_state["is_running"] = False
        st.rerun()

current_state = st.session_state.get("last_state")

# Live Agent Activity Section
st.markdown("---")
events = current_state.get("agent_events", []) if current_state else []
render_agent_activity(events, is_running=st.session_state.get("is_running", False))

# If results are available in state or database, render KPI and Opportunity section
opps = current_state.get("opportunities", []) if current_state else []
posts = current_state.get("normalized_posts", []) if current_state else []
metrics = current_state.get("metrics", {}) if current_state else {}

# If current state is empty, check repository for recent discovery
if not opps:
    repo = get_lead_repository()
    db_leads = repo.list_leads(limit=20)
    if db_leads:
        chart_icon = get_icon_svg("chart-bar", size=18, color="#818cf8")
        st.markdown("---")
        st.markdown(
            f"""
            <div style="background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.3); border-radius:10px; padding:14px 18px; display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-weight:700; color:#c7d2fe; font-size:1.05rem;">{chart_icon} {len(db_leads)} Qualified Leads Ready in Intelligence Database</span>
                    <div style="color:#94a3b8; font-size:0.85rem; margin-top:2px;">Discovered from recent LinkedIn hiring scans. Fully enriched with verified contacts and company signals.</div>
                </div>
                <div>
                    <a href="/Lead_Intelligence" target="_self" style="text-decoration:none;"><button style="background:#6366f1; border:none; color:white; font-weight:700; border-radius:8px; padding:8px 16px; cursor:pointer;">Open Lead Database &rarr;</button></a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

if opps:
    st.markdown("---")
    hot_opps = [o for o in opps if o.temperature == "HOT"]
    warm_opps = [o for o in opps if o.temperature == "WARM"]
    low_opps = [o for o in opps if o.temperature == "LOW"]

    # Top KPI Metrics Row: 5 Cleanly Aligned Cards with Tabler SVG icons
    flame_icon = get_icon_svg("flame", size=14, color="#f87171")
    bolt_metric_icon = get_icon_svg("bolt", size=14, color="#fb923c")
    snow_icon = get_icon_svg("snowflake", size=14, color="#60a5fa")
    file_icon = get_icon_svg("file-text", size=14, color="#34d399")

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(
            f'<div class="metric-box"><div class="metric-number">{len(opps)}</div><div class="metric-label">Total Opportunities</div></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-box"><div class="metric-number" style="color:#f87171;">{len(hot_opps)}</div><div class="metric-label">{flame_icon} HOT (80-100)</div></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="metric-box"><div class="metric-number" style="color:#fb923c;">{len(warm_opps)}</div><div class="metric-label">{bolt_metric_icon} WARM (60-79)</div></div>',
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f'<div class="metric-box"><div class="metric-number" style="color:#60a5fa;">{len(low_opps)}</div><div class="metric-label">{snow_icon} LOW (&lt;60)</div></div>',
            unsafe_allow_html=True,
        )
    with m5:
        st.markdown(
            f'<div class="metric-box"><div class="metric-number" style="color:#34d399;">{metrics.get("unique_posts_count", len(posts))}</div><div class="metric-label">{file_icon} Posts Audited</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    target_header_icon = get_icon_svg("target", size=22, color="#818cf8")
    st.markdown(f"### {target_header_icon} Discovered Commercial Opportunities ({len(opps)})", unsafe_allow_html=True)

    for opp in opps:
        render_opportunity_card(opp, posts, key_prefix="home")

    # Diagnostics
    render_diagnostics(current_state)
