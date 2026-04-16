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
        c.group_id
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

    # Normalize handles
    df["handle_normalized"] = df["handle_raw"].apply(normalize_handle)
    df["is_email_handle"] = df["handle_raw"].apply(
        lambda x: "@" in x if isinstance(x, str) else False
    )

    # Flag reactions vs real messages
    df["is_reaction"] = df["associated_message_type"] != 0

    # Flag group chats
    df["is_group_chat"] = df["group_id"].notna()

    # Clean up columns
    df = df.drop(columns=["date_raw", "attributedBody", "associated_message_type", "group_id"])
    df = df.rename(columns={"handle_raw": "handle_id"})

    total = len(df)
    real = (~df["is_reaction"]).sum()
    groups = df["is_group_chat"].sum()
    logger.info(
        "Loaded %d messages (%d real, %d reactions, %d in group chats)",
        total, real, total - real, groups,
    )

    return df
