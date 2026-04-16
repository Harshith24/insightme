# Open Questions

> Unresolved design decisions and known gaps.

## Timezone Handling
**Current**: Hardcoded to `US/Eastern` in both `imessage.py` and `calls.py`.
**Question**: Should we auto-detect via `tzlocal` library, or make it a config option?
**Impact**: Wrong timezone shifts all hour-of-day analytics and response time sessions.

## Contact Name Resolution
**Current**: We only have phone numbers and emails — no display names.
**Question**: Should we try to read the macOS Contacts database (`AddressBook-v22.abcddb`) to resolve names?
**Tradeoff**: Adds another FDA-protected database to read, but dramatically improves UX (seeing "Mom" instead of "5551234567").
**Alternative**: Let users manually map nicknames in a config file.

## International Number Handling
**Current**: `normalize_phone()` keeps last 10 digits. Works for US/Canada.
**Question**: How to handle international contacts (UK +44, India +91, etc.)?
**Impact**: International numbers may collide or be truncated incorrectly.
**Possible fix**: Use `phonenumbers` library for proper parsing, but adds complexity.

## Relationship Category Thresholds
**Current**: Categories defined conceptually (text-heavy, call-heavy, etc.).
**Question**: What percentile thresholds define "high" vs "low"?
**Options**: Top 25%? Fixed counts? User-configurable?

## Group Chat Analytics
**Current**: Group chats flagged but not deeply analyzed.
**Question**: Should we compute per-group stats (most active group, your contribution %, etc.)?
**Impact**: Adds significant complexity but could be interesting.

## Historical iMessage Date Format
**Current**: We only handle nanosecond timestamps (macOS 10.13+).
**Question**: Should we also handle the older seconds-based format?
**Detection**: If `date` values are < 1e12, they're seconds; otherwise nanoseconds.

---

*Each question should be resolved before or during the phase it affects. Update this page as decisions are made.*
