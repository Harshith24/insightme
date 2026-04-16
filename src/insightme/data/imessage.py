"""iMessage chat.db reader.

Copies ~/Library/Messages/chat.db to a temp directory before reading
to avoid locking the live database while Messages.app is open.
"""

import logging
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd

from insightme.data.contacts import normalize_handle

logger = logging.getLogger(__name__)

CHAT_DB_PATH = Path.home() / "Library" / "Messages" / "chat.db"

# Apple epoch: 2001-01-01 00:00:00 UTC in Unix seconds
APPLE_EPOCH_OFFSET = 978307200


def _extract_attributed_body(blob: bytes | None) -> str | None:
    """Extract text from an NSAttributedString attributedBody BLOB.

    On macOS 13+, many messages have NULL `text` but store content in
    the `attributedBody` column as a serialized NSAttributedString.
    """
    if not blob:
        return None
    try:
        parts = blob.split(b"NSString")
        if len(parts) < 2:
            return None
        text = parts[1]
        text = text[5:]  # skip header bytes
        length = int.from_bytes(text[:1], "little")
        if length == 0x81:
            length = int.from_bytes(text[1:3], "little")
            text = text[3 : 3 + length]
        else:
            text = text[1 : 1 + length]
        return text.decode("utf-8", errors="replace")
    except Exception:
        return None


def _copy_db(src: Path, tmp_dir: str) -> Path:
    """Copy a database file (and its WAL/SHM) to a temp directory."""
    dest = Path(tmp_dir) / src.name
    shutil.copy2(src, dest)
    # Also copy WAL and SHM files if they exist
    for suffix in ("-wal", "-shm"):
        wal = src.parent / (src.name + suffix)
        if wal.exists():
            shutil.copy2(wal, Path(tmp_dir) / (src.name + suffix))
    return dest


def _impute_peer_handles_in_dms(df: pd.DataFrame) -> pd.DataFrame:
    """Fill NULL handle_raw for outgoing rows where SQLite has no handle join.

    Apple stores ``handle_id = 0`` on many sent messages. We only impute when the
    chat looks like a **1:1** thread: ``chat_participant_count <= 2`` and all
    received (non-reaction) messages share a **single** distinct handle — so we
    never assign a fake peer in multi-party chats.
    """
    if df.empty or "handle_raw" not in df.columns:
        return df

    recv = df[
        (df["associated_message_type"] == 0)
        & (df["is_from_me"] == 0)
        & df["chat_id"].notna()
        & df["handle_raw"].notna()
        & (df["handle_raw"].astype(str).str.len() > 0)
    ]
    if recv.empty:
        return df

    n_peers = recv.groupby("chat_id")["handle_raw"].nunique()
    single_peer_chats = set(n_peers[n_peers == 1].index.tolist())

    jcnt = df.groupby("chat_id")["chat_participant_count"].first()
    safe_chats = {
        cid
        for cid in single_peer_chats
        if pd.notna(cid) and int(jcnt.get(cid, 99) or 0) <= 2
    }

    def _pick_peer(series: pd.Series) -> str:
        return str(series.iloc[0])

    recv_ok = recv[recv["chat_id"].isin(safe_chats)]
    if recv_ok.empty:
        return df

    peer_by_chat = recv_ok.groupby("chat_id", sort=False)["handle_raw"].agg(_pick_peer)

    miss = (
        (df["associated_message_type"] == 0)
        & (df["is_from_me"] == 1)
        & df["chat_id"].notna()
        & df["chat_id"].map(lambda x: x in safe_chats if pd.notna(x) else False)
        & (df["handle_raw"].isna() | (df["handle_raw"].astype(str).str.strip() == ""))
    )
    if not miss.any():
        return df

    out = df.copy()
    fill = out.loc[miss, "chat_id"].map(peer_by_chat)
    out.loc[miss, "handle_raw"] = fill.values
    unfilled = miss & out["handle_raw"].isna()
    if unfilled.any():
        logger.debug(
            "%d outgoing rows still lack a peer handle after impute",
            int(unfilled.sum()),
        )
    return out


