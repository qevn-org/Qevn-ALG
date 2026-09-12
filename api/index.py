"""API entrypoint for Vercel /api function runtime."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from index import app, application  # noqa: E402

__all__ = ["app", "application"]
