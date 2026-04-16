# Data Layer Design

> How we safely read macOS databases and produce clean DataFrames.

## Core Principle: Copy Before Read
Both `chat.db` (iMessage) and `CallHistory.storedata` (Call History) are live databases actively written to by macOS apps. We **never** query them directly:

1. `shutil.copy2()` the DB file (plus `-wal` and `-shm` if they exist) to a `tempfile.TemporaryDirectory`
2. Open the copy with `sqlite3.connect()`
3. Query, build DataFrame, close connection
4. Temp dir auto-cleans up via context manager

This prevents locking the live DB and avoids corruption if the app writes mid-query.

## DataFrame Schemas

### Messages DataFrame (`imessage.load_messages()`)
| Column | Type | Description |
|--------|------|-------------|
| message_id | int | Primary key from message.ROWID |
| date | datetime | Converted from Apple nanosecond epoch |
| text | str/None | Message text (from `text` or `attributedBody`) |
| is_from_me | int | 1 = sent, 0 = received |
| handle_id | str | Raw phone/email from handle table |
| handle_normalized | str | Normalized via `contacts.normalize_handle()` |
| is_reaction | bool | True if tapback/reaction (associated_message_type != 0) |
| chat_id | int | Chat ROWID for grouping |
| is_group_chat | bool | True if chat.group_id is not NULL |
| is_email_handle | bool | True if handle is an email address |

### Calls DataFrame (`calls.load_calls()`)
| Column | Type | Description |
|--------|------|-------------|
| date | datetime | Converted from Core Data epoch |
| phone_normalized | str | Normalized via `contacts.normalize_phone()` |
| duration_seconds | float | Call duration (0 for missed) |
| is_outgoing | bool | True = I called them |
| is_answered | bool | True = call was answered |
| call_type | str | "phone", "facetime_video", "facetime_audio", "other" |

## Error Handling
- **No Full Disk Access** → `PermissionError` with instructions to enable FDA
- **DB not found** → `FileNotFoundError` with descriptive message
- **Unparseable attributedBody** → logged as warning, returns None for that message's text

## Related Pages
- → [imessage-parsing.md](imessage-parsing.md) — iMessage-specific parsing details
- → [call-history.md](call-history.md) — Call History specifics
- → [phone-normalization.md](phone-normalization.md) — How handles are normalized
- → [apple-dates.md](apple-dates.md) — Date conversion details
