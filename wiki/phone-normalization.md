# Phone Normalization

> Why phone numbers need normalization and how we do it.

## The Problem
The same person appears in different formats across databases:
- iMessage: `+15551234567`
- Call History: `(555) 123-4567`
- Another message: `555-123-4567`
- FaceTime: `15551234567`

Without normalization, the same contact would appear as 4 different people.

## The Solution: `contacts.normalize_phone()`

```python
def normalize_phone(raw: str | None) -> str | None:
    digits = re.sub(r"\D", "", raw)    # strip non-digits
    if len(digits) >= 10:
        return digits[-10:]             # keep last 10 (drops +1 country code)
    return digits                       # short codes returned as-is
```

**Decision: Last 10 digits.** This works for US numbers (always 10 digits) and correctly strips the `+1` country code without needing a phone number parsing library.

### Limitation
International numbers with different digit counts will collide or be wrong. For a personal US-focused tool, this tradeoff is acceptable. If international support is needed later, consider the `phonenumbers` library.

## Handle Normalization
`contacts.normalize_handle()` routes by type:
- **Email handles** (`@` present) → lowercase, strip whitespace
- **Phone handles** → `normalize_phone()`

## Where It's Used
Every module that touches phone numbers or handles calls `normalize_phone()` or `normalize_handle()`:
- `imessage.py` — normalizes `handle.id` into `handle_normalized`
- `calls.py` — normalizes `ZADDRESS` into `phone_normalized`
- `area_codes.py` — `extract_area_code()` expects a pre-normalized 10-digit string

**Rule: Never compare raw phone strings. Always normalize first.**

## Related Pages
- → [data-layer.md](data-layer.md) — DataFrame schemas using normalized handles
- → [area-code-mapping.md](area-code-mapping.md) — Area codes extracted from normalized numbers
