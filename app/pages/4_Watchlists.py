"""QEVN INTELLIGENCE — Watchlists."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from app.utils.icons import OutlineIcon, get_icon_svg, get_tabler_image

book_img = get_tabler_image(OutlineIcon.BOOKMARK, size=32)
st.set_page_config(page_title="Watchlists | QEVN Intelligence", page_icon=book_img or "Q", layout="wide")

# Theme CSS
css_path = Path(__file__).resolve().parent.parent / "styles" / "theme.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

book_icon = get_icon_svg("bookmark", size=24, color="#38bdf8")
st.markdown(f'<div class="qevn-brand">{book_icon}Watchlists & Saved Strategies</div>', unsafe_allow_html=True)
st.markdown('<div class="qevn-subhead">Track target companies, role families, and automated signal scans.</div>', unsafe_allow_html=True)

w1, w2 = st.columns([1.2, 1])

bldg_icon = get_icon_svg("building", size=20, color="#38bdf8")
search_icon = get_icon_svg("search", size=20, color="#38bdf8")
chev_icon = get_icon_svg("chevron-right", size=14, color="#818cf8")

with w1:
    st.markdown(f"### {bldg_icon}Monitored Companies", unsafe_allow_html=True)
    if "watchlist" not in st.session_state:
        st.session_state["watchlist"] = []

    watchlist = st.session_state["watchlist"]
    if watchlist:
        st.table(watchlist)
    else:
        st.info("No companies in watchlist yet. Discover opportunities on the Home page and click 'Save to Watchlist' on any company card.")

    with st.form("add_company_form"):
        new_comp = st.text_input("Add Company to Watchlist", placeholder="e.g. Apex Dental Care")
        category = st.text_input("Category / Domain", placeholder="e.g. Healthcare & Clinics")
        submitted = st.form_submit_button("Add Company")
        if submitted and new_comp.strip():
            st.session_state["watchlist"].append(
                {"Company": new_comp.strip(), "Category": category.strip() or "General", "Status": "Active Scan"}
            )
            st.success(f"Added '{new_comp.strip()}' to monitoring watchlist.")
            st.rerun()

with w2:
    st.markdown(f"### {search_icon}Saved Search Strategies", unsafe_allow_html=True)
    saved_strategies = [
        "Engineering Hiring in India (CTO/VP Eng)",
        "Fintech Scaleups series B Backend Hiring",
        "GenAI Infrastructure Engineers Bangalore",
    ]
    for s in saved_strategies:
        st.markdown(f"{chev_icon} **{s}**", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Scheduled Automation: The graph architecture is ready for automated recurring cron triggers once persistent storage is enabled.")
