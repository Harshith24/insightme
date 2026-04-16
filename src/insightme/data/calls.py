"""Call History database reader.

Reads ~/Library/Application Support/CallHistoryDB/CallHistory.storedata,
a Core Data SQLite file with call records.
"""

import logging
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd

from insightme.data.contacts import normalize_phone

logger = logging.getLogger(__name__)

CALL_DB_PATH = (
    Path.home() / "Library" / "Application Support" / "CallHistoryDB" / "CallHistory.storedata"
)

# Apple Core Data epoch: 2001-01-01 in Unix seconds
APPLE_EPOCH_OFFSET = 978307200

# Call type mapping
CALL_TYPES = {
    1: "phone",
    8: "facetime_video",
    16: "facetime_audio",
}


def _copy_db(src: Path, tmp_dir: str) -> Path:
    """Copy a database file (and its WAL/SHM) to a temp directory."""
    dest = Path(tmp_dir) / src.name
    shutil.copy2(src, dest)
    for suffix in ("-wal", "-shm"):
        wal = src.parent / (src.name + suffix)
        if wal.exists():
            shutil.copy2(wal, Path(tmp_dir) / (src.name + suffix))
    return dest


def load_calls(db_path: Path | None = None) -> pd.DataFrame:
    """Load call history into a clean DataFrame.

    Returns a DataFrame with columns:
        date, phone_normalized, duration_seconds, is_outgoing,
        is_answered, call_type
    """
    src = db_path or CALL_DB_PATH

    if not src.exists():
        raise FileNotFoundError(
            f"Call History database not found at {src}. "
            "Make sure you're on macOS with Phone/FaceTime configured."
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
            return _query_calls(conn)
        finally:
            conn.close()


def _query_calls(conn: sqlite3.Connection) -> pd.DataFrame:
    """Query the ZCALLRECORD table and build a clean DataFrame."""
    query = """
    SELECT
        ZDATE as date_raw,
        ZADDRESS as phone_raw,
        ZDURATION as duration_seconds,
        ZORIGINATED as is_outgoing,
        ZANSWERED as is_answered,
        ZCALLTYPE as call_type_raw
    FROM ZCALLRECORD
    ORDER BY ZDATE
    """

    df = pd.read_sql_query(query, conn)

    # Convert Core Data timestamp (seconds since 2001-01-01)
    df["date"] = pd.to_datetime(
        df["date_raw"] + APPLE_EPOCH_OFFSET, unit="s", utc=True
    ).dt.tz_convert("US/Eastern").dt.tz_localize(None)

    # Normalize phone numbers
    df["phone_normalized"] = df["phone_raw"].apply(normalize_phone)

    # Map call types
    df["call_type"] = df["call_type_raw"].map(CALL_TYPES).fillna("other")

    # Convert flags to bool
    df["is_outgoing"] = df["is_outgoing"] == 1
    df["is_answered"] = df["is_answered"] == 1

    # Clean up
    df = df.drop(columns=["date_raw", "phone_raw", "call_type_raw"])

    logger.info(
        "Loaded %d calls (%d answered, %d missed)",
        len(df),
        df["is_answered"].sum(),
        (~df["is_answered"]).sum(),
    )

    return df
