# Apple Date Handling

> Two different epoch formats and how we convert them.

## The Two Formats

Apple uses 2001-01-01 00:00:00 UTC as its epoch (unlike Unix's 1970-01-01). But the two databases store time differently:

| Database | Column | Unit | Conversion |
|----------|--------|------|------------|
| iMessage (chat.db) | `message.date` | **Nanoseconds** since 2001-01-01 | `date / 1e9 + 978307200` |
| Call History | `ZCALLRECORD.ZDATE` | **Seconds** since 2001-01-01 | `date + 978307200` |

The magic number `978307200` is the number of seconds between Unix epoch (1970-01-01) and Apple epoch (2001-01-01).

## Why Nanoseconds vs Seconds?
- **iMessage** switched to nanosecond precision around macOS 10.13 (High Sierra). Older databases may use seconds — but we only handle the modern format since old Macs are rare.
- **Call History** uses Core Data, which stores `NSDate` as seconds since the Apple reference date.

## Conversion Code

```python
# iMessage (nanoseconds)
pd.to_datetime(date_raw / 1e9 + 978307200, unit='s', utc=True)

# Call History (seconds)
pd.to_datetime(date_raw + 978307200, unit='s', utc=True)
```

Both are converted to UTC, then to US/Eastern, then made timezone-naive for simpler downstream handling.

## Timezone Decision
Hardcoded to `US/Eastern` currently. This should be made configurable or auto-detected via `tzlocal` if the user is in a different timezone.

## Related Pages
- → [imessage-parsing.md](imessage-parsing.md) — Where iMessage dates are converted
- → [call-history.md](call-history.md) — Where call dates are converted
- → [open-questions.md](open-questions.md) — Timezone configurability is an open question
