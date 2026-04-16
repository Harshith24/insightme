"""Per-contact and global call analytics."""

import pandas as pd

from insightme.data.contacts import is_short_code


def _clean_calls(df: pd.DataFrame) -> pd.DataFrame:
    """Filter out short codes and null phone numbers."""
    clean = df[df["phone_normalized"].notna()].copy()
    clean = clean[~clean["phone_normalized"].apply(is_short_code)]
    return clean


def per_contact_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-contact call statistics.

    Returns DataFrame indexed by phone_normalized with columns:
        total_calls, incoming, outgoing, missed, answered,
        total_duration_mins, avg_duration_mins, max_duration_mins,
        facetime_video, facetime_audio, phone_calls,
        first_call, last_call
    """
    calls = _clean_calls(df)
    if calls.empty:
        return pd.DataFrame()

    results = []
    for phone, group in calls.groupby("phone_normalized"):
        answered = group[group["is_answered"]]

        results.append(
            {
                "phone_normalized": phone,
                "total_calls": len(group),
                "incoming": (~group["is_outgoing"]).sum(),
                "outgoing": group["is_outgoing"].sum(),
                "missed": (~group["is_answered"]).sum(),
                "answered": len(answered),
                "total_duration_mins": round(answered["duration_seconds"].sum() / 60, 1),
                "avg_duration_mins": round(answered["duration_seconds"].mean() / 60, 1) if len(answered) > 0 else 0,
                "max_duration_mins": round(answered["duration_seconds"].max() / 60, 1) if len(answered) > 0 else 0,
                "facetime_video": (group["call_type"] == "facetime_video").sum(),
                "facetime_audio": (group["call_type"] == "facetime_audio").sum(),
                "phone_calls": (group["call_type"] == "phone").sum(),
                "first_call": group["date"].min(),
                "last_call": group["date"].max(),
            }
        )

    return pd.DataFrame(results).set_index("phone_normalized").sort_values(
        "total_calls", ascending=False
    )


def hourly_distribution(df: pd.DataFrame, phone: str | None = None) -> pd.Series:
    """Call count by hour of day."""
    calls = _clean_calls(df)
    if phone:
        calls = calls[calls["phone_normalized"] == phone]
    return calls["date"].dt.hour.value_counts().sort_index()


def daily_distribution(df: pd.DataFrame, phone: str | None = None) -> pd.Series:
    """Call count by day of week."""
    calls = _clean_calls(df)
    if phone:
        calls = calls[calls["phone_normalized"] == phone]
    return calls["date"].dt.dayofweek.value_counts().sort_index()


def hour_day_heatmap(df: pd.DataFrame) -> pd.DataFrame:
    """Call count pivoted by hour x day-of-week."""
    calls = _clean_calls(df)
    calls = calls.copy()
    calls["hour"] = calls["date"].dt.hour
    calls["dow"] = calls["date"].dt.dayofweek

    pivot = calls.groupby(["hour", "dow"]).size().unstack(fill_value=0)
    pivot.columns = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return pivot.reindex(range(24), fill_value=0)


def global_stats(df: pd.DataFrame) -> dict:
    """Top-level aggregate call statistics."""
    calls = _clean_calls(df)
    answered = calls[calls["is_answered"]]

    return {
        "total_calls": len(calls),
        "total_answered": len(answered),
        "total_missed": (~calls["is_answered"]).sum(),
        "total_outgoing": calls["is_outgoing"].sum(),
        "total_incoming": (~calls["is_outgoing"]).sum(),
        "total_duration_hours": round(answered["duration_seconds"].sum() / 3600, 1),
        "avg_duration_mins": round(answered["duration_seconds"].mean() / 60, 1) if len(answered) > 0 else 0,
        "unique_contacts": calls["phone_normalized"].nunique(),
        "facetime_video_count": (calls["call_type"] == "facetime_video").sum(),
        "facetime_audio_count": (calls["call_type"] == "facetime_audio").sum(),
        "phone_count": (calls["call_type"] == "phone").sum(),
        "date_range_start": calls["date"].min(),
        "date_range_end": calls["date"].max(),
    }


FACETIME_TYPES = ("facetime_video", "facetime_audio")


def top_contacts_by_call_types(
    df: pd.DataFrame,
    types: tuple[str, ...],
    n: int = 5,
) -> pd.DataFrame:
    """Count sessions per contact, filtered to given ``call_type`` values."""
    calls = _clean_calls(df)
    if calls.empty:
        return pd.DataFrame()
    mask = calls["call_type"].isin(types)
    if not mask.any():
        return pd.DataFrame()
    sub = calls[mask]
    counts = sub.groupby("phone_normalized").size().sort_values(ascending=False).head(n)
    return (
        pd.DataFrame(
            {
                "phone_normalized": counts.index.astype(str),
                "session_count": counts.values.astype(int),
            }
        ).reset_index(drop=True)
    )


def longest_answered_calls(df: pd.DataFrame) -> dict[str, dict | None]:
    """Longest answered call overall and longest FaceTime (video or audio).

    Each value is a dict with phone_normalized, duration_seconds, call_type, date,
    or None if no matching rows.
    """
    calls = _clean_calls(df)
    answered = calls[calls["is_answered"] & (calls["duration_seconds"] > 0)]
    if answered.empty:
        return {"longest_any": None, "longest_facetime": None}

    def row_dict(r: pd.Series) -> dict:
        return {
            "phone_normalized": str(r["phone_normalized"]),
            "duration_seconds": float(r["duration_seconds"]),
            "call_type": str(r["call_type"]),
            "date": r["date"],
        }

    longest_any = row_dict(answered.nlargest(1, "duration_seconds").iloc[0])

    ft = answered[answered["call_type"].isin(FACETIME_TYPES)]
    if ft.empty:
        return {"longest_any": longest_any, "longest_facetime": None}
    longest_ft = row_dict(ft.nlargest(1, "duration_seconds").iloc[0])
    return {"longest_any": longest_any, "longest_facetime": longest_ft}
