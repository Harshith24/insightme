# Analytics Overview

> All planned analytics computations and their status.

## Per-Contact iMessage Stats
| Stat | Status | Notes |
|------|--------|-------|
| Total messages sent/received | TODO | Filter out reactions |
| Sent/received ratio | TODO | |
| Average message length (words) | TODO | Only count messages with text |
| Median response time | TODO | → [response-time.md](response-time.md) for session rules |
| Most used emojis | TODO | Use `emoji` library for detection |
| Most used words | TODO | Exclude stop words |
| First/last message date | TODO | |
| Messages by hour/day | TODO | Heatmap data |
| Longest conversation streak | TODO | Days with at least 1 exchange |
| Longest dry spell | TODO | Days with zero messages |

## Per-Contact Call Stats
| Stat | Status | Notes |
|------|--------|-------|
| Total calls (in/out/missed) | TODO | |
| Total call duration | TODO | Only answered calls |
| Average call duration | TODO | |
| Longest call | TODO | |
| FaceTime vs regular breakdown | TODO | |
| Calls by hour/day | TODO | |

## Global Stats
| Stat | Status | Notes |
|------|--------|-------|
| Total messages / calls / call hours | TODO | |
| Top 10 by message volume | TODO | |
| Top 10 by call duration | TODO | |
| Busiest hour/day heatmap | TODO | |
| Weekly rolling message volume | TODO | |
| New contacts over time | TODO | First message date histogram |

## Unified / Relationship Stats
| Stat | Status | Notes |
|------|--------|-------|
| Combined message + call per contact | TODO | → [relationships.md](relationships.md) |
| Scatter: messages vs call minutes | TODO | Dot size = months known |
| Contact categories | TODO | text-heavy, call-heavy, both, dormant |
| Fading connections | TODO | 3+ months declining trend |

## Related Pages
- → [response-time.md](response-time.md) — Session-based response time rules
- → [relationships.md](relationships.md) — Category definitions and fading logic
- → [ui-structure.md](ui-structure.md) — Where each stat appears in the UI