def load_messages(db_path: Path | None = None) -> pd.DataFrame:
    """Load all iMessage data into a clean DataFrame.

    Returns a DataFrame with columns:
        message_id, date, text, is_from_me, handle_id, handle_normalized,
        is_reaction, chat_id, is_group_chat, is_email_handle
    """
    src = db_path or CHAT_DB_PATH

    if not src.exists():
        raise FileNotFoundError(
            f"iMessage database not found at {src}. "
            "Make sure you're on macOS with Messages configured."
        )

    with tempfile.TemporaryDirectory(prefix="insightme_") as tmp_dir:
        try:
            db_copy = _copy_db(src, tmp_dir)
        except PermissionError:
            raise PermissionError(
                f"Cannot read {src}. Grant Full Disk Access to your terminal:\n"
                "  System Settings → Privacy & Security → Full Disk Access → add your terminal app"
            )

        conn = sqlite3.connect(str(db_copy))
        try:
            return _query_messages(conn)
        finally:
            conn.close()


def _query_messages(conn: sqlite3.Connection) -> pd.DataFrame:
    """Run queries against the copied database and build the DataFrame."""
    query = """
    SELECT
        m.ROWID as message_id,
        m.date as date_raw,
        m.text,
        m.attributedBody,
        m.is_from_me,
        m.associated_message_type,
        h.id as handle_raw,
        cmj.chat_id,
        c.group_id,
        (
            SELECT COUNT(*)
            FROM chat_handle_join ch
            WHERE cmj.chat_id IS NOT NULL AND ch.chat_id = cmj.chat_id
        ) AS chat_participant_count
    FROM message m
    LEFT JOIN handle h ON m.handle_id = h.ROWID
    LEFT JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
    LEFT JOIN chat c ON cmj.chat_id = c.ROWID
    ORDER BY m.date
    """

    df = pd.read_sql_query(query, conn)

    # Convert Apple nanosecond timestamps to datetime
    df["date"] = pd.to_datetime(
        df["date_raw"] / 1e9 + APPLE_EPOCH_OFFSET, unit="s", utc=True
    ).dt.tz_convert("US/Eastern").dt.tz_localize(None)

    # Extract text from attributedBody where text is NULL
    unparseable_count = 0
    mask = df["text"].isna() & df["attributedBody"].notna()
    if mask.any():
        extracted = df.loc[mask, "attributedBody"].apply(_extract_attributed_body)
        still_null = extracted.isna().sum()
        unparseable_count = int(still_null)
        df.loc[mask, "text"] = extracted

    if unparseable_count > 0:
        logger.warning(
            "Could not parse attributedBody for %d messages", unparseable_count
        )

    # Outgoing messages often have message.handle_id = 0, so the handle JOIN is NULL.
    # For 1:1 chats, infer the peer handle from received rows in the same chat_id.
    df = _impute_peer_handles_in_dms(df)

    # Normalize handles
    df["handle_normalized"] = df["handle_raw"].apply(normalize_handle)
    df["is_email_handle"] = df["handle_raw"].apply(
        lambda x: "@" in x if isinstance(x, str) else False
    )

    # Flag reactions vs real messages
    df["is_reaction"] = df["associated_message_type"] != 0

    # Group chat: more than two participants in chat_handle_join OR more than two
    # distinct normalized handles on real messages (covers under-joined groups).
    df["chat_participant_count"] = (
        pd.to_numeric(df["chat_participant_count"], errors="coerce").fillna(0).astype(int)
    )
    real = df[~df["is_reaction"] & df["chat_id"].notna()]
    distinct_handles = real.groupby("chat_id")["handle_normalized"].apply(
        lambda s: int(s.dropna().nunique())
    )
    join_cnt = df.groupby("chat_id")["chat_participant_count"].transform("first")
    dist_cnt = df["chat_id"].map(distinct_handles).fillna(0).astype(int)
    df["is_group_chat"] = (join_cnt > 2) | (dist_cnt > 2)

    # Clean up columns
    df = df.drop(
        columns=[
            "date_raw",
            "attributedBody",
            "associated_message_type",
            "group_id",
            "chat_participant_count",
        ]
    )
    df = df.rename(columns={"handle_raw": "handle_id"})

    total = len(df)
    real = (~df["is_reaction"]).sum()
    groups = df["is_group_chat"].sum()
    logger.info(
        "Loaded %d messages (%d real, %d reactions, %d in group chats)",
        total, real, total - real, groups,
    )

    return df
