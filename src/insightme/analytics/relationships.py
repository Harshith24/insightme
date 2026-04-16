"""Unified cross-source analytics — combining messages and calls per contact."""

import pandas as pd

from insightme.analytics import messages as msg_analytics
from insightme.analytics import calls as call_analytics
from insightme.data.contacts import extract_area_code


def unified_contacts(messages_df: pd.DataFrame, calls_df: pd.DataFrame) -> pd.DataFrame:
    """Build a unified view of each contact across messages and calls.

    Joins on normalized phone number. Returns a DataFrame with combined stats.
    """
    msg_stats = msg_analytics.per_contact_stats(messages_df)
    call_stats = call_analytics.per_contact_stats(calls_df)

    # Rename to avoid collisions
    msg_cols = msg_stats.add_prefix("msg_")
    call_cols = call_stats.add_prefix("call_")

    # Full outer join on normalized phone/handle
    unified = msg_cols.join(call_cols, how="outer")

    # Fill NaN for contacts that only appear in one source
    for col in msg_cols.columns:
        if unified[col].dtype in ("float64", "int64", "Int64"):
            unified[col] = unified[col].fillna(0)
    for col in call_cols.columns:
        if unified[col].dtype in ("float64", "int64", "Int64"):
            unified[col] = unified[col].fillna(0)

    # Compute derived fields
    unified["total_interactions"] = unified.get("msg_total", 0) + unified.get("call_total_calls", 0)

    # First/last contact across both sources
    unified["first_contact"] = unified[
        ["msg_first_message", "call_first_call"]
    ].min(axis=1)
    unified["last_contact"] = unified[
        ["msg_last_message", "call_last_call"]
    ].max(axis=1)
    unified["months_known"] = (
        (unified["last_contact"] - unified["first_contact"]).dt.days / 30.44
    ).round(1)

    # Area code
    unified["area_code"] = unified.index.map(extract_area_code)

    return unified.sort_values("total_interactions", ascending=False)


def categorize_contacts(unified: pd.DataFrame) -> pd.Series:
    """Categorize each contact as text-heavy, call-heavy, both, or dormant.

    Uses percentile-based thresholds relative to the user's own data.
    """
    msg_count = unified.get("msg_total", pd.Series(0, index=unified.index))
    call_mins = unified.get("call_total_duration_mins", pd.Series(0, index=unified.index))

    # Use median as threshold — above median = "high"
    msg_threshold = msg_count[msg_count > 0].median() if (msg_count > 0).any() else 1
    call_threshold = call_mins[call_mins > 0].median() if (call_mins > 0).any() else 1

    high_msg = msg_count >= msg_threshold
    high_call = call_mins >= call_threshold
    no_msg = msg_count == 0
    no_call = call_mins == 0

    # Dormant: no activity in last 90 days
    now = pd.Timestamp.now()
    last_contact = unified.get("last_contact", pd.Series(pd.NaT, index=unified.index))
    dormant = (now - last_contact).dt.days > 90

    categories = pd.Series("other", index=unified.index)
    categories[high_msg & ~high_call] = "text-heavy"
    categories[high_call & ~high_msg] = "call-heavy"
    categories[high_msg & high_call] = "both"
    categories[dormant & ~high_msg & ~high_call] = "dormant"

    return categories


def fading_connections(messages_df: pd.DataFrame, months: int = 6) -> pd.DataFrame:
    """Find contacts whose monthly message count has been declining for 3+ months.

    Returns DataFrame with contact, monthly counts, and trend direction.
    """
    from insightme.data.contacts import is_short_code

    msgs = messages_df[
        ~messages_df["is_reaction"]
        & ~messages_df["is_group_chat"]
        & messages_df["handle_normalized"].notna()
    ].copy()
    msgs = msgs[~msgs["handle_normalized"].apply(is_short_code)]

    if msgs.empty:
        return pd.DataFrame()

    # Monthly message counts per contact for last N months
    cutoff = pd.Timestamp.now() - pd.DateOffset(months=months)
    recent = msgs[msgs["date"] >= cutoff]

    if recent.empty:
        return pd.DataFrame()

    recent = recent.copy()
    recent["month"] = recent["date"].dt.to_period("M")

    monthly = recent.groupby(["handle_normalized", "month"]).size().unstack(fill_value=0)

    # Need at least 3 months of data to detect a trend
    if monthly.shape[1] < 3:
        return pd.DataFrame()

    fading = []
    for handle in monthly.index:
        counts = monthly.loc[handle].values
        # Check last 3 months are strictly declining
        last3 = counts[-3:]
        if last3[0] > last3[1] > last3[2] and last3[0] > 0:
            fading.append(
                {
                    "handle_normalized": handle,
                    "months_declining": 3,
                    "peak_monthly": int(counts.max()),
                    "current_monthly": int(counts[-1]),
                    "trend": list(int(c) for c in counts),
                }
            )

    return pd.DataFrame(fading).set_index("handle_normalized") if fading else pd.DataFrame()


def area_code_summary(unified: pd.DataFrame) -> pd.DataFrame:
    """Aggregate contacts by area code for the map view.

    Returns DataFrame with area_code, count, lat, lng, region.
    """
    from insightme.data.area_codes import get_area_code_location

    codes = unified["area_code"].dropna()
    counts = codes.value_counts()

    rows = []
    for code, count in counts.items():
        loc = get_area_code_location(code)
        if loc:
            lat, lng, region = loc
            rows.append(
                {
                    "area_code": code,
                    "contact_count": count,
                    "lat": lat,
                    "lng": lng,
                    "region": region,
                }
            )

    return pd.DataFrame(rows) if rows else pd.DataFrame()
