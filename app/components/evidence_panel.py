"""Component for inspecting source evidence posts and citations."""

import streamlit as st

from app.utils.icons import get_icon_svg
from linkedin_intelligence.models.linkedin import LinkedInPost
from linkedin_intelligence.models.opportunities import Opportunity


def render_evidence_panel(opp: Opportunity, all_posts: list[LinkedInPost]) -> None:
    """Render expandable source posts supporting this opportunity."""
    post_map = {p.id: p for p in all_posts}
    evidence_posts = [post_map[pid] for pid in opp.evidence_post_ids if pid in post_map]

    file_icon = get_icon_svg("file-text", size=18, color="#38bdf8")
    st.markdown(f"#### {file_icon}Source Evidence ({len(evidence_posts)} posts)", unsafe_allow_html=True)

    if not evidence_posts:
        st.write("No direct post records attached.")
        return

    for i, post in enumerate(evidence_posts, 1):
        with st.container():
            st.markdown(
                f"""
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:12px; margin-bottom:10px;">
                    <div style="font-weight:600; color:#e2e8f0; font-size:0.95rem;">
                        {post.author_name or 'LinkedIn Member'} <span style="color:#94a3b8; font-weight:normal; font-size:0.85rem;">— {post.author_headline or 'Professional'}</span>
                    </div>
                    <div style="font-size:0.8rem; color:#64748b; margin-bottom:8px;">
                        Published: {post.published_at or 'Recent'} | Post ID: <code>{post.id}</code>
                    </div>
                    <div style="font-size:0.9rem; color:#cbd5e1; line-height:1.4; background:rgba(0,0,0,0.2); padding:8px 10px; border-radius:6px;">
                        "{post.content}"
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if post.url:
                st.link_button(f"Open Post on LinkedIn #{i}", post.url, use_container_width=False)

