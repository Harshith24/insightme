# iMessage Parsing

> How we read chat.db and handle its quirks.

## Database Location
`~/Library/Messages/chat.db` — requires Full Disk Access for the terminal app.

## Key Tables and Joins

```sql
message                    -- every message
handle                     -- phone numbers and emails
chat                       -- conversations (1:1 and group)
chat_message_join          -- links messages to chats
chat_handle_join           -- links handles to chats
```

The main query joins `message → handle` (via `handle_id`), `message → chat` (via `chat_message_join`).

## attributedBody Parsing

**The biggest gotcha in this project.**

On macOS 13+ (Ventura), Apple changed iMessage storage. The `text` column in the `message` table is often NULL for newer messages. The actual text lives in the `attributedBody` BLOB column as a serialized `NSAttributedString`.

### Extraction Algorithm
```python
1. Split blob on b"NSString"
2. Take the part after the marker
3. Skip 5 header bytes
4. Read 1 byte as length
5. If length == 0x81, read next 2 bytes as actual length (extended format)
6. Read that many bytes as UTF-8 text
```

This is a heuristic — it works on ~95%+ of messages but will fail on some (attachments, special formats). We log the failure count and return None for those messages rather than crashing.

## Tapbacks / Reactions
Messages with `associated_message_type != 0` are reactions (thumbs up, heart, etc.), not real messages. We flag them as `is_reaction = True` so analytics can:
- **Exclude** them from message counts and response time calculations
- **Include** them as a separate fun stat (e.g., "most reacted-to messages")

## Group Chats
Detected via `chat.group_id IS NOT NULL`. The `is_group_chat` flag lets analytics separate 1:1 conversations from group activity, since group messages skew per-contact stats.

## Related Pages
- → [apple-dates.md](apple-dates.md) — Date conversion for the `date` column
- → [phone-normalization.md](phone-normalization.md) — Handle normalization
- → [data-layer.md](data-layer.md) — Output DataFrame schema
