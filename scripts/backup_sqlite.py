"""Salin file SQLite aplikasi ke data/backups/ dengan cap waktu."""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from src.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    src = Path(settings.db_path)
    if not src.is_file():
        print(f"Database tidak ditemukan: {src}")
        sys.exit(1)
    dest_dir = ROOT / "data" / "backups"
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"app-{stamp}.db"
    shutil.copy2(src, dest)
    print(f"Disalin ke {dest}")


if __name__ == "__main__":
    main()
