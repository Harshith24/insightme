"""Phone number normalization and contact utilities."""

import math
import re
from typing import Any


def _coerce_sql_text(value: Any) -> str | None:
    """SQLite NULL / pandas NA often arrive as float('nan'); normalize to None or str."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if not isinstance(value, str):
        value = str(value)
    s = value.strip()
    return s if s else None


def normalize_phone(raw: str | None) -> str | None:
    """Normalize a phone number to its last 10 digits (US) or cleaned form.

    Strips all non-digit characters. For numbers with 10+ digits, keeps the
    last 10 (drops country code). Returns None for empty/invalid input.
    """
    raw = _coerce_sql_text(raw)
    if not raw:
        return None

    digits = re.sub(r"\D", "", raw)

    if not digits:
        return None

    # US numbers: keep last 10 digits (strips +1 country code)
    if len(digits) >= 10:
        return digits[-10:]

    # Short numbers (e.g. short codes) — return as-is
    return digits


def is_email(identifier: str | None) -> bool:
    """Check if a handle identifier is an email address."""
    identifier = _coerce_sql_text(identifier)
    if not identifier:
        return False
    return "@" in identifier


def normalize_handle(identifier: str | None) -> str | None:
    """Normalize a handle ID — email left as-is, phone numbers normalized."""
    identifier = _coerce_sql_text(identifier)
    if not identifier:
        return None
    if is_email(identifier):
        return identifier.strip().lower()
    return normalize_phone(identifier)


def is_short_code(phone: str | None) -> bool:
    """Check if a normalized phone number is a short code (automated SMS).

    Short codes are 5-6 digit numbers used for 2FA, notifications, marketing, etc.
    They should be excluded from personal contact analytics.
    """
    phone = _coerce_sql_text(phone)
    if not phone or not phone.isdigit():
        return False
    return len(phone) <= 6


def extract_area_code(phone: str | None) -> str | None:
    """Extract the 3-digit area code from a normalized 10-digit US phone number."""
    phone = _coerce_sql_text(phone)
    if not phone or len(phone) != 10 or not phone.isdigit():
        return None
    return phone[:3]
