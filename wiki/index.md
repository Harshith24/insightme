# insightme LLM Wiki — Index

> This wiki documents every design decision, architecture choice, and session history for the insightme project. Each topic links to a dedicated page. When starting a new session, read this index to find relevant context fast.

## Architecture & Design

| Topic | Page | Summary |
|-------|------|---------|
| System Architecture | [architecture.md](architecture.md) | Overall system design, data flow, layer separation |
| Data Layer Design | [data-layer.md](data-layer.md) | How we read macOS databases safely, DataFrame schemas |
| Phone Normalization | [phone-normalization.md](phone-normalization.md) | Why and how phone numbers are normalized across sources |
| Apple Date Handling | [apple-dates.md](apple-dates.md) | Two different Apple epoch formats, conversion strategies |
| iMessage Parsing | [imessage-parsing.md](imessage-parsing.md) | chat.db schema, attributedBody blobs, tapback filtering |
| Call History Parsing | [call-history.md](call-history.md) | Core Data SQLite format, ZCALLRECORD schema |
| Area Code Mapping | [area-code-mapping.md](area-code-mapping.md) | Static NANPA lookup, geographic visualization approach |
| Privacy & Security | [privacy.md](privacy.md) | Local-only design, temp copies, no network calls |

## Analytics & Features

| Topic | Page | Summary |
|-------|------|---------|
| Analytics Overview | [analytics-overview.md](analytics-overview.md) | All planned per-contact and global analytics |
| Response Time Calc | [response-time.md](response-time.md) | Session-based response time, 12-hour gap rule |
| Relationship Categories | [relationships.md](relationships.md) | Text-heavy, call-heavy, fading connections logic |
| UI Structure | [ui-structure.md](ui-structure.md) | Streamlit pages, sidebar, caching strategy |

## Project Status

| Topic | Page | Summary |
|-------|------|---------|
| Roadmap & Phases | [roadmap.md](roadmap.md) | Phase 1 (data) → Phase 2 (analytics) → Phase 3 (UI) |
| Open Questions | [open-questions.md](open-questions.md) | Unresolved design decisions and known gaps |

---

### How to use this wiki

- **New to the project?** Read [architecture.md](architecture.md) first, then [data-layer.md](data-layer.md).
- **Working on a specific module?** Find it in the Architecture & Design table above.
- **Cross-references** are marked with → links between pages to show relationships.
- **This wiki is auto-maintained** — Claude updates relevant pages after every interaction. Pages always reflect the latest state of the project.
