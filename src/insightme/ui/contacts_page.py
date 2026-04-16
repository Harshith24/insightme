"""Contacts explorer — unified view, area-code map, display names."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from insightme.analytics import calls as call_analytics
from insightme.analytics import messages as msg_analytics
from insightme.analytics.relationships import categorize_contacts, unified_with_names
from insightme.data.area_codes import get_area_code_location


def _jitter_lat_lng(key: str, lat: float, lng: float) -> tuple[float, float]:
    """Stable pseudo-random offset so stacked same–area-code contacts separate on the map."""
    seed = abs(hash(str(key))) % (2**32)
    rng = np.random.default_rng(seed)
    dlat = rng.uniform(-0.08, 0.08)
    dlng = rng.uniform(-0.08, 0.08)
    return lat + dlat, lng + dlng


def _contact_map_dataframe(unified: pd.DataFrame) -> pd.DataFrame:
    """One row per contact with a mappable US area code; lat/lng jittered for visibility."""
    rows = []
    for handle in unified.index:
        handle_s = str(handle)
        code = unified.loc[handle, "area_code"] if "area_code" in unified.columns else None
        if code is None or (isinstance(code, float) and pd.isna(code)):
            continue
        code = str(code).strip()
        loc = get_area_code_location(code)
        if not loc:
            continue
        lat, lng, region = loc
        jlat, jlng = _jitter_lat_lng(handle_s, float(lat), float(lng))
        name = unified.loc[handle, "display_name"] if "display_name" in unified.columns else handle_s
        rows.append(
            {
                "handle": handle_s,
                "display_name": name,
                "area_code": code,
                "region": region,
                "lat": jlat,
                "lng": jlng,
                "msg_total": int(unified.loc[handle].get("msg_total", 0) or 0),
                "call_total_calls": int(unified.loc[handle].get("call_total_calls", 0) or 0),
            }
        )
    return pd.DataFrame(rows)


def _render_contact_map(map_df: pd.DataFrame) -> None:
    if map_df.empty:
        st.info(
            "No contacts with a mappable US area code (10-digit phone). "
            "Email-only handles are not shown on the map."
        )
        return

    customdata = np.column_stack(
        [
            map_df["handle"].astype(str),
            map_df["area_code"].astype(str),
            map_df["region"].astype(str),
            map_df["msg_total"].astype(int),
            map_df["call_total_calls"].astype(int),
        ]
    )

    fig = go.Figure(
        go.Scattermap(
            lat=map_df["lat"],
            lon=map_df["lng"],
            mode="markers",
            marker=dict(size=12, color="#2563eb", opacity=0.9),
            text=map_df["display_name"],
            customdata=customdata,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Handle: %{customdata[0]}<br>"
                "%{customdata[1]} — %{customdata[2]}<br>"
                "Messages: %{customdata[3]} · Calls: %{customdata[4]}"
                "<extra></extra>"
            ),
            # MapLibre: merge nearby markers when zoomed out; split as you zoom in.
            # maxzoom: at this zoom level and above, points are never clustered (0–24).
            cluster=dict(
                enabled=True,
                maxzoom=22,
                size=28,
            ),
        )
    )
    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(lat=39.8, lon=-98.5),
            zoom=3,
            uirevision="insightme-contacts-map",
        ),
        height=560,
        margin=dict(l=0, r=0, t=44, b=0),
        title=dict(
            text="Contacts by area code — clusters show counts when zoomed out; zoom in to expand",
            font=dict(size=14),
        ),
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        },
    )
    st.caption(
        "Approximate NANPA area-code centers (not street addresses). "
        "Use **scroll/pinch to zoom**; nearby contacts merge into numbered bubbles until you zoom in. "
        "Same-area-code contacts stay slightly offset so they can separate when unclustered."
    )


def _fmt_dt(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    if hasattr(x, "strftime"):
        return x.strftime("%Y-%m-%d %H:%M")
    return str(x)


def _render_message_stats_card(stats_row: pd.Series) -> None:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total messages", f"{int(stats_row['total']):,}")
    m2.metric("Sent", f"{int(stats_row['sent']):,}")
    m3.metric("Received", f"{int(stats_row['received']):,}")
    ratio = stats_row["ratio"]
    m4.metric("Sent / received ratio", f"{ratio:.2f}" if ratio != float("inf") else "∞")

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Longest streak (days)", f"{int(stats_row['streak_max'])}")
    m6.metric("Longest dry spell (days)", f"{int(stats_row['dry_spell_max'])}")
    m7.metric("Days active", f"{int(stats_row['days_active'])}")
    m8.metric("Avg words (sent / recv)", f"{stats_row['avg_words_sent']:.1f} / {stats_row['avg_words_received']:.1f}")

    st.markdown(
        f"**First message:** {_fmt_dt(stats_row.get('first_message'))}  \n"
        f"**Last message:** {_fmt_dt(stats_row.get('last_message'))}"
    )


def _render_call_stats_card(row: pd.Series) -> None:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total calls", f"{int(row['total_calls']):,}")
    m2.metric("Answered", f"{int(row['answered']):,}")
    m3.metric("Missed", f"{int(row['missed']):,}")
    m4.metric("Total talk time", f"{row['total_duration_mins']:.0f} min")

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Outgoing", f"{int(row['outgoing']):,}")
    m6.metric("Incoming", f"{int(row['incoming']):,}")
    m7.metric("Avg duration (answered)", f"{row['avg_duration_mins']:.1f} min")
    m8.metric("Longest call", f"{row['max_duration_mins']:.1f} min")

    st.markdown("**By type**")
    t1, t2, t3 = st.columns(3)
    t1.metric("Phone", f"{int(row['phone_calls']):,}")
    t2.metric("FaceTime video", f"{int(row['facetime_video']):,}")
    t3.metric("FaceTime audio", f"{int(row['facetime_audio']):,}")

    st.markdown(
        f"**First call:** {_fmt_dt(row.get('first_call'))}  \n"
        f"**Last call:** {_fmt_dt(row.get('last_call'))}"
    )


def render(
    messages_df: pd.DataFrame | None,
    calls_df: pd.DataFrame | None,
    lookup: dict[str, str],
) -> None:
    st.header("Contacts")
    if messages_df is None and calls_df is None:
        st.warning("No data loaded.")
        return

    if messages_df is None or calls_df is None:
        st.warning("Load both iMessage and Call History for a unified table.")
        if messages_df is not None:
            st.dataframe(
                messages_df.groupby("handle_normalized").size().head(50),
                use_container_width=True,
            )
        return

    unified = unified_with_names(messages_df, calls_df, lookup)
    if unified.empty:
        st.info("No contacts to show.")
        return

    cats = categorize_contacts(unified)
    show = unified.copy()
    show["category"] = cats
    show = show.reset_index()
    handle_col = show.columns[0]
    show["handle"] = show[handle_col].astype(str)

    q = st.text_input("Filter by name or number", "")
    if q.strip():
        mask = show["display_name"].str.contains(q, case=False, na=False) | show[
            "handle"
        ].str.contains(q, case=False, na=False)
        show = show[mask]

    tab_dir, tab_map = st.tabs(["Directory", "Map"])

    with tab_map:
        map_df = _contact_map_dataframe(unified)
        if not q.strip():
            map_filtered = map_df
        else:
            handles = set(show["handle"].astype(str))
            map_filtered = map_df[map_df["handle"].isin(handles)]
        _render_contact_map(map_filtered)

    with tab_dir:
        cols = [
            "display_name",
            "handle",
            "category",
            "msg_total",
            "call_total_calls",
            "call_total_duration_mins",
            "total_interactions",
            "first_contact",
            "last_contact",
        ]
        cols = [c for c in cols if c in show.columns]
        sort_col = "total_interactions" if "total_interactions" in show.columns else cols[0]
        st.dataframe(
            show[cols].sort_values(sort_col, ascending=False),
            use_container_width=True,
            height=420,
        )

        st.subheader("Contact detail")
        opts = unified.reset_index()
        hc = opts.columns[0]
        opts = opts.sort_values("total_interactions", ascending=False)
        opts["_label"] = opts["display_name"] + " (" + opts[hc].astype(str) + ")"

        pick = st.selectbox(
            "Choose a contact",
            options=opts[hc].tolist(),
            format_func=lambda h: opts.loc[opts[hc] == h, "_label"].iloc[0],
        )
        if pick is None:
            return

        label = opts.loc[opts[hc] == pick, "_label"].iloc[0]
        st.markdown(f"### {label}")

        row_u = unified.loc[pick]
        ac = row_u.get("area_code")
        cat_lbl = str(cats[pick]) if pick in cats.index else "—"
        if ac is not None and not (isinstance(ac, float) and pd.isna(ac)):
            loc = get_area_code_location(str(ac))
            region_note = f" ({loc[2]})" if loc else ""
            st.caption(f"Area code **{ac}**{region_note} · Category: **{cat_lbl}**")
        else:
            st.caption(f"Category: **{cat_lbl}** (no US area code for map)")

        msg_stats = msg_analytics.per_contact_stats(messages_df)
        cstats = call_analytics.per_contact_stats(calls_df)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Messages (1:1)")
            if pick in msg_stats.index:
                _render_message_stats_card(msg_stats.loc[pick])
            else:
                st.caption("No 1:1 message stats for this handle.")

        with c2:
            st.markdown("#### Calls")
            if pick in cstats.index:
                _render_call_stats_card(cstats.loc[pick])
            else:
                st.caption("No calls for this number.")
