"""CLI entry point for insightme."""

import subprocess
import sys
from pathlib import Path


def main():
    """Launch the Streamlit app."""
    app_path = Path(__file__).parent / "ui" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=True)


if __name__ == "__main__":
    main()
