# Response Time Calculation

> How we measure response time without overnight skew.

## The Problem
Naive response time = time between their message and my next reply. But if someone texts at 11pm and I reply at 8am, that's not a 9-hour response time — I was asleep.

## The Solution: Session-Based Measurement

A **conversation session** is a sequence of messages where no gap exceeds 12 hours.

```
11:00am  Them: "hey"
11:02am  Me: "what's up"        ← response time: 2 min
11:05am  Them: "want to grab lunch?"
11:15am  Me: "sure"             ← response time: 10 min
--- 14 hours pass ---
9:00am   Them: "running late"   ← NEW SESSION, no response time from previous
9:05am   Me: "no worries"      ← response time: 5 min
```

### Rules
1. Only measure within sessions (gaps < 12 hours)
2. Response time = time from their last message to my next reply (and vice versa)
3. Report **median** response time, not mean (outliers skew mean badly)
4. Compute separately: "my response time to them" and "their response time to me"

## Implementation Notes
- Sort messages by date within each 1:1 conversation
- Walk through sequentially, tracking who sent the last message
- When sender flips (them → me or me → them), record the gap if < 12 hours
- Aggregate into two lists per contact: my_response_times, their_response_times

## Related Pages
- → [analytics-overview.md](analytics-overview.md) — Where this fits in the analytics suite
- → [imessage-parsing.md](imessage-parsing.md) — Source data for response time calc
