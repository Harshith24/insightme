"""InsightMe Streamlit app — local iMessage and call analytics."""

from __future__ import annotations

import streamlit as st

from insightme.ui import contacts_page, dashboard, data_access, insights_page, patterns_page

st.set_page_config(
    page_title="InsightMe",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --bg: #f5f1e8;
    --panel: #fffdf7;
    --ink: #131313;
    --muted: #4b5563;
    --line: #131313;
    --accent-a: #ff4d6d;
    --accent-b: #4f46e5;
    --accent-c: #06b6d4;
}

html, body, [class*="css"] {
    font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

body {
    background: var(--bg) !important;
    color: var(--ink) !important;
}

header, footer {
    visibility: hidden;
}

.stApp {
    background: var(--bg) !important;
}

.block-container {
    max-width: 1240px;
    padding-top: 1.2rem !important;
    padding-bottom: 1.4rem !important;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--ink) !important;
    letter-spacing: -0.02em;
    line-height: 1.1;
}

h1 {
    font-size: 2.1rem !important;
    font-weight: 700 !important;
}

h2 {
    font-size: 1.55rem !important;
    font-weight: 700 !important;
}

.page-shell {
    border: 2px solid var(--line);
    background: var(--panel);
    border-radius: 20px;
    box-shadow: 8px 8px 0 #131313;
    padding: 1.1rem 1.2rem;
    margin: 0 0 1rem;
}

.kicker {
    font-family: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #334155;
    margin-bottom: 0.45rem;
}

.lead-copy {
    color: var(--muted);
    font-size: 0.98rem;
}

.soft-rule {
    height: 2px;
    width: 100%;
    background: repeating-linear-gradient(
        90deg,
        #131313,
        #131313 16px,
        transparent 16px,
        transparent 24px
    );
    margin: 0.9rem 0 1.2rem;
}

/* Disable sidebar completely */
[data-testid="stSidebar"],
[data-testid="collapsedControl"] {
    display: none !important;
}

/* Force readable foreground colors in main content */
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] span,
[data-testid="stAppViewContainer"] label,
[data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] div {
    color: #111827;
}

[data-testid="stCaptionContainer"] p,
.stAlert p,
.stInfo p,
.stWarning p,
.stSuccess p,
.stError p {
    color: #111827 !important;
}

div[role="radiogroup"] > label {
    border: 2px solid #131313 !important;
    border-radius: 14px !important;
    background: #ffffff !important;
    margin-bottom: 10px !important;
    padding: 10px 12px !important;
    transition: transform .12s ease, box-shadow .12s ease;
}

div[role="radiogroup"] > label:hover {
    transform: translate(-2px, -2px);
    box-shadow: 4px 4px 0 #131313;
}

div[role="radiogroup"] > label[data-checked="true"] {
    background: linear-gradient(135deg, rgba(255,77,109,0.22), rgba(79,70,229,0.18)) !important;
    box-shadow: 4px 4px 0 #131313;
}

div[role="radiogroup"] > label p {
    color: #111827 !important;
    font-weight: 600 !important;
}

button[kind="primary"] {
    border: 2px solid #131313 !important;
    border-radius: 12px !important;
    background: #ffffff !important;
    color: #111827 !important;
}

button[kind="primary"]:hover {
    box-shadow: 4px 4px 0 #131313;
}

[data-testid="metric-container"] {
    border: 2px solid #131313 !important;
    border-radius: 14px !important;
    background: #ffffff !important;
    box-shadow: 6px 6px 0 rgba(17, 24, 39, 0.9);
    padding: 0.85rem !important;
}

[data-testid="metric-container"] [data-testid="stMetricLabel"] p,
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #111827 !important;
}

[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    color: #111827 !important;
}

[data-testid="stDataFrame"],
.stTable > div {
    border: 2px solid #131313 !important;
    border-radius: 12px;
    background: #fff;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 10px;
}

.stTabs [data-baseweb="tab"] {
    border: 2px solid #131313;
    border-radius: 12px 12px 0 0;
    background: #fff;
}

.stTabs [data-baseweb="tab-highlight"] {
    background: linear-gradient(90deg, #ff4d6d, #4f46e5);
    height: 4px;
}

.top-chip {
    border: 2px solid #131313;
    border-radius: 10px;
    padding: 0.45rem 0.65rem;
    background: #fff;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.76rem;
    display: inline-block;
}

</style>
"""


def _render_header(page_name: str) -> None:
    title_map = {
        "Overview": "Signal Board",
        "Deep Dive": "Interaction Lab",
        "People & Places": "Network Atlas",
        "Rhythms": "Pattern Studio",
    }
    subtitle_map = {
        "Overview": "Fast read on total communication, top relationships, and trend velocity.",
        "Deep Dive": "Response speed, group dynamics, and standout call sessions.",
        "People & Places": "Directory intelligence with geographic context and profile cards.",
        "Rhythms": "Temporal distribution by hour and weekday for messages and calls.",
    }
    st.markdown(
        "<div class='page-shell'>"
        "<div class='kicker'>InsightMe Interface vNext</div>"
        f"<h1>{title_map[page_name]}</h1>"
        f"<div class='lead-copy'>{subtitle_map[page_name]}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    pages = ("Overview", "Deep Dive", "People & Places", "Rhythms")
    if "active_page" not in st.session_state:
        st.session_state.active_page = "Overview"

    messages_df, calls_df, lookup, errors = data_access.load_data_or_errors()

    nav_col, contacts_col, action_col = st.columns([4, 1.2, 1.4])
    with nav_col:
        page = st.radio(
            "Navigate pages",
            pages,
            index=pages.index(st.session_state.active_page),
            horizontal=True,
            key="main_nav_radio",
        )
    with action_col:
        st.markdown("<div style='height: 1.9rem'></div>", unsafe_allow_html=True)
        if st.button("Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with contacts_col:
        st.markdown("<div style='height: 1.9rem'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='top-chip'>Contacts mapped: {len(lookup)}</div>",
            unsafe_allow_html=True,
        )

    st.session_state.active_page = page

    if errors:
        with st.expander("Data load issues", expanded=True):
            for src, err in errors:
                st.error(f"**{src}**\n\n{err}")

    _render_header(page)

    if "Overview" in page:
        dashboard.render(messages_df, calls_df, lookup)
    elif "Deep Dive" in page:
        insights_page.render(messages_df, calls_df, lookup)
    elif "People" in page:
        contacts_page.render(messages_df, calls_df, lookup)
    else:
        patterns_page.render(messages_df, calls_df)


if __name__ == "__main__":
    main()
