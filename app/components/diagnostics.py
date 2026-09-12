"""Developer Diagnostics component."""

import streamlit as st

from app.utils.icons import get_icon_svg


def render_diagnostics(state: dict) -> None:
    """Render developer diagnostics panel."""
    with st.expander("Developer Diagnostics & Telemetry", expanded=False):
        metrics = state.get("metrics", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Request ID", state.get("request_id", "N/A"))
        c2.metric("Raw Scraped Posts", metrics.get("retrieval_count", 0))
        c3.metric("Normalized Posts", metrics.get("normalized_count", 0))
        c4.metric("Duplicates Removed", metrics.get("duplicates_removed", 0))

        search_plan = state.get("search_plan")
        if search_plan:
            search_icon = get_icon_svg("search", size=16, color="#38bdf8")
            st.markdown(f'<div style="font-size: 0.95rem; font-weight: 600; color: #f8fafc; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">{search_icon} Generated Query Set:</div>', unsafe_allow_html=True)
            queries = getattr(search_plan, "queries", [])
            st.write(queries)
            if hasattr(search_plan, "rationale") and search_plan.rationale:
                st.caption(f"Strategy: {search_plan.rationale}")

        errors = state.get("errors", [])
        warnings = state.get("warnings", [])
        if errors:
            st.error("Errors encountered during execution:")
            for err in errors:
                st.write(f"- {err}")
        if warnings:
            st.warning("Warnings:")
            for w in warnings:
                st.write(f"- {w}")

        stream_icon = get_icon_svg("file-text", size=16, color="#38bdf8")
        st.markdown(f'<div style="font-size: 0.95rem; font-weight: 600; color: #f8fafc; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">{stream_icon} Node Event Stream:</div>', unsafe_allow_html=True)
        events = state.get("agent_events", [])
        st.json(events)
