"""Ensure repo ``src/`` is preferred for Streamlit Cloud imports.

Cloud often keeps a cached ``pasi`` wheel in site-packages. Always put the
checked-out ``src/`` first and drop any already-imported ``pasi*`` modules so
pages pick up the latest UI helpers.
"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_src_on_path() -> None:
    here = Path(__file__).resolve()
    for root in here.parents:
        if (root / "pyproject.toml").exists() and (root / "src" / "pasi").is_dir():
            src = str(root / "src")
            while src in sys.path:
                sys.path.remove(src)
            sys.path.insert(0, src)

            # Force reload from src if a stale site-packages copy was imported.
            for name in list(sys.modules):
                if name == "pasi" or name.startswith("pasi."):
                    del sys.modules[name]
            return


ensure_src_on_path()
