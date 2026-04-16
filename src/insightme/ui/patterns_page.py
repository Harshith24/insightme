"""Message / call pattern charts."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from insightme.analytics import calls as call_analytics
from insightme.analytics import messages as msg_analytics


def render(
    messages_df: pd.DataFrame | None,
    calls_df: pd.DataFrame | None,
) -> None:
    st.header("Patterns")
    if messages_df is None:
        st.warning("iMessage data not loaded.")
    else:
        st.subheader("Messages — hour & day")
        heat = msg_analytics.hour_day_heatmap(messages_df)
        if not heat.empty and heat.values.sum() > 0:
            fig = px.imshow(
                heat.T,
                labels=dict(x="Hour", y="Day", color="Msgs"),
                aspect="auto",
                color_continuous_scale="Viridis",
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Not enough 1:1 messages for a heatmap.")

        hcol1, hcol2 = st.columns(2)
        hourly = msg_analytics.hourly_distribution(messages_df)
        if len(hourly) > 0:
            fig_h = px.bar(x=hourly.index, y=hourly.values, labels={"x": "Hour", "y": "Count"})
            fig_h.update_layout(title="Messages by hour of day")
            hcol1.plotly_chart(fig_h, use_container_width=True)
        daily = msg_analytics.daily_distribution(messages_df)
        if len(daily) > 0:
            order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            day_labels = {i: order[i] for i in range(7)}
            s = daily.rename(index=day_labels).reindex(order, fill_value=0)
            fig_d = px.bar(x=s.index, y=s.values, labels={"x": "Day", "y": "Count"})
            fig_d.update_layout(title="Messages by weekday")
            hcol2.plotly_chart(fig_d, use_container_width=True)

    if calls_df is None:
        st.warning("Call history not loaded.")
    else:
        st.subheader("Calls — hour & day")
        ch = call_analytics.hour_day_heatmap(calls_df)
        if not ch.empty and ch.values.sum() > 0:
            fig_c = px.imshow(
                ch.T,
                labels=dict(x="Hour", y="Day", color="Calls"),
                aspect="auto",
                color_continuous_scale="Oranges",
            )
            fig_c.update_layout(height=400)
            st.plotly_chart(fig_c, use_container_width=True)
