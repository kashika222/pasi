"""Ensure ``src/`` is on ``sys.path`` for Streamlit Cloud.

Cloud may cache a prior non-editable ``pasi==0.1.x`` wheel. Prefer the
checked-out source tree so UI/package imports always match the repo.
"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_src_on_path() -> None:
    here = Path(__file__).resolve()
    for root in here.parents:
        if (root / "pyproject.toml").exists() and (root / "src" / "pasi").is_dir():
            src = str(root / "src")
            if src not in sys.path:
                sys.path.insert(0, src)
            return


ensure_src_on_path()
