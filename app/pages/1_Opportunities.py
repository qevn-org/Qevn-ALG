"""QEVN INTELLIGENCE — Opportunity Dashboard."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src"
for p in (str(SRC_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st

from app.components.opportunity_card import render_opportunity_card
from app.utils.icons import OutlineIcon, get_icon_svg, get_tabler_image
from linkedin_intelligence.db.repository import get_lead_repository
from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.opportunities import Contact, Opportunity, ScoreBreakdown

target_img = get_tabler_image(OutlineIcon.TARGET, size=32)
st.set_page_config(page_title="Opportunities | QEVN Intelligence", page_icon=target_img or "Q", layout="wide")

# Theme CSS
css_path = Path(__file__).resolve().parent.parent / "styles" / "theme.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

target_icon = get_icon_svg("target", size=24, color="#38bdf8")
st.markdown(f'<div class="qevn-brand">{target_icon}Opportunities Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="qevn-subhead">Action-ready business opportunities qualified from verified public LinkedIn hiring signals.</div>',
    unsafe_allow_html=True,
)

state = st.session_state.get("last_state")
opps: list[Opportunity] = []
posts: list[LinkedInPost] = []

if state and state.get("opportunities"):
    opps = state.get("opportunities", [])
    posts = state.get("normalized_posts", [])
else:
    # Gracefully hydrate from the persisted Lead Intelligence database
    repo = get_lead_repository()
    db_leads = repo.list_leads(limit=100)
    if db_leads:
        for lead in db_leads:
            contacts = [
                Contact(
                    name=lead.person.name,
                    role_type=lead.person.job_title or "Decision Maker",
                    headline=lead.person.job_title,
                    profile_url=lead.person.profile_url,
                    status="confirmed" if lead.is_decision_maker else "probable",
                )
            ]
            temp_mapped = "HOT" if lead.temperature == "HOT" else ("WARM" if lead.temperature in ["WARM", "COOL"] else "LOW")
            why_bullets = lead.why_detected if lead.why_detected else [f"Hiring demand for {lead.person.job_title} at {lead.company.name}"]
            why_now_text = lead.enrichment.why_now or lead.why_now or "Active public hiring window detected."
            action_text = lead.recommended_action or lead.enrichment.recommended_outreach_angle or "Initiate outreach to decision maker."
            detected_roles = [lead.person.job_title] if lead.person.job_title else [lead.intent.detected_requirement or "Talent Need"]

            opp = Opportunity(
                id=lead.id,
                company_name=lead.company.name,
                location=lead.company.location or "Global / Remote",
                industry=lead.company.industry or "Healthcare",
                score=lead.score,
                confidence=lead.ml_score or 0.85,
                company_fit=90.0,
                temperature=temp_mapped,
                detected_roles=detected_roles,
                why_detected=why_bullets,
                why_now=why_now_text,
                recommended_action=action_text,
                contacts=contacts,
                evidence_post_ids=lead.evidence,
                score_breakdown=ScoreBreakdown(
                    hiring_intent_score=float(lead.feature_vector.get("hiring_intent", 0.8)) * 100,
                    decision_maker_score=90.0 if lead.is_decision_maker else 50.0,
                    company_fit_score=float(lead.feature_vector.get("company_fit", 0.8)) * 100,
                    freshness_score=float(lead.feature_vector.get("post_freshness", 0.9)) * 100,
                    urgency_score=float(lead.feature_vector.get("urgency", 0.75)) * 100,
                    evidence_confidence_score=float(lead.feature_vector.get("evidence_confidence", 0.85)) * 100,
                    total_score=lead.score,
                ),
            )
            opps.append(opp)


if not opps:
    st.info("No opportunities currently loaded. Return to the [Home](/Home) page to run an intelligence discovery search.")
    st.stop()

# Sort opportunities by score descending
opps.sort(key=lambda o: o.score, reverse=True)

hot_opps = [o for o in opps if o.temperature == "HOT"]
warm_opps = [o for o in opps if o.temperature == "WARM"]
cool_opps = [o for o in opps if o.temperature == "COOL"]
low_opps = [o for o in opps if o.temperature == "LOW"]

# Metrics row: 4 balanced cards
flame_icon = get_icon_svg("flame", size=15, color="#f87171")
bolt_icon = get_icon_svg("bolt", size=15, color="#fb923c")
snow_icon = get_icon_svg("snowflake", size=15, color="#60a5fa")

m1, m2, m3, m4 = st.columns(4)
m1.markdown(
    f'<div class="metric-box"><div class="metric-number">{len(opps)}</div><div class="metric-label">Total Opportunities</div></div>',
    unsafe_allow_html=True,
)
m2.markdown(
    f'<div class="metric-box"><div class="metric-number" style="color:#f87171;">{len(hot_opps)}</div><div class="metric-label">{flame_icon}HOT (80-100)</div></div>',
    unsafe_allow_html=True,
)
m3.markdown(
    f'<div class="metric-box"><div class="metric-number" style="color:#fb923c;">{len(warm_opps)}</div><div class="metric-label">{bolt_icon}WARM (60-79)</div></div>',
    unsafe_allow_html=True,
)
m4.markdown(
    f'<div class="metric-box"><div class="metric-number" style="color:#60a5fa;">{len(cool_opps) + len(low_opps)}</div><div class="metric-label">{snow_icon}COOL / LOW (&lt;60)</div></div>',
    unsafe_allow_html=True,
)

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# Tabs
tab_all, tab_hot, tab_warm, tab_cool = st.tabs([
    f"All Opportunities ({len(opps)})",
    f"HOT Tier ({len(hot_opps)})",
    f"WARM Tier ({len(warm_opps)})",
    f"COOL / LOW ({len(cool_opps) + len(low_opps)})",
])

with tab_all:
    for o in opps:
        render_opportunity_card(o, posts, key_prefix="all")

with tab_hot:
    if hot_opps:
        for o in hot_opps:
            render_opportunity_card(o, posts, key_prefix="hot")
    else:
        st.write("No HOT opportunities in current run.")

with tab_warm:
    if warm_opps:
        for o in warm_opps:
            render_opportunity_card(o, posts, key_prefix="warm")
    else:
        st.write("No WARM opportunities in current run.")

with tab_cool:
    targets = cool_opps + low_opps
    if targets:
        for o in targets:
            render_opportunity_card(o, posts, key_prefix="cool")
    else:
        st.write("No COOL / LOW opportunities in current run.")
