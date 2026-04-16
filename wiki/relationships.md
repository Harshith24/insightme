# Relationship Analytics

> How we combine message + call data and categorize contacts.

## Unified View
For each contact (matched by normalized phone number), we combine:
- **Message stats** from iMessage (count, frequency, response times)
- **Call stats** from Call History (count, duration, FaceTime ratio)

This gives a holistic picture of each relationship.

## Contact Categories

| Category | Definition |
|----------|-----------|
| **text-heavy** | High message count, low call minutes |
| **call-heavy** | Low message count, high call minutes |
| **both** | High in both messages and calls |
| **dormant** | No messages or calls in the last 3 months |

Thresholds TBD — likely based on percentiles (e.g., top 25% in messages = "high").

## Fading Connections
A contact is "fading" if their monthly message count has been **declining for 3+ consecutive months**. This is calculated as:

```
month_counts = messages per month for last 6 months
if month_counts[-3] > month_counts[-2] > month_counts[-1]:
    → fading
```

This surfaces relationships that might need attention — people you used to talk to frequently but have been drifting from.

## Scatter Plot Design
- **X-axis**: Total message count
- **Y-axis**: Total call minutes
- **Dot size**: Months since first interaction (longer = bigger)
- **Color**: Contact category
- **Hover**: Contact name/number, key stats

## Related Pages
- → [analytics-overview.md](analytics-overview.md) — Full analytics list
- → [phone-normalization.md](phone-normalization.md) — How contacts are matched across databases
- → [ui-structure.md](ui-structure.md) — Relationships page in the UI
