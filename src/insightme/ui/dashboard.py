"""Dashboard charts and KPIs."""

from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from insightme.analytics import calls as call_analytics
from insightme.analytics import messages as msg_analytics
from insightme.analytics.relationships import categorize_contacts, unified_with_names


def render(
    messages_df: pd.DataFrame | None,
    calls_df: pd.DataFrame | None,
    lookup: dict[str, str],
) -> None:
    st.header("Overview")
    if messages_df is None and calls_df is None:
        st.warning("No data loaded. Grant Full Disk Access and ensure databases exist.")
        return

    col1, col2, col3, col4 = st.columns(4)
    if messages_df is not None:
        g = msg_analytics.global_stats(messages_df)
        col1.metric("1:1 messages", f"{g['total_messages']:,}")
        col3.metric("Unique chat contacts", f"{g['unique_contacts']:,}")
    else:
        col1.metric("1:1 messages", "—")
        col3.metric("Unique chat contacts", "—")

    if calls_df is not None:
        cg = call_analytics.global_stats(calls_df)
        col2.metric("Calls", f"{cg['total_calls']:,}")
        col4.metric("Call hours (answered)", f"{cg['total_duration_hours']:,}")
    else:
        col2.metric("Calls", "—")
        col4.metric("Call hours", "—")

    st.caption(
        f"Contacts name map: **{len(lookup)}** phone/email → name pairs from macOS Contacts."
    )

    if messages_df is not None and calls_df is not None:
        unified = unified_with_names(messages_df, calls_df, lookup)
        if unified.empty:
            st.info("No overlapping contact stats yet.")
            return

        cats = categorize_contacts(unified)
        unified = unified.copy()
        unified["category"] = cats

        c1, c2 = st.columns(2)

        top_msg = unified.sort_values("msg_total", ascending=False).head(15)
        if not top_msg.empty and "msg_total" in top_msg.columns:
            fig_m = px.bar(
                top_msg.reset_index(),
                x="display_name",
                y="msg_total",
                title="Top contacts by 1:1 messages",
                labels={"display_name": "", "msg_total": "Messages"},
            )
            fig_m.update_layout(xaxis_tickangle=-35, height=420, margin=dict(b=120))
            c1.plotly_chart(fig_m, use_container_width=True)

        top_call = unified.sort_values("call_total_calls", ascending=False).head(15)
        if not top_call.empty and top_call["call_total_calls"].sum() > 0:
            fig_c = px.bar(
                top_call.reset_index(),
                x="display_name",
                y="call_total_duration_mins",
                title="Top contacts by call time (minutes)",
                labels={"display_name": "", "call_total_duration_mins": "Minutes"},
            )
            fig_c.update_layout(xaxis_tickangle=-35, height=420, margin=dict(b=120))
            c2.plotly_chart(fig_c, use_container_width=True)
        else:
            c2.info("No call duration data to chart.")

        weekly = msg_analytics.weekly_volume(messages_df)
        if len(weekly) > 0:
            fig_w = go.Figure()
            fig_w.add_trace(
                go.Scatter(
                    x=weekly.index,
                    y=weekly.values,
                    mode="lines",
                    fill="tozeroy",
                    name="Messages / week",
                )
            )
            fig_w.update_layout(
                title="Weekly message volume (1:1)",
                height=360,
                margin=dict(t=50),
                xaxis_title="Week",
                yaxis_title="Messages",
            )
            st.plotly_chart(fig_w, use_container_width=True)

        heat = msg_analytics.hour_day_heatmap(messages_df)
        if not heat.empty and heat.values.sum() > 0:
            fig_h = px.imshow(
                heat.T,
                labels=dict(x="Hour", y="Day", color="Msgs"),
                title="When you message (1:1) — hour × day",
                aspect="auto",
                color_continuous_scale="Blues",
            )
            fig_h.update_layout(height=380)
            st.plotly_chart(fig_h, use_container_width=True)

    elif messages_df is not None:
        weekly = msg_analytics.weekly_volume(messages_df)
        if len(weekly) > 0:
            fig_w = px.line(x=weekly.index, y=weekly.values, title="Weekly messages")
            st.plotly_chart(fig_w, use_container_width=True)
