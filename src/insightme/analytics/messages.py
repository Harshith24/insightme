"""Per-contact and global message analytics."""

import re
from collections import Counter

import pandas as pd

from insightme.data.contacts import is_short_code

# Common English stop words to exclude from word frequency analysis
STOP_WORDS = frozenset(
    "i me my myself we our ours ourselves you your yours yourself yourselves "
    "he him his himself she her hers herself it its itself they them their "
    "theirs themselves what which who whom this that these those am is are was "
    "were be been being have has had having do does did doing a an the and but "
    "if or because as until while of at by for with about against between "
    "through during before after above below to from up down in out on off "
    "over under again further then once here there when where why how all both "
    "each few more most other some such no nor not only own same so than too "
    "very s t can will just don should now d ll m o re ve y ain aren couldn "
    "didn doesn hadn hasn haven isn ma mightn mustn needn shan shouldn wasn "
    "weren won wouldn yeah yes no ok okay like lol got im ur dont u ya haha "
    "lmao gonna wanna gotta thats its ill ive youre theyre were hes shes "
    "theres whats didnt doesnt isnt wasnt werent wont cant couldnt shouldnt "
    "wouldnt right think know get go going well also would could one two "
    "really just thats".split()
)

# Regex to match emoji unicode ranges
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-A
    "\U00002600-\U000026FF"  # misc symbols
    "]+",
    flags=re.UNICODE,
)


