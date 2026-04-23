"""Answer-first insights for messages and calls: responders, groups, and longest sessions."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from insightme.analytics import calls as call_analytics
from insightme.analytics import messages as msg_analytics
from insightme.data.addressbook import contact_label


def _label_sender_key(key: str, lookup: dict[str, str]) -> str:
    if key == "__you__":
        return "You"
    if key == "__unknown__":
        return "Unknown"
    return contact_label(str(key), lookup)


def _format_group_chat_title(keys: list[str], lookup: dict[str, str], max_names: int = 3) -> str:
    labels = [_label_sender_key(k, lookup) for k in keys]
    uniq: list[str] = []
    seen: set[str] = set()
    for lab in labels:
        if lab not in seen:
            seen.add(lab)
            uniq.append(lab)
    uniq.sort(key=lambda x: (-len(x), x))
    if len(uniq) <= max_names:
        return ", ".join(uniq)
    rest = len(uniq) - max_names
    return ", ".join(uniq[:max_names]) + f" + {rest} more"


def _fmt_duration_secs(secs: float) -> str:
    if secs >= 3600:
        return f"{secs / 3600:.2f} h"
    if secs >= 60:
        return f"{secs / 60:.1f} min"
    return f"{secs:.0f} s"


def _record_card(title: str, value: str, subtitle: str) -> None:
    st.markdown(
        """
<div class='page-shell' style="padding: 0.9rem; margin-bottom: 0.7rem;">
  <div class='kicker'>{title}</div>
  <h3 style="margin: 0.1rem 0 0.4rem 0;">{value}</h3>
  <div class='lead-copy'>{subtitle}</div>
</div>
""".format(title=title, value=value, subtitle=subtitle),
        unsafe_allow_html=True,
    )


def render(
    messages_df: pd.DataFrame | None,
    calls_df: pd.DataFrame | None,
    lookup: dict[str, str],
) -> None:
    st.markdown("<div class='kicker'>Deep Dive</div>", unsafe_allow_html=True)
    st.markdown("## Conversation behavior")
    st.markdown(
        "<div class='lead-copy'>Read response speed, group chatter patterns, and standout call sessions in one place.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='soft-rule'></div>", unsafe_allow_html=True)
    lu = lookup or {}

    left, right = st.columns([1.55, 0.85])

    with left:
        if messages_df is None:
            st.warning("Load iMessage for texting insights.")
        else:
            st.markdown("### Fastest responders")
            st.caption("Sorted by lowest median reply delay after your outbound messages.")
            fast = msg_analytics.fastest_dm_responders(messages_df, top_n=10, min_their_responses=3)
            if fast.empty:
                st.caption("Not enough direct message reply history to score responsiveness.")
            else:
                f2 = fast.reset_index()
                f2["Name"] = f2["handle_normalized"].astype(str).map(lambda h: contact_label(h, lu))
                f2["Median Time"] = f2["their_median_response_secs"].map(
                    lambda s: _fmt_duration_secs(float(s)) if pd.notna(s) else "—"
                )
                ranked = (
                    f2[["Name", "Median Time", "their_response_count"]]
                    .rename(columns={"their_response_count": "Replies"})
                    .copy()
                )
                ranked.insert(0, "Rank", range(1, len(ranked) + 1))
                st.dataframe(
                    ranked,
                    use_container_width=True,
                    hide_index=True,
                )

            st.markdown("### Group chat activity")
            lb = msg_analytics.group_chat_leaderboard(messages_df, top_chats=5)
            if lb.empty:
                st.caption("No qualifying group activity yet.")
            else:
                rows = []
                for _, row in lb.iterrows():
                    cid = row["chat_id"]
                    keys = msg_analytics.group_chat_participant_keys(messages_df, cid)
                    chat_name = str(row.get("chat_name") or "").strip()
                    title = chat_name if chat_name else _format_group_chat_title(keys, lu)
                    rows.append(
                        {
                            "Chat": title,
                            "Messages": int(row["message_count"]),
                            "Most Active": _label_sender_key(str(row["top_sender_key"]), lu),
                        }
                    )
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with right:
        if calls_df is None:
            st.warning("Load Call History for call insights.")
        else:
            st.markdown("### Call profile")
            cg = call_analytics.global_stats(calls_df)
            c1, c2 = st.columns(2)
            c1.metric("Phone", f"{cg.get('phone_count', 0):,}")
            c2.metric("FaceTime Video", f"{cg.get('facetime_video_count', 0):,}")
            c3, c4 = st.columns(2)
            c3.metric("FaceTime Audio", f"{cg.get('facetime_audio_count', 0):,}")
            c4.metric("Total Hours", f"{cg.get('total_duration_hours', 0):,}")

            highs = call_analytics.longest_answered_calls(calls_df)
            la = highs.get("longest_any")
            lf = highs.get("longest_facetime")

            if la:
                _record_card(
                    "Longest answered call",
                    contact_label(la["phone_normalized"], lu),
                    f"{_fmt_duration_secs(la['duration_seconds'])} · {la['call_type']} · {la['date'].strftime('%b %d, %Y')}",
                )
            else:
                st.caption("No answered call records available.")

            if lf:
                _record_card(
                    "Longest FaceTime",
                    contact_label(lf["phone_normalized"], lu),
                    f"{_fmt_duration_secs(lf['duration_seconds'])} · {lf['call_type']} · {lf['date'].strftime('%b %d, %Y')}",
                )
            else:
                st.caption("No FaceTime records available.")
