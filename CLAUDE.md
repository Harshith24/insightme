# insightme — Project Context for Claude

## What is this?
A Python-based personal analytics tool that analyzes iMessage and Call History data from a Mac. Runs 100% locally — no cloud, no uploads, no servers. UI is Streamlit.

## Quick Start
```bash
# Requires Full Disk Access for the terminal app
# System Settings → Privacy & Security → Full Disk Access → toggle on terminal
python3 test_data_layer.py        # verify data layer works
pip install -e .                  # install package
insightme                         # launch Streamlit UI
```

## Project Structure
```
insightme/
├── CLAUDE.md                     # You are here
├── wiki/                         # LLM wiki — living design docs, auto-maintained by Claude
│   └── index.md                  # START HERE — table of contents for all wiki pages
├── pyproject.toml                # Package config, dependencies
├── test_data_layer.py            # Data layer verification script
└── src/insightme/
    ├── cli.py                    # Entry point → launches Streamlit
    ├── data/                     # Data access layer (Phase 1 — DONE)
    │   ├── contacts.py           # Phone normalization (normalize_phone, normalize_handle)
    │   ├── imessage.py           # chat.db reader with attributedBody parsing
    │   ├── calls.py              # CallHistory.storedata reader
    │   └── area_codes.py         # US area code → lat/lng static lookup
    ├── analytics/                # Analytics computations (Phase 2 — TODO)
    │   ├── messages.py           # Per-contact message stats
    │   ├── calls.py              # Per-contact call stats
    │   └── relationships.py      # Unified cross-source analytics
    └── ui/                       # Streamlit pages (Phase 3 — TODO)
        ├── app.py                # Main app, page routing
        ├── dashboard.py          # Top-level stats, heatmaps
        ├── contact_detail.py     # Per-contact deep dive
        ├── relationships.py      # Scatter plots, fading connections
        ├── map_view.py           # Area code geographic map
        └── patterns.py           # Hour/day heatmaps, trends
```

## LLM Wiki
**Always read `wiki/index.md` first** when starting a new session. It contains a linked table of contents covering every design decision, architecture choice, and history. Each topic links to a dedicated wiki page with full context.

## Wiki Maintenance Protocol — MANDATORY

**After every user prompt and your response, you MUST update the wiki.** This is not optional. Follow these steps:

1. **Read `wiki/index.md`** to see all existing topic pages.
2. **Match**: Determine which wiki page(s) are relevant to what just happened in this conversation turn — what the user asked, what you changed, what decisions were made.
3. **Update in-place**: Edit the relevant `.md` file(s) to reflect the current state. Wiki pages should always describe the **latest truth**, not append history. If a design changed, rewrite that section. If a feature was built, update its status from TODO to DONE. If a new decision was made, add it.
4. **Create new page if needed**: If the conversation covered something that doesn't fit any existing wiki page (e.g., a brand-new feature area, a new integration), create a new `.md` file in `wiki/` and add it to the appropriate section in `wiki/index.md`.
5. **Update `wiki/index.md`** if you added, renamed, or removed any wiki pages.

### What to capture in wiki updates:
- Design decisions and **why** they were made
- Architecture changes
- New features or modules added
- Status changes (TODO → DONE)
- Bug fixes and what caused them
- Changed approaches (old approach → new approach and why)
- New open questions discovered

### What NOT to put in the wiki:
- Raw conversation transcripts or prompts
- Temporary debugging notes
- Things that are obvious from reading the code

### Key principle:
The wiki is a **living document** — every page should read as if it was written today, describing the current state of the project. A new Claude session reading any wiki page should get an accurate, up-to-date picture without needing conversation history.

## Key Technical Decisions
- **Never query live databases** — always `shutil.copy2` to a temp dir first
- **Phone normalization** — strip to digits, keep last 10 (US). One function used everywhere: `contacts.normalize_phone()`
- **Apple date conversion** — iMessage uses nanoseconds since 2001-01-01; Call History uses seconds since 2001-01-01. Offset: `978307200`
- **attributedBody parsing** — macOS 13+ stores text in NSAttributedString blobs, not the `text` column. Fallback parser in `imessage.py`
- **Tapbacks/reactions** — `associated_message_type != 0` means reaction. Filter from counts, optionally show as fun stat.
- **Timezone** — Dates converted to US/Eastern and stored as naive datetime. Change in `imessage.py` and `calls.py` if user is in different zone.

## Dependencies
pandas, plotly, streamlit, wordcloud, emoji — all in pyproject.toml

## Conventions
- Use `st.cache_data` for all data loading in Streamlit
- All phone normalization goes through `data.contacts.normalize_phone()`
- DataFrames are the interchange format between layers
- Logging via stdlib `logging`, not print statements
