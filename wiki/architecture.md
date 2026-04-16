# System Architecture

> How insightme is structured and why.

## Three-Layer Design

```
┌─────────────────────────────────────────────┐
│  UI Layer (Streamlit)                       │
│  - Pages: Dashboard, Contact, Relationships │
│  - st.cache_data for session-level caching  │
├─────────────────────────────────────────────┤
│  Analytics Layer                            │
│  - Pure functions: DataFrame in → stats out │
│  - No database access, no side effects      │
├─────────────────────────────────────────────┤
│  Data Layer                                 │
│  - Reads macOS SQLite databases             │
│  - Outputs clean pandas DataFrames          │
│  - Handles all normalization                │
└─────────────────────────────────────────────┘
```

### Why this separation?
1. **Testability** — Analytics can be tested with synthetic DataFrames, no real DB needed.
2. **Caching** — UI caches the DataFrames once per session; analytics recompute on filter changes.
3. **Safety** — Only the data layer touches the filesystem. It copies DBs to temp dirs before reading.

## Data Flow

```
macOS databases
    ↓ (shutil.copy2 to temp dir)
Data Layer (imessage.py, calls.py)
    ↓ (pandas DataFrames)
Analytics Layer (messages.py, calls.py, relationships.py)
    ↓ (stats dicts, aggregated DataFrames)
UI Layer (Streamlit pages)
    ↓ (Plotly charts, metrics)
Browser
```

## Entry Point
`cli.py` → launches `streamlit run ui/app.py`. Package installed via `pip install -e .` exposes the `insightme` command.

## LLM Wiki System
The project includes a `wiki/` directory that serves as a living knowledge base. Claude is instructed (via `CLAUDE.md`) to update relevant wiki pages after every interaction. This means:
- Wiki pages always reflect the **current** state of the project
- Design decisions are captured with rationale at the time they're made
- New Claude sessions can read `wiki/index.md` to quickly orient themselves
- No session logs — pages are updated in-place to stay current

## Related Pages
- → [data-layer.md](data-layer.md) — Data layer specifics
- → [ui-structure.md](ui-structure.md) — UI page layout
- → [privacy.md](privacy.md) — Why local-only matters
