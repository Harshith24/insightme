"""Answer-first insights: who you text/call most, group chats, reply speed, call records."""

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
    return ", ".join(uniq[:max_names]) + f" +{rest} more"


def _fmt_duration_secs(secs: float) -> str:
    if secs >= 3600:
        return f"{secs / 3600:.2f} h"
    if secs >= 60:
        return f"{secs / 60:.1f} min"
    return f"{secs:.0f} s"


def render(
    messages_df: pd.DataFrame | None,
    calls_df: pd.DataFrame | None,
    lookup: dict[str, str],
) -> None:
    st.header("Insights")
    lu = lookup or {}

    if messages_df is None:
        st.warning("Load iMessage for texting insights.")
    else:
        st.subheader("Who you text the most (1:1, excl. short codes)")
        stats = msg_analytics.per_contact_stats(messages_df)
        if stats.empty:
            st.caption("No 1:1 message stats.")
        else:
            top = stats.head(15).reset_index()
            top["Name"] = top["handle_normalized"].astype(str).map(lambda h: contact_label(h, lu))
            top["Handle"] = top["handle_normalized"].astype(str)
            show = top[["Name", "Handle", "total", "sent", "received"]].rename(
                columns={"total": "Messages", "sent": "Sent", "received": "Received"}
            )
            st.dataframe(show, use_container_width=True, hide_index=True)

        st.subheader("Fastest DM replies (their median time after you send)")
        st.caption(
            "Uses 12-hour conversation sessions; requires enough back-and-forth. "
            "Lower median = they reply sooner after you."
        )
        fast = msg_analytics.fastest_dm_responders(
            messages_df, top_n=15, min_their_responses=3
        )
        if fast.empty:
            st.caption("Not enough DM reply data (or increase message history).")
        else:
            f2 = fast.reset_index()
            f2["Name"] = f2["handle_normalized"].astype(str).map(lambda h: contact_label(h, lu))
            f2["Their median"] = (
                f2["their_median_response_secs"].map(
                    lambda s: _fmt_duration_secs(float(s)) if pd.notna(s) else "—"
                )
            )
            f2["n (their replies)"] = f2["their_response_count"].astype(int)
            st.dataframe(
                f2[["Name", "handle_normalized", "Their median", "n (their replies)"]].rename(
                    columns={"handle_normalized": "Handle"}
                ),
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("Top group chats (by message volume)")
        lb = msg_analytics.group_chat_leaderboard(messages_df, top_chats=5)
        if lb.empty:
            st.caption("No group chat messages found.")
        else:
            rows = []
            for _, row in lb.iterrows():
                cid = row["chat_id"]
                keys = msg_analytics.group_chat_participant_keys(messages_df, cid)
                title = _format_group_chat_title(keys, lu)
                top_sk = str(row["top_sender_key"])
                rows.append(
                    {
                        "Chat (participants)": title,
                        "chat_id": cid,
                        "Messages": int(row["message_count"]),
                        "Participants": int(row["participant_count"]),
                        "Most active": _label_sender_key(top_sk, lu),
                        "Their msgs": int(row["top_sender_messages"]),
                    }
                )
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if calls_df is None:
        st.warning("Load Call History for call insights.")
    else:
        st.subheader("Calls by type")
        cg = call_analytics.global_stats(calls_df)
        c1, c2, c3 = st.columns(3)
        c1.metric("Phone", f"{cg.get('phone_count', 0):,}")
        c2.metric("FaceTime video", f"{cg.get('facetime_video_count', 0):,}")
        c3.metric("FaceTime audio", f"{cg.get('facetime_audio_count', 0):,}")

        st.subheader("Who you call the most (phone)")
        phone_top = call_analytics.top_contacts_by_call_types(
            calls_df, ("phone",), n=10
        )
        if phone_top.empty:
            st.caption("No phone calls in filtered data.")
        else:
            p2 = phone_top.copy()
            p2["Name"] = p2["phone_normalized"].map(lambda x: contact_label(str(x), lu))
            st.dataframe(
                p2.rename(columns={"session_count": "Sessions"})[
                    ["Name", "phone_normalized", "Sessions"]
                ].rename(columns={"phone_normalized": "Phone"}),
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("Who you FaceTime the most (video + audio sessions)")
        ft_top = call_analytics.top_contacts_by_call_types(
            calls_df, call_analytics.FACETIME_TYPES, n=10
        )
        if ft_top.empty:
            st.caption("No FaceTime calls in filtered data.")
        else:
            f3 = ft_top.copy()
            f3["Name"] = f3["phone_normalized"].map(lambda x: contact_label(str(x), lu))
            st.dataframe(
                f3.rename(columns={"session_count": "Sessions"})[
                    ["Name", "phone_normalized", "Sessions"]
                ].rename(columns={"phone_normalized": "Phone"}),
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("Longest single calls (answered)")
        highs = call_analytics.longest_answered_calls(calls_df)
        la = highs.get("longest_any")
        lf = highs.get("longest_facetime")
        if la:
            st.write(
                f"**Any type:** {contact_label(la['phone_normalized'], lu)} "
                f"— {_fmt_duration_secs(la['duration_seconds'])} "
                f"({la['call_type']}) @ {la['date']}"
            )
        else:
            st.caption("No answered calls with duration.")
        if lf:
            st.write(
                f"**FaceTime:** {contact_label(lf['phone_normalized'], lu)} "
                f"— {_fmt_duration_secs(lf['duration_seconds'])} "
                f"({lf['call_type']}) @ {lf['date']}"
            )
        else:
            st.caption("No answered FaceTime with duration.")
