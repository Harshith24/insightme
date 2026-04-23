"""People explorer and contact detail panels."""

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
    """Stable pseudo-random offset so stacked same-area contacts separate on the map."""
    seed = abs(hash(str(key))) % (2 ** 32)
    rng = np.random.default_rng(seed)
    dlat = rng.uniform(-0.08, 0.08)
    dlng = rng.uniform(-0.08, 0.08)
    return lat + dlat, lng + dlng


def _contact_map_dataframe(unified: pd.DataFrame) -> pd.DataFrame:
    """One row per contact with a mappable area code and jittered coordinates."""
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
        st.info("No contacts with a mappable US area code (10-digit phone) are available for the map.")
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
            marker=dict(size=13, color="#4f46e5", opacity=0.92),
            text=map_df["display_name"],
            customdata=customdata,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Handle: %{customdata[0]}<br>"
                "%{customdata[1]} - %{customdata[2]}<br>"
                "%{customdata[3]} messages · %{customdata[4]} calls"
                "<extra></extra>"
            ),
            cluster=dict(
                enabled=True,
                maxzoom=22,
                size=30,
                color="#ff4d6d",
            ),
        )
    )
    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(lat=39.8, lon=-98.5),
            zoom=3.5,
            uirevision="insightme-contacts-map",
        ),
        height=540,
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="#fffdf7",
        paper_bgcolor="#fffdf7",
        font=dict(color="#111827", family="Space Grotesk, sans-serif"),
    )
    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": False,
        },
    )
    st.caption("Scroll to zoom. Clusters collapse nearby points when zoomed out and split as you zoom in.")


def _render_message_stats_card(stats_row: pd.Series) -> None:
    st.markdown("#### Message profile")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", f"{int(stats_row['total']):,}")
    m2.metric("Sent", f"{int(stats_row['sent']):,}")
    m3.metric("Received", f"{int(stats_row['received']):,}")
    ratio = stats_row["ratio"]
    m4.metric("Sent / Received", f"{ratio:.2f}x" if ratio != float("inf") else "inf")

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Longest Streak", f"{int(stats_row['streak_max'])} days")
    m6.metric("Longest Gap", f"{int(stats_row['dry_spell_max'])} days")
    m7.metric("Days Active", f"{int(stats_row['days_active'])}")
    m8.metric("Avg Words", f"{stats_row['avg_words_sent']:.1f} / {stats_row['avg_words_received']:.1f}")


def _render_call_stats_card(row: pd.Series) -> None:
    st.markdown("#### Call profile")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Calls", f"{int(row['total_calls']):,}")
    m2.metric("Answered", f"{int(row['answered']):,}")
    m3.metric("Missed", f"{int(row['missed']):,}")
    m4.metric("Talk Time", f"{row['total_duration_mins']:.0f} min")

    m5, m6, m7 = st.columns(3)
    m5.metric("Avg Duration", f"{row['avg_duration_mins']:.1f} min")
    m6.metric("Longest", f"{row['max_duration_mins']:.1f} min")
    m7.metric("FaceTime (V / A)", f"{int(row['facetime_video'])} / {int(row['facetime_audio'])}")


def _render_contact_header(label: str, handle: str, category: str, location: str) -> None:
    st.markdown(
        """
<div class='page-shell' style="padding: 1rem;">
  <div class='kicker'>Contact profile</div>
  <h2 style="margin: 0;">{label}</h2>
  <div class='lead-copy'>{location}</div>
  <div class='lead-copy'>{category} • {handle}</div>
</div>
""".format(
            label=label,
            location=location,
            category=category.title(),
            handle=handle,
        ),
        unsafe_allow_html=True,
    )


def render(
    messages_df: pd.DataFrame | None,
    calls_df: pd.DataFrame | None,
    lookup: dict[str, str],
) -> None:
    st.markdown("<div class='kicker'>People & Places</div>", unsafe_allow_html=True)
    st.markdown("## Network atlas")
    st.markdown(
        "<div class='lead-copy'>Search your network, inspect where contacts are from, and open profile-level interaction summaries.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='soft-rule'></div>", unsafe_allow_html=True)

    if messages_df is None and calls_df is None:
        st.warning("No data loaded.")
        return

    if messages_df is None or calls_df is None:
        st.warning("Load both iMessage and Call History for the full unified experience.")
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

    tab_map, tab_dir = st.tabs(["Geographic Map", "Directory Workspace"])

    with tab_map:
        st.markdown("### Area-code geography")
        map_df = _contact_map_dataframe(unified)
        _render_contact_map(map_df)

    with tab_dir:
        st.markdown("### Search")
        q = st.text_input("Find by name or handle", "")

        if q.strip():
            mask = show["display_name"].str.contains(q, case=False, na=False) | show["handle"].str.contains(
                q, case=False, na=False
            )
            show = show[mask]

        cols = [
            "display_name",
            "handle",
            "category",
            "msg_total",
            "call_total_calls",
            "call_total_duration_mins",
            "total_interactions",
        ]
        cols = [c for c in cols if c in show.columns]
        sort_col = "total_interactions" if "total_interactions" in show.columns else cols[0]

        st.dataframe(
            show[cols]
            .sort_values(sort_col, ascending=False)
            .rename(
                columns={
                    "display_name": "Name",
                    "handle": "Handle",
                    "category": "Category",
                    "msg_total": "Messages",
                    "call_total_calls": "Calls",
                    "call_total_duration_mins": "Call Minutes",
                    "total_interactions": "Total Interactions",
                }
            ),
            use_container_width=True,
            height=300,
            hide_index=True,
        )

        st.markdown("### Contact detail")
        opts = unified.reset_index()
        hc = opts.columns[0]
        opts = opts.sort_values("total_interactions", ascending=False)
        opts["_label"] = opts["display_name"] + " (" + opts[hc].astype(str) + ")"

        pick = st.selectbox(
            "Select contact",
            options=opts[hc].tolist(),
            format_func=lambda h: opts.loc[opts[hc] == h, "_label"].iloc[0],
        )

        if pick:
            cat_lbl = str(cats[pick]) if pick in cats.index else "-"
            row_u = unified.loc[pick]
            ac = row_u.get("area_code")
            loc_str = "Unknown location"
            if ac is not None and not (isinstance(ac, float) and pd.isna(ac)):
                loc = get_area_code_location(str(ac))
                loc_str = f"{loc[2]} (Area Code {ac})" if loc else f"Area Code {ac}"

            _render_contact_header(
                opts.loc[opts[hc] == pick, "display_name"].iloc[0],
                str(pick),
                cat_lbl,
                loc_str,
            )

            msg_stats = msg_analytics.per_contact_stats(messages_df)
            cstats = call_analytics.per_contact_stats(calls_df)

            if pick in msg_stats.index:
                _render_message_stats_card(msg_stats.loc[pick])
            else:
                st.caption("No 1:1 messaging stats for this handle.")

            if pick in cstats.index:
                _render_call_stats_card(cstats.loc[pick])
            else:
                st.caption("No calls for this number.")
