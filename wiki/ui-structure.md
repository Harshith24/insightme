# UI Structure

> Streamlit page layout and caching strategy.

## Pages

### 1. Dashboard (`ui/dashboard.py`)
- Top-level metrics: total messages, total calls, total call hours
- Top 10 contacts by message volume (bar chart)
- Top 10 contacts by call duration (bar chart)
- Weekly message volume over time (line chart)
- Hour × day-of-week heatmap

### 2. Contact Deep Dive (`ui/contact_detail.py`)
- Contact selector (search/dropdown)
- All per-contact message stats
- All per-contact call stats
- Message timeline (volume over time)
- Word cloud of most-used words
- Emoji usage breakdown
- Response time distribution

### 3. Relationships (`ui/relationships.py`)
- Scatter plot: messages vs call minutes
- Contact category breakdown (pie or bar)
- Fading connections list with trend sparklines

### 4. Map (`ui/map_view.py`)
- Interactive Plotly map with area code markers
- Marker size = number of contacts from that area code
- Label: "Contact regions by phone number"

### 5. Patterns (`ui/patterns.py`)
- Hour-of-day distribution
- Day-of-week distribution
- Hour × day heatmap (detailed)
- Response time distributions
- Monthly trends over time

## Sidebar (Global)
- Contact search/filter
- Date range picker (filters all pages)

## Caching Strategy
```python
@st.cache_data
def get_messages():
    return load_messages()

@st.cache_data
def get_calls():
    return load_calls()
```

Database reads happen **once per Streamlit session**. Analytics recompute when filters change but work on cached DataFrames.

## Related Pages
- → [architecture.md](architecture.md) — Why UI is a separate layer
- → [analytics-overview.md](analytics-overview.md) — What stats appear on which page
- → [relationships.md](relationships.md) — Scatter plot and fading connections details
