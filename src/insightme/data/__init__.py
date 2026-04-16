"""Data access layer: iMessage, Call History, and macOS Contacts (Address Book)."""

from insightme.data.addressbook import contact_label, load_contact_lookup

__all__ = ["contact_label", "load_contact_lookup"]
