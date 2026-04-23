"""CLI entry point for insightme."""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Launch the Streamlit app."""
    app_path = Path(__file__).parent / "ui" / "app.py"
    env = os.environ.copy()
    # Keep visuals consistent for pip-installed runs regardless of user/global
    # Streamlit config files on the machine.
    env.setdefault("STREAMLIT_THEME_BASE", "light")
    env.setdefault("STREAMLIT_THEME_PRIMARY_COLOR", "#4f46e5")
    env.setdefault("STREAMLIT_THEME_BACKGROUND_COLOR", "#f5f1e8")
    env.setdefault("STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR", "#fffdf7")
    env.setdefault("STREAMLIT_THEME_TEXT_COLOR", "#111827")
    env.setdefault("STREAMLIT_THEME_FONT", "sans serif")
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path)],
        check=True,
        env=env,
    )


if __name__ == "__main__":
    main()
