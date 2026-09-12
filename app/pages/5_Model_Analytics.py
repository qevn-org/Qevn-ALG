"""QEVN INTELLIGENCE — Model Performance & Analytics Dashboard."""

import sys
from pathlib import Path

# Ensure root and src in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src"
for p in (str(SRC_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
import streamlit as st

from app.utils.icons import OutlineIcon, get_icon_svg, get_tabler_image
from linkedin_intelligence.db.repository import get_lead_repository
from linkedin_intelligence.services.ml_scoring import get_ml_scoring_service

brain_img = get_tabler_image(OutlineIcon.BRAIN, size=32)
st.set_page_config(page_title="Model & Analytics | QEVN Intelligence", page_icon=brain_img or "Q", layout="wide")

# Theme CSS
css_path = ROOT_DIR / "app" / "styles" / "theme.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

brain_icon = get_icon_svg("brain", size=24, color="#38bdf8")
st.markdown(f'<div class="qevn-brand">{brain_icon}Machine Learning & Scoring Analytics</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="qevn-subhead">Supervised lead conversion modeling, 18-dim feature importances, and outcome feedback analytics.</div>',
    unsafe_allow_html=True,
)

repo = get_lead_repository()
ml_service = get_ml_scoring_service()
metrics = ml_service.get_metrics()
outcomes = repo.get_outcomes_dataset()
stats = repo.get_stats()

# Model Status Alert in a luxury Card
status_color = "#38bdf8" if metrics.mode == "Trained" else "#fbbf24"
with st.container(border=True):
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <h3 style="margin:0; color:#ffffff;">MODEL STATUS: <span style="color:{status_color}; font-weight:800;">{metrics.mode.upper()}</span></h3>
                <div style="color:#94a3b8; font-size:0.95rem; margin-top:4px;">{metrics.status_message}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.05rem; font-weight:700; color:#c7d2fe;">Algorithm: {metrics.algorithm}</div>
                <div style="color:#64748b; font-size:0.82rem; margin-top:2px;">Last Trained: {metrics.last_trained or 'Never (Cold Start)'}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# Top Metrics Row
c1, c2, c3, c4 = st.columns(4)
c1.markdown(
    f'<div class="metric-box"><div class="metric-number">{len(outcomes)}</div><div class="metric-label">Historical Feedback Labels</div></div>',
    unsafe_allow_html=True,
)
c2.markdown(
    f'<div class="metric-box"><div class="metric-number" style="color:#34d399;">{stats["positive_outcomes"]}</div><div class="metric-label">Positive (Won/Meeting)</div></div>',
    unsafe_allow_html=True,
)
c3.markdown(
    f'<div class="metric-box"><div class="metric-number" style="color:#f87171;">{stats["negative_outcomes"]}</div><div class="metric-label">Negative (Disqualified)</div></div>',
    unsafe_allow_html=True,
)
c4.markdown(
    f'<div class="metric-box"><div class="metric-number" style="color:#38bdf8;">{stats["total_leads"]}</div><div class="metric-label">Total Repository Leads</div></div>',
    unsafe_allow_html=True,
)

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# Training Section
t_col1, t_col2 = st.columns([1.8, 1.2], gap="large")

chart_icon = get_icon_svg("chart-bar", size=18, color="#38bdf8")
settings_icon = get_icon_svg("settings", size=18, color="#38bdf8")
clip_icon = get_icon_svg("clipboard-list", size=20, color="#818cf8")

with t_col1:
    with st.container(border=True):
        st.markdown(f"#### {chart_icon}Model Evaluation & Diagnostic Metrics", unsafe_allow_html=True)
        if metrics.mode == "Trained" and metrics.accuracy is not None:
            m_c1, m_c2, m_c3, m_c4 = st.columns(4)
            m_c1.metric("Validation Accuracy", f"{metrics.accuracy * 100:.1f}%")
            m_c2.metric("Precision", f"{metrics.precision * 100:.1f}%" if metrics.precision else "N/A")
            m_c3.metric("Recall", f"{metrics.recall * 100:.1f}%" if metrics.recall else "N/A")
            m_c4.metric("ROC-AUC", f"{metrics.roc_auc:.3f}" if metrics.roc_auc else "0.500")

            if metrics.feature_importances:
                st.markdown("##### Feature Importances (Model Weights)")
                feat_df = pd.DataFrame(
                    list(metrics.feature_importances.items()),
                    columns=["Feature", "Importance Weight"],
                ).sort_values(by="Importance Weight", ascending=False)
                st.bar_chart(feat_df.set_index("Feature"))
        else:
            st.info(
                f"**Cold-Start Hybrid Heuristic Active**\n\n"
                f"Current labeled feedback: **{len(outcomes)} / 20 required** for supervised model training.\n\n"
                "The platform is currently operating in **Transparent Hybrid Scoring Mode** (18-feature weighted heuristic). "
                "Tag leads as **Won**, **Meeting**, **Responded**, or **Disqualified** on the [Lead Intelligence](/Lead_Intelligence) page to build your training dataset."
            )

with t_col2:
    with st.container(border=True):
        st.markdown(f"#### {settings_icon}Train / Retrain Model", unsafe_allow_html=True)
        st.write("Trigger supervised retraining on collected outcome dataset.")
        if st.button("Train Supervised Model", type="primary", use_container_width=True):
            with st.spinner("Evaluating dataset and training model..."):
                new_meta = ml_service.train_from_dataset(outcomes)
                if new_meta.mode == "Trained":
                    st.success(f"Model trained successfully! Accuracy: {new_meta.accuracy * 100:.1f}%")
                    st.rerun()
                else:
                    st.warning(new_meta.status_message)

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# Labeled Outcome History
st.markdown(f"### {clip_icon}Labeled Feedback Audit Trail", unsafe_allow_html=True)
if outcomes:
    outcomes_flat = [
        {
            "Lead ID": o.lead_id[:8] + "...",
            "Action Taken": o.action.upper(),
            "ML Label": "POSITIVE (1)" if o.label == 1 else "NEGATIVE (0)",
            "Notes": o.notes,
            "Recorded At": o.recorded_at,
        }
        for o in outcomes
    ]
    st.dataframe(pd.DataFrame(outcomes_flat), use_container_width=True, hide_index=True)
else:
    st.caption("No outcome labels recorded yet. Record feedback actions on the Lead Intelligence page.")
