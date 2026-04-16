#!/usr/bin/env python3
"""Quick verification script for the insightme data + analytics layers.

Run: python test_data_layer.py
Requires Full Disk Access for the terminal.
"""

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

# Add src to path for direct execution
sys.path.insert(0, "src")

from insightme.data.contacts import normalize_phone, normalize_handle, extract_area_code
from insightme.data.imessage import load_messages
from insightme.data.calls import load_calls
from insightme.analytics import messages as msg_analytics
from insightme.analytics import calls as call_analytics
from insightme.analytics import relationships as rel_analytics


def test_normalization():
    print("=== Phone Normalization ===")
    tests = [
        ("+15551234567", "5551234567"),
        ("(555) 123-4567", "5551234567"),
        ("555-123-4567", "5551234567"),
        ("15551234567", "5551234567"),
        ("5551234567", "5551234567"),
        ("user@example.com", None),  # not a phone number
    ]
    for raw, expected in tests:
        result = normalize_phone(raw)
        status = "OK" if result == expected else f"FAIL (got {result})"
        print(f"  {raw:25s} -> {result}  {status}")

    print("\n=== Handle Normalization ===")
    print(f"  email: {normalize_handle('User@Example.COM')}")
    print(f"  phone: {normalize_handle('+1 (555) 123-4567')}")

    print("\n=== Area Code Extraction ===")
    print(f"  5551234567 -> area code {extract_area_code('5551234567')}")
    print()


def test_imessage(df):
    print("=== iMessage Data ===")
    real = df[~df["is_reaction"]]
    one_on_one = real[~real["is_group_chat"]]

    print(f"  Total messages: {len(df):,}")
    print(f"  Real messages (excl. reactions): {len(real):,}")
    print(f"  Reactions/tapbacks: {df['is_reaction'].sum():,}")
    print(f"  1:1 messages: {len(one_on_one):,}")
    print(f"  Group chat messages: {real['is_group_chat'].sum():,}")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Messages with text: {df['text'].notna().sum():,}")
    print(f"  Messages without text: {df['text'].isna().sum():,}")

    print("\n  Top 10 contacts by message count (1:1, excl. reactions):")
    top = (
        one_on_one.groupby("handle_normalized")
        .size()
        .sort_values(ascending=False)
        .head(10)
    )
    for handle, count in top.items():
        print(f"    {handle:30s}  {count:,} messages")
    print()


def test_calls():
    print("=== Call History ===")
    try:
        df = load_calls()
    except (PermissionError, FileNotFoundError) as e:
        print(f"  Skipped: {e}")
        return

    print(f"  Total calls: {len(df):,}")
    print(f"  Answered: {df['is_answered'].sum():,}")
    print(f"  Missed: {(~df['is_answered']).sum():,}")
    print(f"  Outgoing: {df['is_outgoing'].sum():,}")
    print(f"  Incoming: {(~df['is_outgoing']).sum():,}")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

    answered = df[df["is_answered"]]
    if len(answered) > 0:
        total_hrs = answered["duration_seconds"].sum() / 3600
        print(f"  Total call time: {total_hrs:.1f} hours")

    print("\n  Calls by type:")
    for ctype, count in df["call_type"].value_counts().items():
        print(f"    {ctype:20s}  {count:,}")

    print("\n  Top 10 contacts by call count:")
    top = (
        df.groupby("phone_normalized")
        .size()
        .sort_values(ascending=False)
        .head(10)
    )
    for phone, count in top.items():
        print(f"    {phone:30s}  {count:,} calls")
    print()


def test_analytics(messages_df, calls_df):
    print("=== Message Analytics ===")
    stats = msg_analytics.per_contact_stats(messages_df)
    print(f"  Contacts with 1:1 stats: {len(stats)}")
    if not stats.empty:
        top = stats.head(5)
        print("\n  Top 5 contacts (1:1, excl. short codes):")
        for handle, row in top.iterrows():
            print(
                f"    {handle:20s}  {int(row['total']):>5} msgs  "
                f"ratio={row['ratio']:.1f}  "
                f"streak={int(row['streak_max'])}d  "
                f"dry={int(row['dry_spell_max'])}d"
            )

    rt = msg_analytics.response_times(messages_df)
    if not rt.empty:
        print("\n  Response times (top contacts):")
        for handle, row in rt.head(5).iterrows():
            my_rt = f"{row['my_median_response_secs']/60:.1f}m" if row['my_median_response_secs'] else "N/A"
            their_rt = f"{row['their_median_response_secs']/60:.1f}m" if row['their_median_response_secs'] else "N/A"
            print(f"    {handle:20s}  me: {my_rt:>8}  them: {their_rt:>8}")

    gstats = msg_analytics.global_stats(messages_df)
    print(f"\n  Global: {gstats['total_messages']} messages, {gstats['unique_contacts']} contacts")

    print("\n=== Call Analytics ===")
    cstats = call_analytics.per_contact_stats(calls_df)
    print(f"  Contacts with call stats: {len(cstats)}")
    if not cstats.empty:
        print("\n  Top 5 contacts by call count:")
        for phone, row in cstats.head(5).iterrows():
            print(
                f"    {phone:20s}  {int(row['total_calls']):>4} calls  "
                f"{row['total_duration_mins']:.0f}min  "
                f"FT:{int(row['facetime_video'])}v/{int(row['facetime_audio'])}a"
            )

    cglobal = call_analytics.global_stats(calls_df)
    print(f"\n  Global: {cglobal['total_calls']} calls, {cglobal['total_duration_hours']}h total")

    print("\n=== Relationship Analytics ===")
    unified = rel_analytics.unified_contacts(messages_df, calls_df)
    print(f"  Unified contacts: {len(unified)}")

    categories = rel_analytics.categorize_contacts(unified)
    print(f"\n  Categories:")
    for cat, count in categories.value_counts().items():
        print(f"    {cat:15s}  {count}")

    fading = rel_analytics.fading_connections(messages_df)
    print(f"\n  Fading connections: {len(fading)}")
    if not fading.empty:
        for handle, row in fading.iterrows():
            print(f"    {handle:20s}  peak={row['peak_monthly']}/mo → now={row['current_monthly']}/mo")

    area = rel_analytics.area_code_summary(unified)
    print(f"\n  Area codes mapped: {len(area)}")
    if not area.empty:
        for _, row in area.head(5).iterrows():
            print(f"    {row['area_code']}  {row['region']:25s}  {int(row['contact_count'])} contacts")
    print()


if __name__ == "__main__":
    test_normalization()

    messages_df = None
    calls_df = None

    try:
        messages_df = load_messages()
        test_imessage()
    except (PermissionError, FileNotFoundError) as e:
        print(f"=== iMessage Data ===\n  Skipped: {e}\n")

    try:
        calls_df = load_calls()
        test_calls()
    except (PermissionError, FileNotFoundError) as e:
        print(f"=== Call History ===\n  Skipped: {e}\n")

    if messages_df is not None and calls_df is not None:
        test_analytics(messages_df, calls_df)
    else:
        print("=== Analytics ===\n  Skipped: need both databases for analytics\n")

    print("Done!")
