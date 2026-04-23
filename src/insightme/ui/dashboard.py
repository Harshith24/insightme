"""Overview dashboard with top-level communication signals."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from insightme.analytics import calls as call_analytics
from insightme.analytics import messages as msg_analytics
from insightme.analytics.relationships import categorize_contacts, unified_with_names


def _style_plot(fig: go.Figure | px.Figure, *, height: int = 420) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(t=26, b=24, l=10, r=10),
        plot_bgcolor="#fffdf7",
        paper_bgcolor="#fffdf7",
        font=dict(color="#131313", family="Space Grotesk, sans-serif"),
        xaxis=dict(gridcolor="rgba(0,0,0,0.12)", zeroline=False, linecolor="#111", mirror=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0.12)", zeroline=False, linecolor="#111", mirror=True),
        hoverlabel=dict(
            bgcolor="#ffffff",
            font_size=12,
            font_family="Space Grotesk, sans-serif",
            font_color="#111827",
            bordercolor="#111827",
        ),
        title_font=dict(size=16, color="#111827"),
    )
    if fig.layout.title.text is None:
        fig.update_layout(title_text="")
    if hasattr(fig, "update_coloraxes"):
        fig.update_coloraxes(colorbar_title=None)
    return fig


def render(
    messages_df: pd.DataFrame | None,
    calls_df: pd.DataFrame | None,
    lookup: dict[str, str],
) -> None:
    st.markdown("<div class='kicker'>Overview</div>", unsafe_allow_html=True)
    st.markdown("## Communication snapshot")
    st.markdown(
        "<div class='lead-copy'>A single board for volume, relationship concentration, and weekly trend shape.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='soft-rule'></div>", unsafe_allow_html=True)

    if messages_df is None and calls_df is None:
        st.warning("No data loaded. Grant Full Disk Access and ensure local databases exist.")
        return

    col1, col2, col3, col4 = st.columns(4)

    if messages_df is not None:
        g = msg_analytics.global_stats(messages_df)
        col1.metric("Messages", f"{g['total_messages']:,}")
        col3.metric("People Messaged", f"{g['unique_contacts']:,}")
    else:
        col1.metric("Messages", "—")
        col3.metric("People Messaged", "—")

    if calls_df is not None:
        cg = call_analytics.global_stats(calls_df)
        col2.metric("Calls", f"{cg['total_calls']:,}")
        col4.metric("Call Hours", f"{cg['total_duration_hours']:,}")
    else:
        col2.metric("Calls", "—")
        col4.metric("Call Hours", "—")

    if messages_df is not None and calls_df is not None:
        unified = unified_with_names(messages_df, calls_df, lookup)
        if unified.empty:
            st.info("No overlapping contact stats yet.")
            return

        unified = unified.copy()
        unified["category"] = categorize_contacts(unified)

        st.markdown("## Relationship concentration")
        c1, c2 = st.columns(2)

        top_msg = unified.sort_values("msg_total", ascending=False).head(10)
        if not top_msg.empty and "msg_total" in top_msg.columns:
            fig_m = px.bar(
                top_msg.reset_index(),
                x="msg_total",
                y="display_name",
                orientation="h",
                title="Top Message Partners",
                labels={"display_name": "", "msg_total": "Messages"},
                color="msg_total",
                color_continuous_scale=["#c7d2fe", "#818cf8", "#4f46e5"],
            )
            fig_m.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
            fig_m.update_traces(marker_line_width=1.4, marker_line_color="#111", hovertemplate="%{y}<br>%{x} messages<extra></extra>")
            c1.plotly_chart(_style_plot(fig_m, height=420), use_container_width=True)

        top_call = unified.sort_values("call_total_duration_mins", ascending=False).head(10)
        if not top_call.empty and top_call["call_total_duration_mins"].sum() > 0:
            fig_c = px.bar(
                top_call.reset_index(),
                x="call_total_duration_mins",
                y="display_name",
                orientation="h",
                title="Top Call-Time Partners",
                labels={"display_name": "", "call_total_duration_mins": "Minutes"},
                color="call_total_duration_mins",
                color_continuous_scale=["#99f6e4", "#2dd4bf", "#0ea5e9"],
            )
            fig_c.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
            fig_c.update_traces(marker_line_width=1.4, marker_line_color="#111", hovertemplate="%{y}<br>%{x} minutes<extra></extra>")
            c2.plotly_chart(_style_plot(fig_c, height=420), use_container_width=True)
        else:
            c2.info("No call-duration signal for visualization yet.")

        st.markdown("## Weekly momentum")
        weekly = msg_analytics.weekly_volume(messages_df)
        if len(weekly) > 0:
            fig_w = go.Figure()
            fig_w.add_trace(
                go.Scatter(
                    x=weekly.index,
                    y=weekly.values,
                    mode="lines+markers",
                    fill="tozeroy",
                    name="Messages / week",
                    line=dict(color="#ff4d6d", width=3, shape="spline"),
                    marker=dict(color="#111827", size=6),
                    fillcolor="rgba(255, 77, 109, 0.2)",
                )
            )
            fig_w.update_layout(xaxis_title="Week", yaxis_title="Messages")
            fig_w.update_layout(showlegend=False)
            st.plotly_chart(_style_plot(fig_w, height=390), use_container_width=True)

        return

    if messages_df is not None:
        weekly = msg_analytics.weekly_volume(messages_df)
        if len(weekly) > 0:
            st.markdown("## Weekly momentum")
            fig_w = px.line(
                x=weekly.index,
                y=weekly.values,
                title="Messages by Week",
                color_discrete_sequence=["#ff4d6d"],
            )
            fig_w.update_traces(line=dict(shape="spline", width=3), marker=dict(size=5))
            fig_w.update_layout(showlegend=False)
            st.plotly_chart(_style_plot(fig_w, height=390), use_container_width=True)
