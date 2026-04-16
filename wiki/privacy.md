# Privacy & Security

> Why insightme is designed to be 100% local and what that means.

## Core Principle
This tool analyzes deeply personal communication data — who you talk to, how often, when, what you say. **None of this data ever leaves the machine.**

## Design Rules
1. **No network calls** — No analytics APIs, no external services, no telemetry
2. **No servers** — Streamlit runs locally on `localhost`
3. **Temp copies only** — We copy databases to a temp dir, read them, then the temp dir auto-deletes. The original databases are never modified.
4. **No data export** — The tool doesn't write analyzed data to persistent files (it's all in-memory DataFrames)
5. **Static lookups** — Area code mapping uses a bundled dictionary, not an API

## Full Disk Access
The tool requires macOS Full Disk Access because `chat.db` and `CallHistory.storedata` are protected by TCC (Transparency, Consent, and Control). The user must explicitly grant this to their terminal app.

This is a feature, not a bug — it means no random app can read your messages without your consent.

## What Gets Loaded Into Memory
- All iMessage text content (for word analysis, emoji counts)
- All phone numbers/emails (for contact matching)
- Call metadata (times, durations, numbers)

This data lives in pandas DataFrames for the duration of the Streamlit session and is garbage-collected when the app closes.

## Related Pages
- → [architecture.md](architecture.md) — System design that enforces local-only
- → [data-layer.md](data-layer.md) — Temp copy mechanism
- → [area-code-mapping.md](area-code-mapping.md) — Static lookup instead of API
