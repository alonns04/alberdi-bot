from __future__ import annotations

import hashlib
from pathlib import Path


def compute_file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
