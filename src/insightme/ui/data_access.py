"""Cached data loading for the Streamlit UI."""

from __future__ import annotations

import logging

import streamlit as st

from insightme.data.addressbook import load_contact_lookup
from insightme.data.calls import load_calls
from insightme.data.imessage import load_messages

logger = logging.getLogger(__name__)


@st.cache_data(show_spinner="Loading iMessage…")
def get_messages():
    return load_messages()


@st.cache_data(show_spinner="Loading call history…")
def get_calls():
    return load_calls()


@st.cache_data(show_spinner="Loading Contacts names…")
def get_contact_lookup() -> dict[str, str]:
    return load_contact_lookup()


def load_data_or_errors():
    """Return messages, calls, lookup, and a list of (source, error) for anything that failed."""
    errors: list[tuple[str, str]] = []
    messages = None
    calls = None
    lookup: dict[str, str] = {}

    try:
        messages = get_messages()
    except Exception as e:
        logger.exception("iMessage load failed")
        errors.append(("iMessage (chat.db)", str(e)))

    try:
        calls = get_calls()
    except Exception as e:
        logger.exception("Call history load failed")
        errors.append(("Call History", str(e)))

    try:
        lookup = get_contact_lookup()
    except Exception as e:
        logger.exception("Contacts lookup failed")
        errors.append(("Contacts (Address Book)", str(e)))

    return messages, calls, lookup, errors
