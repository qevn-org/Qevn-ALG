"""Component for rendering an executive, perfectly aligned Opportunity Card."""

import streamlit as st

try:
    from app.components.evidence_panel import render_evidence_panel
    from app.components.score_breakdown import render_score_breakdown
except ModuleNotFoundError:
    from components.evidence_panel import render_evidence_panel  # type: ignore[no-redef]
    from components.score_breakdown import render_score_breakdown  # type: ignore[no-redef]
from app.utils.icons import get_icon_svg, get_temp_badge
from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.opportunities import Opportunity


def render_opportunity_card(
    opp: Opportunity,
    all_posts: list[LinkedInPost],
    key_prefix: str = "opp",
) -> None:
    """Render high-impact, properly aligned actionable opportunity card with Tabler SVG icons."""
    temp_badge = get_temp_badge(opp.temperature)
    pin_icon = get_icon_svg("map-pin", size=13, color="#94a3b8")
    tag_icon = get_icon_svg("tag", size=13, color="#94a3b8")
    target_icon = get_icon_svg("target", size=16, color="#818cf8")
    bolt_icon = get_icon_svg("bolt", size=14, color="#fb923c")
    sparkle_icon = get_icon_svg("sparkles", size=14, color="#a5b4fc")
    users_icon = get_icon_svg("users", size=16, color="#818cf8")
    link_icon = get_icon_svg("link", size=12, color="#818cf8")

    # Native st.container with border receives the luxury glassmorphism card styling
    with st.container(border=True):
        # 1. Card Header Row
        st.markdown(
            f"""
            <div class="opp-header">
                <div style="display:flex; align-items:center; flex-wrap:wrap; gap:8px;">
                    <span class="opp-company-name">{opp.company_name}</span>
                    <span class="opp-meta-pill">{pin_icon} {opp.location or 'Global / Remote'}</span>
                    <span class="opp-meta-pill">{tag_icon} {opp.industry or 'Technology'}</span>
                </div>
                <div style="display:flex; align-items:center; gap:12px;">
                    <div class="score-pill">
                        <span class="score-number">{opp.score:.1f}</span>
                        <span class="score-denom">/ 100</span>
                    </div>
                    {temp_badge}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 2. Card Content: Two Balanced Columns
        c_left, c_right = st.columns([1.5, 1.3], gap="large")

        with c_left:
            st.markdown(f"##### {target_icon} Strategic Opportunity Intelligence", unsafe_allow_html=True)
            for bullet in opp.why_detected:
                st.markdown(f"&bull; {bullet}")

            st.markdown(f"**{bolt_icon} Urgency Window (Why Now):** {opp.why_now}", unsafe_allow_html=True)

            st.markdown(
                f"""
                <div class="action-callout">
                    <div class="action-callout-title">{sparkle_icon} Recommended Action</div>
                    <div>{opp.recommended_action}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with c_right:
            st.markdown(f"##### {users_icon} Key Stakeholders & Decision Makers", unsafe_allow_html=True)
            if opp.contacts:
                for c in opp.contacts:
                    badge_class = (
                        "status-badge-confirmed" if c.status == "confirmed" else "status-badge-probable"
                    )
                    link_html = (
                        f'<a href="{c.profile_url}" target="_blank" style="color:#818cf8; text-decoration:none; margin-left:6px; font-weight:600;">{link_icon}Profile</a>'
                        if c.profile_url
                        else ""
                    )
                    st.markdown(
                        f"""
                        <div class="stakeholder-item">
                            <div>
                                <div class="stakeholder-name">{c.name} {link_html}</div>
                                <div class="stakeholder-title">{c.headline or c.role_type}</div>
                            </div>
                            <div>
                                <span class="{badge_class}">{c.status.upper()}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("No specific leadership profile identified in public post.")

            roles_str = ", ".join(opp.detected_roles) if opp.detected_roles else "Talent Need"
            st.markdown(f"**Target Roles:** `{roles_str}`")

            # Mini Metric meters for confidence & fit
            fit_col1, fit_col2 = st.columns(2)
            with fit_col1:
                st.caption(f"Evidence Confidence: **{int(opp.confidence * 100)}%**")
                st.progress(min(1.0, max(0.0, opp.confidence)))
            with fit_col2:
                st.caption(f"Company ICP Fit: **{int(opp.company_fit)}%**")
                st.progress(min(1.0, max(0.0, opp.company_fit / 100.0)))

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # 3. Action Toolbar: Perfectly Aligned 3-Button Strip (Clean Professional Labels)
        b1, b2, b3 = st.columns(3, gap="medium")
        with b1:
            if st.button("Save to Watchlist", key=f"{key_prefix}_watch_{opp.id}", use_container_width=True):
                if "watchlist" not in st.session_state:
                    st.session_state["watchlist"] = []
                st.session_state["watchlist"].append(
                    {"Company": opp.company_name, "Category": opp.industry or "Healthcare", "Status": "Active Scan"}
                )
                st.toast(f"Added {opp.company_name} to Watchlist")

        with b2:
            if st.button("Draft Outreach", key=f"{key_prefix}_draft_{opp.id}", use_container_width=True):
                st.session_state["draft_target"] = opp
                st.toast(f"Outreach draft prepared for {opp.company_name}")

        with b3:
            st.link_button("Open in Lead Database", "/Lead_Intelligence", use_container_width=True)

        # 4. Analytics & Evidence Expanders
        with st.expander("Mathematical Score Breakdown", expanded=False):
            render_score_breakdown(opp.score_breakdown)

        with st.expander(f"Evidence Dossier ({len(opp.evidence_post_ids)} Source Posts)", expanded=False):
            render_evidence_panel(opp, all_posts)
