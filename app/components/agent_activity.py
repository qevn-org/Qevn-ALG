"""Component for rendering live agent activity timeline and execution metrics."""

import streamlit as st

from app.utils.icons import get_icon_svg


def render_agent_activity(events: list[dict], is_running: bool = False) -> None:
    """Render structured agent node events."""
    bolt_icon = get_icon_svg("bolt", size=20, color="#38bdf8")
    st.markdown(f'<div style="font-size: 1.25rem; font-weight: 700; color: #f8fafc; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">{bolt_icon} Live Agent Activity</div>', unsafe_allow_html=True)

    if not events and not is_running:
        st.info("No active discovery session. Enter a prompt above and click **RUN INTELLIGENCE** to start.")
        return

    pipeline_nodes = [
        ("Intent Agent", "target"),
        ("Query Expansion Agent", "search"),
        ("Query Validation", "shield-check"),
        ("Retrieval Agent", "antenna"),
        ("Normalization", "adjustments"),
        ("Deduplication", "filter"),
        ("Signal Detection Agent", "activity"),
        ("Qualification Agent", "scale"),
        ("Enrichment Agent", "building"),
        ("Decision-Maker Agent", "user-check"),
        ("Opportunity Agent", "sparkles"),
    ]

    event_map = {e.get("node"): e for e in events}

    cols = st.columns([1, 1])
    with cols[0]:
        for node_name, icon_name in pipeline_nodes[:6]:
            icon_svg = get_icon_svg(icon_name, size=15, color="#38bdf8")
            if node_name in event_map:
                ev = event_map[node_name]
                status = ev.get("status", "completed")
                if status == "completed":
                    st.markdown(
                        f"<span style='font-weight:600;'><span style='color:#10b981;'>[DONE]</span> {icon_svg}{node_name}</span> &mdash; <span style='color:#94a3b8; font-style:italic;'>{ev.get('summary')}</span>",
                        unsafe_allow_html=True,
                    )
                elif status == "failed":
                    st.markdown(
                        f"<span style='font-weight:600;'><span style='color:#ef4444;'>[FAIL]</span> {icon_svg}{node_name}</span> &mdash; <span style='color:#94a3b8; font-style:italic;'>{ev.get('summary')}</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<span style='font-weight:600;'><span style='color:#f59e0b;'>[BUSY]</span> {icon_svg}{node_name}</span> &mdash; <span style='color:#94a3b8; font-style:italic;'>{ev.get('summary')}</span>",
                        unsafe_allow_html=True,
                    )
            elif is_running:
                st.markdown(f"<span style='color:#64748b;'>[WAIT] {icon_svg}{node_name}</span>", unsafe_allow_html=True)

    with cols[1]:
        for node_name, icon_name in pipeline_nodes[6:]:
            icon_svg = get_icon_svg(icon_name, size=15, color="#38bdf8")
            if node_name in event_map:
                ev = event_map[node_name]
                status = ev.get("status", "completed")
                if status == "completed":
                    st.markdown(
                        f"<span style='font-weight:600;'><span style='color:#10b981;'>[DONE]</span> {icon_svg}{node_name}</span> &mdash; <span style='color:#94a3b8; font-style:italic;'>{ev.get('summary')}</span>",
                        unsafe_allow_html=True,
                    )
                elif status == "failed":
                    st.markdown(
                        f"<span style='font-weight:600;'><span style='color:#ef4444;'>[FAIL]</span> {icon_svg}{node_name}</span> &mdash; <span style='color:#94a3b8; font-style:italic;'>{ev.get('summary')}</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<span style='font-weight:600;'><span style='color:#f59e0b;'>[BUSY]</span> {icon_svg}{node_name}</span> &mdash; <span style='color:#94a3b8; font-style:italic;'>{ev.get('summary')}</span>",
                        unsafe_allow_html=True,
                    )
            elif is_running:
                st.markdown(f"<span style='color:#64748b;'>[WAIT] {icon_svg}{node_name}</span>", unsafe_allow_html=True)
