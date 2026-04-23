"""Pattern charts for messaging and call cadences."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from insightme.analytics import calls as call_analytics
from insightme.analytics import messages as msg_analytics


def _style_fig(fig) -> None:
    fig.update_layout(
        margin=dict(t=38, b=30, l=10, r=10),
        height=420,
        plot_bgcolor="#fffdf7",
        paper_bgcolor="#fffdf7",
        font=dict(color="#131313", family="Space Grotesk, sans-serif"),
        hoverlabel=dict(
            bgcolor="#ffffff",
            font_size=12,
            font_color="#111827",
            font_family="Space Grotesk, sans-serif",
            bordercolor="#111827",
        ),
        xaxis=dict(gridcolor="rgba(0,0,0,0.12)", zeroline=False, linecolor="#111", mirror=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0.12)", zeroline=False, linecolor="#111", mirror=True),
        title_font=dict(size=16, color="#111827"),
    )
    if fig.layout.title.text is None:
        fig.update_layout(title_text="")


def render(
    messages_df: pd.DataFrame | None,
    calls_df: pd.DataFrame | None,
) -> None:
    st.markdown("<div class='kicker'>Rhythms</div>", unsafe_allow_html=True)
    st.markdown("## Pattern studio")
    st.markdown(
        "<div class='lead-copy'>Temporal breakdown by hour and weekday to uncover repetitive communication windows.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='soft-rule'></div>", unsafe_allow_html=True)

    if messages_df is None and calls_df is None:
        st.warning("No datasets loaded.")
        return

    if messages_df is not None:
        st.markdown("### Messaging heatmap")
        heat = msg_analytics.hour_day_heatmap(messages_df)
        if not heat.empty and heat.values.sum() > 0:
            fig = px.imshow(
                heat.T,
                labels=dict(x="Hour", y="Day", color="Messages"),
                title="Messages by day and hour",
                aspect="auto",
                color_continuous_scale=["#fef3c7", "#f59e0b", "#ff4d6d", "#4f46e5"],
            )
            _style_fig(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Not enough 1:1 messages for a heatmap.")

        st.markdown("### Message distribution")
        hcol1, hcol2 = st.columns(2)

        hourly = msg_analytics.hourly_distribution(messages_df)
        if len(hourly) > 0:
            fig_h = px.bar(
                x=hourly.index,
                y=hourly.values,
                labels={"x": "Hour of day", "y": "Messages"},
                title="Messages by hour",
                color_discrete_sequence=["#4f46e5"],
            )
            fig_h.update_traces(marker_line_width=1.2, marker_line_color="#111")
            _style_fig(fig_h)
            hcol1.plotly_chart(fig_h, use_container_width=True)

        daily = msg_analytics.daily_distribution(messages_df)
        if len(daily) > 0:
            order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            day_labels = {i: order[i] for i in range(7)}
            s = daily.rename(index=day_labels).reindex(order, fill_value=0)
            fig_d = px.bar(
                x=s.index,
                y=s.values,
                labels={"x": "Day", "y": "Messages"},
                title="Messages by weekday",
                color_discrete_sequence=["#ff4d6d"],
            )
            fig_d.update_traces(marker_line_width=1.2, marker_line_color="#111")
            _style_fig(fig_d)
            hcol2.plotly_chart(fig_d, use_container_width=True)

    if calls_df is not None:
        st.markdown("### Call heatmap")
        ch = call_analytics.hour_day_heatmap(calls_df)
        if not ch.empty and ch.values.sum() > 0:
            fig_c = px.imshow(
                ch.T,
                labels=dict(x="Hour", y="Day", color="Calls"),
                title="Calls by day and hour",
                aspect="auto",
                color_continuous_scale=["#cffafe", "#06b6d4", "#1d4ed8", "#312e81"],
            )
            _style_fig(fig_c)
            st.plotly_chart(fig_c, use_container_width=True)
        else:
            st.caption("Not enough call data for a heatmap.")
