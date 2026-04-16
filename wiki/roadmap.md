# Roadmap & Phases

> Build order and current status.

## Phase 1: Data Layer ✅ COMPLETE
**Goal**: Read macOS databases, produce clean DataFrames, verify with test script.

| File | Status | Notes |
|------|--------|-------|
| `data/contacts.py` | ✅ Done | normalize_phone, normalize_handle, extract_area_code |
| `data/imessage.py` | ✅ Done | chat.db reader with attributedBody fallback |
| `data/calls.py` | ✅ Done | CallHistory.storedata reader |
| `data/area_codes.py` | ✅ Done | ~300 US area codes bundled |
| `test_data_layer.py` | ✅ Done | Prints top contacts, basic stats |
| `cli.py` | ✅ Done | Entry point for Streamlit |

**Blocker resolved**: Test script runs. Normalization verified. DB reads blocked by Full Disk Access (expected — user must grant FDA to terminal).

## Phase 2: Analytics Layer — TODO
**Goal**: Compute all per-contact and global analytics from DataFrames.

| File | Status | Notes |
|------|--------|-------|
| `analytics/messages.py` | TODO | Per-contact + global message stats |
| `analytics/calls.py` | TODO | Per-contact + global call stats |
| `analytics/relationships.py` | TODO | Unified view, categories, fading connections |

## Phase 3: Streamlit UI — TODO
**Goal**: Build all 5 pages with interactive charts.

| File | Status | Notes |
|------|--------|-------|
| `ui/app.py` | TODO | Main app, page routing, caching |
| `ui/dashboard.py` | TODO | Top-level stats |
| `ui/contact_detail.py` | TODO | Per-contact deep dive |
| `ui/relationships.py` | TODO | Scatter plot, fading list |
| `ui/map_view.py` | TODO | Area code map |
| `ui/patterns.py` | TODO | Heatmaps, trends |

## Related Pages
- → [architecture.md](architecture.md) — Why this build order
- → [analytics-overview.md](analytics-overview.md) — What Phase 2 computes
- → [ui-structure.md](ui-structure.md) — What Phase 3 builds
