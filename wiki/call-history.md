# Call History Parsing

> How we read the Core Data SQLite file for call records.

## Database Location
`~/Library/Application Support/CallHistoryDB/CallHistory.storedata` — requires Full Disk Access.

## Core Data Format
This isn't a regular SQLite database — it's a Core Data persistent store. The main table is `ZCALLRECORD` (Core Data prefixes entity names with `Z`).

## Key Columns

| Column | Type | Meaning |
|--------|------|---------|
| `ZADDRESS` | text | Phone number (various formats) |
| `ZDATE` | real | Seconds since 2001-01-01 (Apple epoch) |
| `ZDURATION` | real | Duration in seconds (0 = missed/declined) |
| `ZORIGINATED` | int | 1 = outgoing, 0 = incoming |
| `ZANSWERED` | int | 1 = answered, 0 = missed/declined |
| `ZCALLTYPE` | int | 1 = phone, 8 = FaceTime video, 16 = FaceTime audio |

## Call Type Mapping

```python
CALL_TYPES = {
    1: "phone",
    8: "facetime_video",
    16: "facetime_audio",
}
```

Other values are mapped to `"other"`. New call types may appear in future macOS versions — the fallback ensures we don't lose data.

## Relationship to iMessage
Call records and iMessage data are joined via normalized phone numbers. Both databases store phone numbers in different formats, so `contacts.normalize_phone()` is critical for cross-referencing.

A contact might have:
- 500 messages in iMessage
- 30 calls in Call History
- Both linked via the same normalized 10-digit phone number

## Related Pages
- → [apple-dates.md](apple-dates.md) — Date conversion (seconds, not nanoseconds)
- → [phone-normalization.md](phone-normalization.md) — How phone numbers are joined across DBs
- → [data-layer.md](data-layer.md) — Output DataFrame schema
- → [relationships.md](relationships.md) — How messages + calls are unified per contact
