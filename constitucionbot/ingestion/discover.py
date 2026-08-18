from __future__ import annotations

from pathlib import Path
from typing import List

from config import SRC_DIR, SUPPORTED_EXTENSIONS


def discover_documents() -> List[Path]:
    files: List[Path] = []
    for path in SRC_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
    return sorted(files)
