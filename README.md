# insightme

Local-only analytics for **iMessage**, **Call History**, and **macOS Contacts names** on **macOS**. Data never leaves your machine — think Spotify Wrapped for messages and calls.

## Requirements

- **macOS** with Messages / Phone / Contacts data
- **Python 3.11+**
- **Full Disk Access** for the app that runs the tool (e.g. Terminal):  
  **System Settings → Privacy & Security → Full Disk Access** → add that app  
  Then run `insightme` from your terminal

## Install and Run

### Pip install
```bash
pip install insightme
```

### Run it in terminal
```
insightme
```

The `insightme` command starts the **Streamlit** UI. Open the URL shown in the terminal (usually `http://localhost:8501`).

## High level workflow

1. Run on your Mac with Full Disk Access for the terminal as above.
2. To avoid locking and race conditions with system apps, SQLite files (where the message/call/contacts data are) are **copied** to a **temporary directory** and read from the copy.
3. **SQL** loads messages, calls, and address-book rows into **pandas** DataFrames for analytics.
4. Analytics live under `src/insightme/analytics/`.
5. The **Streamlit** app (default port **8501**) renders dashboards locally.

