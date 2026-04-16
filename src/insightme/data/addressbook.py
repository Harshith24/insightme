"""macOS Contacts (Address Book) reader — maps phones and emails to display names.

Reads SQLite databases under ~/Library/Application Support/AddressBook/ (copied to
temp first, same pattern as iMessage and Call History).
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
import tempfile
from pathlib import Path

from insightme.data.contacts import normalize_handle, normalize_phone

logger = logging.getLogger(__name__)

ADDRESSBOOK_ROOT = Path.home() / "Library" / "Application Support" / "AddressBook"


def _find_abcddb_files() -> list[Path]:
    """Return all Address Book SQLite files (iCloud/local sources)."""
    if not ADDRESSBOOK_ROOT.is_dir():
        return []
    found: set[Path] = set()
    for p in ADDRESSBOOK_ROOT.rglob("*.abcddb"):
        if p.is_file():
            found.add(p)
    return sorted(found)


def _copy_db(src: Path, tmp_dir: str) -> Path:
    dest = Path(tmp_dir) / src.name
    shutil.copy2(src, dest)
    for suffix in ("-wal", "-shm"):
        wal = src.parent / (src.name + suffix)
        if wal.exists():
            shutil.copy2(wal, Path(tmp_dir) / (src.name + suffix))
    return dest


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        cur = conn.execute(f'PRAGMA table_info("{table}")')
        return {row[1] for row in cur.fetchall()}
    except sqlite3.Error:
        return set()


def _tables(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return {row[0] for row in cur.fetchall()}


def _display_name(first: str | None, last: str | None, org: str | None) -> str | None:
    parts = []
    for x in (first, last):
        if x and str(x).strip():
            parts.append(str(x).strip())
    if parts:
        return " ".join(parts)
    if org and str(org).strip():
        return str(org).strip()
    return None


def _owner_join_sql(owner_col: str) -> str:
    return f"INNER JOIN ZABCDRECORD r ON r.Z_PK = p.{owner_col}"


def _rows_from_phones(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    tables = _tables(conn)
    if "ZABCDPHONENUMBER" not in tables or "ZABCDRECORD" not in tables:
        return []

    pcols = _table_columns(conn, "ZABCDPHONENUMBER")
    owner_col = None
    for c in ("ZOWNER", "Z22_OWNER"):
        if c in pcols:
            owner_col = c
            break
    if not owner_col or "ZFULLNUMBER" not in pcols:
        return []

    rcols = _table_columns(conn, "ZABCDRECORD")
    zf = "ZFIRSTNAME" if "ZFIRSTNAME" in rcols else None
    zl = "ZLASTNAME" if "ZLASTNAME" in rcols else None
    zo = "ZORGANIZATION" if "ZORGANIZATION" in rcols else None
    if not zf and not zl and not zo:
        return []

    sel = []
    if zf:
        sel.append(f"r.{zf}")
    else:
        sel.append("NULL")
    if zl:
        sel.append(f"r.{zl}")
    else:
        sel.append("NULL")
    if zo:
        sel.append(f"r.{zo}")
    else:
        sel.append("NULL")

    q = f"""
    SELECT {", ".join(sel)}, p.ZFULLNUMBER
    FROM ZABCDPHONENUMBER p
    {_owner_join_sql(owner_col)}
    WHERE p.ZFULLNUMBER IS NOT NULL AND TRIM(p.ZFULLNUMBER) != ''
    """
    out: list[tuple[str, str]] = []
    try:
        for row in conn.execute(q):
            first, last, org, raw = row[0], row[1], row[2], row[3]
            name = _display_name(first, last, org)
            if not name or not raw:
                continue
            key = normalize_phone(str(raw))
            if not key:
                continue
            out.append((key, name))
    except sqlite3.Error as e:
        logger.debug("Phone query failed: %s", e)
    return out


def _rows_from_emails(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    tables = _tables(conn)
    if "ZABCDEMAILADDRESS" not in tables or "ZABCDRECORD" not in tables:
        return []

    ecols = _table_columns(conn, "ZABCDEMAILADDRESS")
    owner_col = None
    for c in ("ZOWNER", "Z22_OWNER"):
        if c in ecols:
            owner_col = c
            break
    addr_col = "ZADDRESS" if "ZADDRESS" in ecols else None
    if not owner_col or not addr_col:
        return []

    rcols = _table_columns(conn, "ZABCDRECORD")
    zf = "ZFIRSTNAME" if "ZFIRSTNAME" in rcols else None
    zl = "ZLASTNAME" if "ZLASTNAME" in rcols else None
    zo = "ZORGANIZATION" if "ZORGANIZATION" in rcols else None

    sel = []
    for col in (zf, zl, zo):
        sel.append(f"r.{col}" if col else "NULL")

    q = f"""
    SELECT {", ".join(sel)}, e.{addr_col}
    FROM ZABCDEMAILADDRESS e
    INNER JOIN ZABCDRECORD r ON r.Z_PK = e.{owner_col}
    WHERE e.{addr_col} IS NOT NULL AND TRIM(e.{addr_col}) != ''
    """
    out: list[tuple[str, str]] = []
    try:
        for row in conn.execute(q):
            first, last, org, raw = row[0], row[1], row[2], row[3]
            name = _display_name(first, last, org)
            if not name or not raw:
                continue
            key = normalize_handle(str(raw))
            if not key or "@" not in key:
                continue
            out.append((key, name))
    except sqlite3.Error as e:
        logger.debug("Email query failed: %s", e)
    return out


def _merge_into_lookup(rows: list[tuple[str, str]], dest: dict[str, str]) -> None:
    """Prefer longer display names when the same key appears twice."""
    for key, name in rows:
        name = name.strip()
        if not name:
            continue
        prev = dest.get(key)
        if prev is None or len(name) > len(prev):
            dest[key] = name


def load_contact_lookup(db_paths: list[Path] | None = None) -> dict[str, str]:
    """Load a map of normalized handle (10-digit phone or lowercased email) → display name.

    Merges all Address Book sources found on disk. Returns an empty dict if
    Contacts data is missing or unreadable.
    """
    paths = db_paths if db_paths is not None else _find_abcddb_files()
    if not paths:
        logger.warning("No Address Book .abcddb files under %s", ADDRESSBOOK_ROOT)
        return {}

    lookup: dict[str, str] = {}

    for src in paths:
        if not src.exists():
            continue
        with tempfile.TemporaryDirectory(prefix="insightme_ab_") as tmp_dir:
            try:
                db_copy = _copy_db(src, tmp_dir)
            except PermissionError:
                logger.warning(
                    "Cannot read Address Book at %s. Grant Full Disk Access to the app running insightme.",
                    src,
                )
                continue
            except OSError as e:
                logger.warning("Cannot copy Address Book DB %s: %s", src, e)
                continue

            conn = sqlite3.connect(str(db_copy))
            try:
                phones = _rows_from_phones(conn)
                emails = _rows_from_emails(conn)
                _merge_into_lookup(phones, lookup)
                _merge_into_lookup(emails, lookup)
            finally:
                conn.close()

    logger.info(
        "Loaded %d contact name mappings from %d Address Book file(s)",
        len(lookup),
        len(paths),
    )
    return lookup


def contact_label(handle: str | None, lookup: dict[str, str] | None) -> str:
    """Return a display label for a normalized handle, or a formatted fallback."""
    if not handle:
        return "Unknown"
    if lookup and handle in lookup:
        return lookup[handle]
    h = str(handle)
    if h.isdigit() and len(h) == 10:
        return f"({h[:3]}) {h[3:6]}-{h[6:]}"
    return h
