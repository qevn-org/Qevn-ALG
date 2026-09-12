"""QEVN LEAD INTELLIGENCE — Unified Master B2B Intelligence Database."""

import sys
from datetime import datetime
from pathlib import Path

# Ensure root and src in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = ROOT_DIR / "src"
for p in (str(SRC_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd
import streamlit as st

from app.utils.icons import OutlineIcon, get_icon_svg, get_tabler_image, get_temp_badge
from linkedin_intelligence.db.repository import get_lead_repository
from linkedin_intelligence.services.export_service import (
    export_leads_csv,
    export_leads_json,
    export_leads_xlsx,
)
from linkedin_intelligence.services.ml_scoring import get_ml_scoring_service

db_img = get_tabler_image(OutlineIcon.DATABASE, size=32)
st.set_page_config(
    page_title="Lead Intelligence | QEVN Platform",
    page_icon=db_img or "Q",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load theme CSS
css_path = ROOT_DIR / "app" / "styles" / "theme.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

repo = get_lead_repository()
ml_service = get_ml_scoring_service()

# Header
db_icon = get_icon_svg("database", size=24, color="#38bdf8")
st.markdown(f'<div class="qevn-brand">{db_icon}LEAD INTELLIGENCE DATABASE</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="qevn-subhead">Unified Master B2B Pipeline & Profiles qualified from LinkedIn hiring signals and multi-agent enrichment.</div>',
    unsafe_allow_html=True,
)

# Fetch stats
stats = repo.get_stats()
metrics_obj = ml_service.get_metrics()

flame_icon = get_icon_svg("flame", size=15, color="#f87171")
bolt_icon = get_icon_svg("bolt", size=15, color="#fb923c")
spark_icon = get_icon_svg("sparkles", size=15, color="#facc15")
snow_icon = get_icon_svg("snowflake", size=15, color="#60a5fa")
phone_icon = get_icon_svg("phone", size=15, color="#34d399")
mail_icon = get_icon_svg("mail", size=15, color="#38bdf8")
chart_icon = get_icon_svg("chart-bar", size=15, color="#c084fc")
search_icon = get_icon_svg("search", size=18, color="#38bdf8")

# Top KPI Metrics Grid (Balanced 4x2 Grid for Perfect Readability & Alignment)
kpi_r1_c1, kpi_r1_c2, kpi_r1_c3, kpi_r1_c4 = st.columns(4)
with kpi_r1_c1:
    st.markdown(
        f'<div class="metric-box"><div class="metric-number">{stats["total_leads"]}</div><div class="metric-label">Total Leads Discovered</div></div>',
        unsafe_allow_html=True,
    )
with kpi_r1_c2:
    st.markdown(
        f'<div class="metric-box"><div class="metric-number" style="color:#f87171;">{stats["hot_count"]}</div><div class="metric-label">{flame_icon}HOT (90-100)</div></div>',
        unsafe_allow_html=True,
    )
with kpi_r1_c3:
    st.markdown(
        f'<div class="metric-box"><div class="metric-number" style="color:#fb923c;">{stats["warm_count"]}</div><div class="metric-label">{bolt_icon}WARM (75-89)</div></div>',
        unsafe_allow_html=True,
    )
with kpi_r1_c4:
    st.markdown(
        f'<div class="metric-box"><div class="metric-number" style="color:#facc15;">{stats["cool_count"]}</div><div class="metric-label">{spark_icon}COOL (55-74)</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

kpi_r2_c1, kpi_r2_c2, kpi_r2_c3, kpi_r2_c4 = st.columns(4)
with kpi_r2_c1:
    st.markdown(
        f'<div class="metric-box"><div class="metric-number" style="color:#60a5fa;">{stats["cold_count"]}</div><div class="metric-label">{snow_icon}COLD (30-54)</div></div>',
        unsafe_allow_html=True,
    )
with kpi_r2_c2:
    st.markdown(
        f'<div class="metric-box"><div class="metric-number" style="color:#34d399;">{stats["contactable_count"]}</div><div class="metric-label">{phone_icon}Direct Contactable</div></div>',
        unsafe_allow_html=True,
    )
with kpi_r2_c3:
    st.markdown(
        f'<div class="metric-box"><div class="metric-number" style="color:#38bdf8;">{stats["verified_emails"]}</div><div class="metric-label">{mail_icon}Verified Emails</div></div>',
        unsafe_allow_html=True,
    )
with kpi_r2_c4:
    st.markdown(
        f'<div class="metric-box"><div class="metric-number" style="color:#c084fc;">{stats["avg_score"]:.1f}</div><div class="metric-label">{chart_icon}Average Score</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# Filter Controls Section in an Executive Card
with st.container(border=True):
    st.markdown(f"##### {search_icon}Pipeline Search & Multi-Dimensional Filters", unsafe_allow_html=True)
    f_col1, f_col2, f_col3, f_col4 = st.columns([3, 2, 2, 2])
    search_query = f_col1.text_input(
        "Search Leads",
        placeholder="Search by name, company, title, industry, tech...",
        label_visibility="collapsed",
    )

    temp_filter = f_col2.multiselect(
        "Temperature",
        options=["HOT", "WARM", "COOL", "COLD", "UNQUALIFIED", "OTHER"],
        default=["HOT", "WARM", "COOL", "COLD"],
        placeholder="Filter temperature...",
    )

    industry_filter = f_col3.selectbox(
        "Industry",
        options=[
            "All",
            "Healthcare & MedTech",
            "Fintech & Financial Services",
            "Artificial Intelligence / Deep Tech",
            "Enterprise SaaS & Cloud",
            "E-commerce & Retail",
            "Technology & Software",
        ],
    )

    status_filter = f_col4.multiselect(
        "Pipeline Status",
        options=["new", "reviewed", "in_progress", "contacted", "responded", "meeting", "won", "lost", "disqualified"],
        placeholder="Filter status...",
    )

    f_sub1, f_sub2, f_sub3, f_sub4 = st.columns(4)
    has_email_only = f_sub1.checkbox("Has Business Email", value=False)
    has_phone_only = f_sub2.checkbox("Has Phone", value=False)
    is_dm_only = f_sub3.checkbox("Decision Maker Confirmed", value=False)
    score_range = f_sub4.slider("Score Threshold", min_value=0, max_value=100, value=(0, 100))

# Query leads from repository
filtered_leads = repo.list_leads(
    temperature=temp_filter if temp_filter else None,
    status=status_filter if status_filter else None,
    search_term=search_query if search_query.strip() else None,
    industry=industry_filter if industry_filter != "All" else None,
    has_email=True if has_email_only else None,
    has_phone=True if has_phone_only else None,
    is_decision_maker=True if is_dm_only else None,
    min_score=float(score_range[0]),
    max_score=float(score_range[1]),
    limit=500,
)

if not filtered_leads:
    st.info("No leads match current criteria. Adjust the filters above or run a discovery search from the [Home](/Home) page.")
    st.stop()

# Flatten leads for tabular display
flat_data = [lead.to_flat_dict() for lead in filtered_leads]
df = pd.DataFrame(flat_data)

# Available Columns for Column Selector
ALL_AVAILABLE_COLUMNS = [
    "Lead Status", "Lead Temperature", "Lead Score", "Person Name", "Job Title",
    "Company", "Industry", "Location", "Business Email", "Phone",
    "Decision Maker Status", "Why This Lead", "Why Now", "Recommended Action",
    "Company Website", "LinkedIn Profile", "LinkedIn Post", "Post Date",
    "Detected Intent", "Signal Type", "Detected Requirement", "Technology Need",
    "Company LinkedIn", "Contact Source", "Contact Confidence", "Contact Status",
    "Company Size", "Company Description", "Evidence", "Last Enriched", "Last Seen",
]

DEFAULT_COLUMNS = [
    "Person Name",
    "Job Title",
    "Company",
    "LinkedIn Profile",
    "Business Email",
    "Lead Score",
    "Lead Temperature",
    "Detected Requirement",
    "Location",
    "Industry",
    "Decision Maker Status",
    "LinkedIn Post",
    "Why This Lead",
    "Recommended Action",
]

# Column Visibility Selector
with st.expander("Customize Table Columns", expanded=False):
    selected_cols = st.multiselect(
        "Choose columns to display",
        options=ALL_AVAILABLE_COLUMNS,
        default=DEFAULT_COLUMNS,
    )

display_cols = [c for c in selected_cols if c in df.columns]
if not display_cols:
    display_cols = DEFAULT_COLUMNS

# Export Toolbar & Bulk Actions
st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
exp_c1, exp_c2, exp_c3, exp_c4 = st.columns([2.2, 1, 1.2, 1], gap="small")
exp_c1.markdown(
    f"<div style='padding-top:8px; font-weight:600; color:#cbd5e1;'>Showing <b>{len(df)}</b> leads &bull; Mode: <code style='color:#818cf8;'>{metrics_obj.mode}</code></div>",
    unsafe_allow_html=True,
)

csv_data = export_leads_csv(filtered_leads, selected_columns=display_cols)
xlsx_data = export_leads_xlsx(filtered_leads)
json_data = export_leads_json(filtered_leads)

exp_c2.download_button(
    label="Export CSV",
    data=csv_data,
    file_name=f"qevn_leads_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
    use_container_width=True,
)

exp_c3.download_button(
    label="Export XLSX (5 Sheets)",
    data=xlsx_data,
    file_name=f"qevn_leads_intelligence_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)

exp_c4.download_button(
    label="Export JSON",
    data=json_data,
    file_name=f"qevn_leads_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
    mime="application/json",
    use_container_width=True,
)

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# Master Lead Table
st.dataframe(
    df[display_cols],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Person Name": st.column_config.TextColumn("Lead / Contact Name", width="medium"),
        "Job Title": st.column_config.TextColumn("Job Title / Role", width="medium"),
        "Company": st.column_config.TextColumn("Company", width="medium"),
        "LinkedIn Profile": st.column_config.LinkColumn("LinkedIn Profile", display_text="Open Profile", width="small"),
        "LinkedIn Post": st.column_config.LinkColumn("Source Post", display_text="View Post", width="small"),
        "Business Email": st.column_config.TextColumn("Email", width="medium"),
        "Lead Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
        "Lead Temperature": st.column_config.TextColumn("Temp", width="small"),
        "Detected Requirement": st.column_config.TextColumn("Requirement / Need", width="large"),
        "Location": st.column_config.TextColumn("Location", width="small"),
        "Industry": st.column_config.TextColumn("Industry", width="medium"),
        "Decision Maker Status": st.column_config.TextColumn("DM Status", width="small"),
        "Company Website": st.column_config.LinkColumn("Website", display_text="Visit Web", width="small"),
    },
)


st.markdown("---")

# Lead Detail Dossier / Profile Viewer
clip_icon = get_icon_svg("clipboard-list", size=20, color="#818cf8")
st.markdown(f"### {clip_icon}Lead Intelligence Dossier & Strategic Outreach", unsafe_allow_html=True)

lead_options = {
    f"[{lead.temperature}] {lead.company.name} — {lead.person.name} ({lead.score:.1f} pts)": lead.id
    for lead in filtered_leads
}
selected_label = st.selectbox(
    "Select Lead Dossier to inspect:",
    options=list(lead_options.keys()),
)

if selected_label:
    lead_id = lead_options[selected_label]
    sel_lead = repo.get_lead(lead_id)

    if sel_lead:
        temp_badge = get_temp_badge(sel_lead.temperature)
        pin_icon = get_icon_svg("map-pin", size=14, color="#94a3b8")

        # Lead Header Card
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                    <div>
                        <div style="font-size:1.6rem; font-weight:800; color:#ffffff;">
                            {sel_lead.person.name} &middot; <span style="color:#818cf8;">{sel_lead.company.name}</span>
                        </div>
                        <div style="color:#94a3b8; font-size:0.95rem; margin-top:4px;">
                            {sel_lead.person.job_title} &bull; {sel_lead.company.industry} &bull; {pin_icon}{sel_lead.company.location}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.85rem; font-weight:800; color:#c7d2fe;">{sel_lead.score:.1f}<span style="font-size:0.9rem; color:#818cf8;"> / 100</span></div>
                        <div style="margin-top:4px;">{temp_badge} <span class="status-pill">{sel_lead.status.upper()}</span></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            d_col1, d_col2 = st.columns([1.2, 1], gap="large")

            target_icon = get_icon_svg("target", size=18, color="#38bdf8")
            bulb_icon = get_icon_svg("bulb", size=16, color="#fbbf24")
            bldg_icon = get_icon_svg("building", size=18, color="#38bdf8")
            phone_icon = get_icon_svg("phone", size=18, color="#38bdf8")
            file_icon = get_icon_svg("file-text", size=18, color="#38bdf8")
            bolt_icon = get_icon_svg("bolt", size=18, color="#fb923c")

            with d_col1:
                st.markdown(f"#### {target_icon}Strategic Intelligence", unsafe_allow_html=True)
                st.markdown(f"**Why This Lead:**\n{sel_lead.enrichment.why_this_lead or ', '.join(sel_lead.why_detected)}")
                st.markdown(f"**What They Need (Requirement):**\n`{sel_lead.intent.detected_requirement}` &mdash; {sel_lead.enrichment.business_need}")
                st.markdown(f"**Urgency Window (Why Now):**\n{sel_lead.enrichment.why_now or sel_lead.why_now or 'Active public hiring window.'}")
                st.markdown(f"**Technology Need:**\n{sel_lead.intent.technology_need or sel_lead.enrichment.technology_requirement}")

                st.markdown(
                    f"""
                    <div class="action-callout">
                        <div class="action-callout-title">{bulb_icon}Recommended Outreach Angle</div>
                        <div>"{sel_lead.enrichment.recommended_outreach_angle}"</div>
                        <div style="margin-top:6px; font-size:0.8rem; color:#a5b4fc;">Service: <b>{sel_lead.enrichment.recommended_service}</b></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown(f"#### {bldg_icon}Company Profile", unsafe_allow_html=True)
                st.markdown(f"- **Website:** [{sel_lead.company.website or 'Not available'}]({sel_lead.company.website or '#'})")
                st.markdown(f"- **Company Size:** {sel_lead.company.company_size}")
                st.markdown(f"- **Tech Stack Detected:** `{', '.join(sel_lead.company.tech_stack) if sel_lead.company.tech_stack else 'Active Engineering'}`")
                st.markdown(f"- **Description:** {sel_lead.company.description or 'Operating commercial entity'}")

            with d_col2:
                st.markdown(f"#### {phone_icon}Discovered Contacts & Channels", unsafe_allow_html=True)
                if sel_lead.contacts:
                    for c in sel_lead.contacts:
                        c_badge = (
                            '<span class="contact-badge-verified">VERIFIED PUBLIC</span>'
                            if c.verification_status == "verified_public"
                            else '<span class="contact-badge-inferred">PATTERN INFERRED</span>'
                        )
                        st.markdown(f"**{c.type.replace('_', ' ').title()}:** `{c.value}` {c_badge} ({int(c.confidence * 100)}% conf)")
                        if c.source_url:
                            st.caption(f"Source: {c.source_url}")
                else:
                    st.info("No direct contact discovered yet.")

                st.markdown(f"#### {file_icon}Source Evidence", unsafe_allow_html=True)
                st.markdown(f"**Evidence Citations:** {len(sel_lead.evidence)} public post(s)")
                if sel_lead.source.raw_post_content:
                    st.text_area("Original LinkedIn Post Text", value=sel_lead.source.raw_post_content, height=130, disabled=True)
                if sel_lead.source.post_url:
                    st.link_button("View Original LinkedIn Post", sel_lead.source.post_url, use_container_width=True)

                st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                # Feedback Loop Actions Section
                st.markdown(f"#### {bolt_icon}Pipeline Feedback Actions (ML Training)", unsafe_allow_html=True)
                st.caption("Recording outcomes refines the supervised machine learning scoring model.")

                act1, act2, act3, act4, act5 = st.columns(5)

                if act1.button("Won", use_container_width=True):
                    repo.record_outcome(sel_lead.id, action="won", label=1, features=sel_lead.feature_vector, notes="Converted customer")
                    st.success("Recorded: WON (Positive Label 1)!")
                    st.rerun()

                if act2.button("Meeting", use_container_width=True):
                    repo.record_outcome(sel_lead.id, action="meeting", label=1, features=sel_lead.feature_vector, notes="Discovery call scheduled")
                    st.success("Recorded: MEETING (Positive Label 1)!")
                    st.rerun()

                if act3.button("Responded", use_container_width=True):
                    repo.record_outcome(sel_lead.id, action="responded", label=1, features=sel_lead.feature_vector, notes="Positive lead response")
                    st.success("Recorded: RESPONDED (Positive Label 1)!")
                    st.rerun()

                if act4.button("Qualified", use_container_width=True):
                    repo.record_outcome(sel_lead.id, action="qualified", label=1, features=sel_lead.feature_vector, notes="Qualified opportunity")
                    st.success("Recorded: QUALIFIED (Positive Label 1)!")
                    st.rerun()

                if act5.button("Disqualify", use_container_width=True):
                    repo.record_outcome(sel_lead.id, action="disqualified", label=0, features=sel_lead.feature_vector, notes="Unfit or no budget")
                    st.warning("Recorded: DISQUALIFIED (Negative Label 0)!")
                    st.rerun()
