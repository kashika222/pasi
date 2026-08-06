"""Load and render prompt templates stored outside application code."""

from __future__ import annotations

import re
from pathlib import Path

from pasi.config.settings import Settings, get_settings
from pasi.logging.setup import get_logger

logger = get_logger(__name__)

_PLACEHOLDER = re.compile(r"\{\{\s*([A-Z0-9_]+)\s*\}\}")


class PromptLoadError(RuntimeError):
    """Raised when a prompt template cannot be loaded or rendered."""


def prompts_dir(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.resolve(settings.prompts_dir)


def load_prompt(name: str, settings: Settings | None = None) -> str:
    """Load ``prompts/{name}`` (include extension, e.g. ``foo_v1.txt``)."""
    path = prompts_dir(settings) / name
    if not path.exists():
        raise PromptLoadError(f"Prompt file not found: {path}")
    text = path.read_text(encoding="utf-8")
    logger.debug("Loaded prompt %s (%s chars)", path.name, len(text))
    return text


def render_prompt(template: str, variables: dict[str, str]) -> str:
    """Replace ``{{VAR}}`` placeholders. Unknown placeholders raise."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in variables:
            raise PromptLoadError(f"Missing prompt variable: {key}")
        return variables[key]

    return _PLACEHOLDER.sub(repl, template)


def load_and_render(
    name: str,
    variables: dict[str, str],
    settings: Settings | None = None,
) -> str:
    return render_prompt(load_prompt(name, settings=settings), variables)
