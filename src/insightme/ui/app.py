"""insightme Streamlit app — local iMessage & call analytics."""

from __future__ import annotations

import streamlit as st

from insightme.ui import contacts_page, dashboard, data_access, insights_page, patterns_page

st.set_page_config(
    page_title="insightme",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    st.sidebar.title("insightme")
    st.sidebar.caption("Runs locally on your Mac — no uploads.")

    messages_df, calls_df, lookup, errors = data_access.load_data_or_errors()
    if errors:
        with st.sidebar.expander("Data load issues", expanded=True):
            for src, err in errors:
                st.error(f"**{src}**\n\n{err}")

    page = st.sidebar.radio(
        "Navigate",
        ("Dashboard", "Insights", "Contacts", "Patterns"),
        label_visibility="collapsed",
    )
    st.sidebar.divider()
    if st.sidebar.button("Clear cached data"):
        st.cache_data.clear()
        st.rerun()

    if messages_df is not None or calls_df is not None:
        st.sidebar.success(
            f"Loaded: "
            f"{'iMessage ✓' if messages_df is not None else 'iMessage —'} · "
            f"{'Calls ✓' if calls_df is not None else 'Calls —'} · "
            f"{len(lookup)} names"
        )
    else:
        st.sidebar.warning("No databases loaded.")

    if page == "Dashboard":
        dashboard.render(messages_df, calls_df, lookup)
    elif page == "Insights":
        insights_page.render(messages_df, calls_df, lookup)
    elif page == "Contacts":
        contacts_page.render(messages_df, calls_df, lookup)
    else:
        patterns_page.render(messages_df, calls_df)


if __name__ == "__main__":
    main()
