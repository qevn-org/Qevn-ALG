"""QEVN INTELLIGENCE — Signal Feed."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src"
for p in (str(SRC_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st

from app.utils.icons import OutlineIcon, get_icon_svg, get_tabler_image
from linkedin_intelligence.db.repository import get_lead_repository
from linkedin_intelligence.models.signals import Signal

act_img = get_tabler_image(OutlineIcon.ACTIVITY, size=32)
st.set_page_config(page_title="Signal Feed | QEVN Intelligence", page_icon=act_img or "Q", layout="wide")

# Theme CSS
css_path = Path(__file__).resolve().parent.parent / "styles" / "theme.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

act_icon = get_icon_svg("activity", size=24, color="#38bdf8")
st.markdown(f'<div class="qevn-brand">{act_icon}Signal Feed & Classification</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="qevn-subhead">Underlying public hiring evidence, urgency classifiers, and role classifications.</div>',
    unsafe_allow_html=True,
)

state = st.session_state.get("last_state")
signals: list[Signal] = []

if state and state.get("signals"):
    signals = state.get("signals", [])
else:
    # Hydrate from repository leads
    repo = get_lead_repository()
    db_leads = repo.list_leads(limit=100)
    for lead in db_leads:
        sig = Signal(
            company_name=lead.company.name,
            signal_type=lead.intent.signal_type or "Hiring",
            confidence=lead.ml_score or 0.85,
            urgency=lead.feature_vector.get("urgency_score", 0.75),
            detected_roles=[lead.person.job_title] if lead.person.job_title else ["Engineering"],
            detected_locations=[lead.company.location or "Global"],
            explanation=lead.enrichment.why_this_lead or lead.why_now or "Active public hiring signal detected on LinkedIn.",
            evidence_post_ids=lead.evidence,
        )
        signals.append(sig)


if not signals:
    st.info("No signal data currently loaded. Run an intelligence search on the [Home](/Home) page.")
    st.stop()

# Filter controls in clean card
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        sig_types = ["All"] + sorted(list({s.signal_type for s in signals if s.signal_type}))
        sel_type = st.selectbox("Filter by Signal Type", sig_types)
    with col2:
        companies = ["All"] + sorted(list({s.company_name for s in signals if s.company_name}))
        sel_comp = st.selectbox("Filter by Company", companies)

filtered = signals
if sel_type != "All":
    filtered = [s for s in filtered if s.signal_type == sel_type]
if sel_comp != "All":
    filtered = [s for s in filtered if s.company_name == sel_comp]

st.markdown(f"**Showing {len(filtered)} classified signals:**")

for s in filtered:
    with st.container(border=True):
        st.markdown(
            f"""
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                <div>
                    <span style="font-weight:800; font-size:1.2rem; color:#ffffff;">{s.company_name or 'Commercial Entity'}</span>
                    <span style="margin-left:8px; font-size:0.75rem; background:rgba(99,102,241,0.2); color:#a5b4fc; border:1px solid rgba(99,102,241,0.4); padding:3px 8px; border-radius:4px; font-weight:700;">{s.signal_type.upper()}</span>
                </div>
                <div>
                    <span style="font-size:0.85rem; color:#94a3b8;">
                        Confidence: <b style="color:#6ee7b7;">{int(s.confidence * 100)}%</b> &bull; Urgency: <b style="color:#fbbf24;">{int(s.urgency * 100)}%</b>
                    </span>
                </div>
            </div>
            <div style="margin-top:10px; font-size:0.95rem; color:#cbd5e1; line-height:1.5;">
                {s.explanation}
            </div>
            <div style="margin-top:10px; font-size:0.82rem; color:#94a3b8;">
                <b>Detected Roles:</b> <code>{', '.join(s.detected_roles) if s.detected_roles else 'Talent Need'}</code> &bull;
                <b>Locations:</b> <code>{', '.join(s.detected_locations) if s.detected_locations else 'Global'}</code>

            </div>
            """,
            unsafe_allow_html=True,
        )