def _real_1on1(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to real (non-reaction) 1:1 messages from non-short-code contacts."""
    mask = ~df["is_reaction"] & ~df["is_group_chat"]
    filtered = df[mask].copy()
    filtered = filtered[~filtered["handle_normalized"].apply(is_short_code)]
    return filtered[filtered["handle_normalized"].notna()]


def per_contact_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-contact message statistics.

    Returns a DataFrame indexed by handle_normalized with columns:
        total, sent, received, ratio, avg_words_sent, avg_words_received,
        first_message, last_message, days_active, streak_max, dry_spell_max
    """
    msgs = _real_1on1(df)
    if msgs.empty:
        return pd.DataFrame()

    results = []
    for handle, group in msgs.groupby("handle_normalized"):
        sent = group[group["is_from_me"] == 1]
        received = group[group["is_from_me"] == 0]

        total = len(group)
        n_sent = len(sent)
        n_received = len(received)
        ratio = n_sent / n_received if n_received > 0 else float("inf")

        # Average word count
        avg_words_sent = (
            sent["text"].dropna().str.split().str.len().mean()
            if len(sent) > 0 and sent["text"].notna().any()
            else 0
        )
        avg_words_received = (
            received["text"].dropna().str.split().str.len().mean()
            if len(received) > 0 and received["text"].notna().any()
            else 0
        )

        first_msg = group["date"].min()
        last_msg = group["date"].max()

        # Streak and dry spell
        dates = group["date"].dt.date.unique()
        dates = sorted(dates)
        streak_max, dry_spell_max = _streak_and_dry_spell(dates)

        results.append(
            {
                "handle_normalized": handle,
                "total": total,
                "sent": n_sent,
                "received": n_received,
                "ratio": round(ratio, 2),
                "avg_words_sent": round(avg_words_sent, 1),
                "avg_words_received": round(avg_words_received, 1),
                "first_message": first_msg,
                "last_message": last_msg,
                "days_active": len(dates),
                "streak_max": streak_max,
                "dry_spell_max": dry_spell_max,
            }
        )

    return pd.DataFrame(results).set_index("handle_normalized").sort_values(
        "total", ascending=False
    )


def _streak_and_dry_spell(dates: list) -> tuple[int, int]:
    """Compute longest consecutive-day streak and longest gap between messages."""
    if len(dates) <= 1:
        return len(dates), 0

    streak = 1
    max_streak = 1
    max_gap = 0

    for i in range(1, len(dates)):
        gap = (dates[i] - dates[i - 1]).days
        if gap == 1:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 1
        if gap > max_gap:
            max_gap = gap

    return max_streak, max_gap


def response_times(df: pd.DataFrame) -> pd.DataFrame:
    """Compute median response times per contact.

    Only measures within conversation sessions (gaps < 12 hours).
    Returns DataFrame indexed by handle_normalized with columns:
        my_median_response_secs, their_median_response_secs
    """
    msgs = _real_1on1(df).sort_values("date")
    session_gap = pd.Timedelta(hours=12)

    results = []
    for handle, group in msgs.groupby("handle_normalized"):
        if len(group) < 2:
            continue

        my_times = []
        their_times = []

        rows = group[["date", "is_from_me"]].values
        for i in range(1, len(rows)):
            gap = rows[i][0] - rows[i - 1][0]
            gap_td = pd.Timedelta(gap)

            if gap_td >= session_gap or gap_td <= pd.Timedelta(0):
                continue

            prev_from_me = rows[i - 1][1]
            curr_from_me = rows[i][1]

            # Sender changed — this is a response
            if prev_from_me != curr_from_me:
                secs = gap_td.total_seconds()
                if curr_from_me == 1:
                    my_times.append(secs)
                else:
                    their_times.append(secs)

        results.append(
            {
                "handle_normalized": handle,
                "my_median_response_secs": (
                    pd.Series(my_times).median() if my_times else None
                ),
                "their_median_response_secs": (
                    pd.Series(their_times).median() if their_times else None
                ),
                "my_response_count": len(my_times),
                "their_response_count": len(their_times),
            }
        )

    return pd.DataFrame(results).set_index("handle_normalized") if results else pd.DataFrame()


def top_words(df: pd.DataFrame, handle: str | None = None, top_n: int = 30) -> list[tuple[str, int]]:
    """Get most frequent words for a contact or globally.

    Excludes stop words. Returns list of (word, count) tuples.
    """
    msgs = _real_1on1(df)
    if handle:
        msgs = msgs[msgs["handle_normalized"] == handle]

    texts = msgs[msgs["is_from_me"] == 1]["text"].dropna()
    words = texts.str.lower().str.findall(r"[a-z']+").explode()
    words = words[~words.isin(STOP_WORDS) & (words.str.len() > 1)]

    return words.value_counts().head(top_n).items()


def top_emojis(df: pd.DataFrame, handle: str | None = None, top_n: int = 20) -> list[tuple[str, int]]:
    """Get most used emojis for a contact or globally."""
    msgs = _real_1on1(df)
    if handle:
        msgs = msgs[msgs["handle_normalized"] == handle]

    texts = msgs[msgs["is_from_me"] == 1]["text"].dropna()
    emojis = texts.str.findall(EMOJI_PATTERN).explode().dropna()

    return emojis.value_counts().head(top_n).items()


def hourly_distribution(df: pd.DataFrame, handle: str | None = None) -> pd.Series:
    """Message count by hour of day (0-23)."""
    msgs = _real_1on1(df)
    if handle:
        msgs = msgs[msgs["handle_normalized"] == handle]
    return msgs["date"].dt.hour.value_counts().sort_index()


def daily_distribution(df: pd.DataFrame, handle: str | None = None) -> pd.Series:
    """Message count by day of week (Monday=0 to Sunday=6)."""
    msgs = _real_1on1(df)
    if handle:
        msgs = msgs[msgs["handle_normalized"] == handle]
    return msgs["date"].dt.dayofweek.value_counts().sort_index()


def hour_day_heatmap(df: pd.DataFrame, handle: str | None = None) -> pd.DataFrame:
    """Message count pivoted by hour (rows) x day-of-week (columns)."""
    msgs = _real_1on1(df)
    if handle:
        msgs = msgs[msgs["handle_normalized"] == handle]

    msgs = msgs.copy()
    msgs["hour"] = msgs["date"].dt.hour
    msgs["dow"] = msgs["date"].dt.dayofweek

    pivot = msgs.groupby(["hour", "dow"]).size().unstack(fill_value=0)
    pivot.columns = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return pivot.reindex(range(24), fill_value=0)


def weekly_volume(df: pd.DataFrame, handle: str | None = None) -> pd.Series:
    """Weekly message count as a time series."""
    msgs = _real_1on1(df)
    if handle:
        msgs = msgs[msgs["handle_normalized"] == handle]
    return msgs.set_index("date").resample("W").size()


def global_stats(df: pd.DataFrame) -> dict:
    """Top-level aggregate statistics."""
    msgs = _real_1on1(df)
    return {
        "total_messages": len(msgs),
        "total_sent": (msgs["is_from_me"] == 1).sum(),
        "total_received": (msgs["is_from_me"] == 0).sum(),
        "unique_contacts": msgs["handle_normalized"].nunique(),
        "date_range_start": msgs["date"].min(),
        "date_range_end": msgs["date"].max(),
        "messages_with_text": msgs["text"].notna().sum(),
    }


def _group_chat_messages(df: pd.DataFrame) -> pd.DataFrame:
    """Real (non-reaction) group chat rows with a stable sender key."""
    gm = df[~df["is_reaction"] & df["is_group_chat"]].copy()
    if gm.empty:
        return gm
    gm = gm[gm["chat_id"].notna()]
    if gm.empty:
        return gm

    def sender_key(row) -> str:
        h = row["handle_normalized"]
        if pd.notna(h) and str(h).strip():
            return str(h)
        return "__you__" if int(row["is_from_me"]) == 1 else "__unknown__"

    gm["sender_key"] = gm.apply(sender_key, axis=1)
    return gm


def group_chat_leaderboard(
    df: pd.DataFrame,
    top_chats: int = 5,
) -> pd.DataFrame:
    """Top group chats by message volume with most active sender per chat.

    Columns: chat_id, message_count, participant_count, top_sender_key,
    top_sender_messages
    """
    gm = _group_chat_messages(df)
    if gm.empty:
        return pd.DataFrame()

    chat_sizes = gm.groupby("chat_id").size().sort_values(ascending=False).head(top_chats)
    rows = []
    for chat_id, _ in chat_sizes.items():
        sub = gm[gm["chat_id"] == chat_id]
        vc = sub.groupby("sender_key").size().sort_values(ascending=False)
        top_key = vc.index[0]
        rows.append(
            {
                "chat_id": int(chat_id) if pd.notna(chat_id) else chat_id,
                "message_count": len(sub),
                "participant_count": sub["sender_key"].nunique(),
                "top_sender_key": top_key,
                "top_sender_messages": int(vc.iloc[0]),
            }
        )
    return pd.DataFrame(rows)


def group_chat_participant_keys(df: pd.DataFrame, chat_id) -> list[str]:
    """Unique sender keys for a group chat (for building a human-readable label)."""
    gm = _group_chat_messages(df)
    if gm.empty:
        return []
    sub = gm[gm["chat_id"] == chat_id]
    if sub.empty:
        return []
    return sorted(sub["sender_key"].unique().tolist(), key=str)


def fastest_dm_responders(
    df: pd.DataFrame,
    top_n: int = 10,
    min_their_responses: int = 3,
) -> pd.DataFrame:
    """Contacts with the lowest median time for *them* to reply after you (DMs only).

    Uses the same session logic as ``response_times`` (12h gap). Rows are sorted
    by ``their_median_response_secs`` ascending (fastest first).
    """
    rt = response_times(df)
    if rt.empty:
        return pd.DataFrame()
    rt = rt[rt["their_median_response_secs"].notna()].copy()
    rt = rt[rt["their_response_count"] >= min_their_responses]
    rt = rt.sort_values("their_median_response_secs", ascending=True).head(top_n)
    return rt
