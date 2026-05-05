from __future__ import annotations

import logging
from pathlib import Path

_configured = False


def setup_app_logging() -> None:
    global _configured
    if _configured:
        return
    root = logging.getLogger()
    if root.handlers:
        _configured = True
        return
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler("logs/app.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    _configured = True
