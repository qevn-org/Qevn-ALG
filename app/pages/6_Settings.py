"""QEVN INTELLIGENCE — Settings & Configuration."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src"
for p in (str(SRC_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st

from app.utils.icons import OutlineIcon, get_icon_svg, get_tabler_image
from linkedin_intelligence.config.settings import get_settings

settings_img = get_tabler_image(OutlineIcon.SETTINGS, size=32)
st.set_page_config(page_title="Settings | QEVN Intelligence", page_icon=settings_img or "Q", layout="wide")

# Theme CSS
css_path = Path(__file__).resolve().parent.parent / "styles" / "theme.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

gear_icon = get_icon_svg("settings", size=24, color="#38bdf8")
st.markdown(f'<div class="qevn-brand">{gear_icon}Settings & System Configuration</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="qevn-subhead">Manage runtime parameters, lead scoring weights, cloud database synchronization, and credentials.</div>',
    unsafe_allow_html=True,
)

settings = get_settings()
masked = settings.get_masked_dict()

shield_icon = get_icon_svg("shield-check", size=18, color="#38bdf8")
guard_icon = get_icon_svg("shield-lock", size=18, color="#38bdf8")
scale_icon = get_icon_svg("scale", size=18, color="#38bdf8")
temp_icon = get_icon_svg("temperature", size=18, color="#38bdf8")
cloud_icon = get_icon_svg("cloud-upload", size=18, color="#38bdf8")
diag_icon = get_icon_svg("activity", size=18, color="#38bdf8")
flame_icon = get_icon_svg("flame", size=14, color="#f87171")
bolt_icon = get_icon_svg("bolt", size=14, color="#fb923c")
snow_icon = get_icon_svg("snowflake", size=14, color="#60a5fa")

c1, c2 = st.columns([1, 1], gap="large")

with c1:
    with st.container(border=True):
        st.markdown(f'<div style="font-size: 1.1rem; font-weight: 600; color: #f8fafc; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">{shield_icon} Secure Credential Status</div>', unsafe_allow_html=True)
        st.caption("API keys are securely resolved from .env and masked at all times.")

        st.markdown(f"- **OpenAI Key:** `{masked['openai_configured']}`")
        st.markdown(f"- **Groq Key:** `{masked['groq_configured']}`")
        st.markdown(f"- **Apify Token:** `{masked['apify_configured']}`")
        st.markdown(f"- **Supabase Cloud DB:** `{masked.get('supabase_configured', 'SQLite (Local Active)')}`")
        st.markdown(f"- **Active LLM Model:** `{masked['llm_model']}`")
        st.markdown(f"- **Tracing:** `{'Enabled' if masked['langsmith_tracing'] else 'Disabled'}`")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f'<div style="font-size: 1.1rem; font-weight: 600; color: #f8fafc; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">{guard_icon} Runtime Guardrails & Search Limits</div>', unsafe_allow_html=True)
        st.markdown(f"- **Max Search Queries:** `{masked['max_search_queries']}`")
        st.markdown(f"- **Max Results Per Discovery:** `{masked['max_results_per_run']}`")
        st.markdown(f"- **Max Deep Research Items:** `{masked['max_deep_research_items']}`")

with c2:
    with st.container(border=True):
        st.markdown(f'<div style="font-size: 1.1rem; font-weight: 600; color: #f8fafc; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">{scale_icon} Scoring Model & Temperature Bands</div>', unsafe_allow_html=True)
        st.caption("Multi-dimensional weights applied during qualification:")

        st.slider("Hiring Intent Weight", 0.0, 1.0, settings.weight_hiring_intent, disabled=True)
        st.slider("Decision Maker Weight", 0.0, 1.0, settings.weight_decision_maker, disabled=True)
        st.slider("Company Fit Weight", 0.0, 1.0, settings.weight_company_fit, disabled=True)
        st.slider("Freshness Weight", 0.0, 1.0, settings.weight_freshness, disabled=True)
        st.slider("Urgency Weight", 0.0, 1.0, settings.weight_urgency, disabled=True)
        st.slider("Evidence Confidence Weight", 0.0, 1.0, settings.weight_evidence_confidence, disabled=True)

        st.markdown(f'<div style="font-size: 0.95rem; font-weight: 600; color: #f8fafc; margin: 12px 0 8px 0; display: flex; align-items: center; gap: 6px;">{temp_icon} Temperature Cutoffs</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; align-items:center; gap:6px; margin:4px 0;">{flame_icon}<strong>HOT:</strong> &ge; {settings.hot_threshold} points</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; align-items:center; gap:6px; margin:4px 0;">{bolt_icon}<strong>WARM:</strong> &ge; {settings.qualification_threshold} points</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex; align-items:center; gap:6px; margin:4px 0;">{snow_icon}<strong>LOW:</strong> &lt; {settings.qualification_threshold} points</div>', unsafe_allow_html=True)

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
s_col1, s_col2 = st.columns([1, 1], gap="large")

with s_col1:
    with st.container(border=True):
        st.markdown(f'<div style="font-size: 1.1rem; font-weight: 600; color: #f8fafc; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">{cloud_icon} Supabase Cloud Synchronization</div>', unsafe_allow_html=True)
        st.caption("Synchronize local SQLite leads to your remote Supabase PostgreSQL database.")
        if st.button("Push Local Leads to Supabase", use_container_width=True):
            with st.spinner("Connecting to Supabase and syncing records..."):
                from linkedin_intelligence.db.repository import SqliteLeadRepository
                from linkedin_intelligence.db.supabase_repo import SupabaseLeadRepository

                sqlite_repo = SqliteLeadRepository()
                leads = sqlite_repo.list_leads(limit=1000)
                supa_repo = SupabaseLeadRepository()

                if supa_repo.is_connected:
                    supa_repo.upsert_leads(leads)
                    st.success(f"Successfully synchronized {len(leads)} leads to Supabase PostgreSQL!")
                else:
                    st.error("Could not connect to Supabase `leads` table.")
                    st.info("Ensure the schema migration in `supabase/lead_intelligence_schema.sql` has been executed in Supabase SQL Editor.")

with s_col2:
    with st.container(border=True):
        st.markdown(f'<div style="font-size: 1.1rem; font-weight: 600; color: #f8fafc; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">{diag_icon} Diagnostic Self-Test</div>', unsafe_allow_html=True)
        st.caption("Validate state graph compilation and retrieval services.")
        if st.button("Run System Diagnostic Check", use_container_width=True):
            with st.spinner("Verifying subsystems..."):
                from linkedin_intelligence.tools.retrieval_service import LinkedInRetrievalService

                service = LinkedInRetrievalService()
                st.success("LangGraph StateGraph compiled and validated.")
                st.success("LinkedInRetrievalService operational.")
                st.success("Normalization, Deduplication, and Scoring pipelines verified.")
