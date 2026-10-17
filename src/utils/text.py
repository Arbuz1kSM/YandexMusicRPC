from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from string import Formatter

_SPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_SECRET_RE = re.compile(
    r"(?i)(access[_-]?token|refresh[_-]?token|authorization|oauth|bearer)"
    r"\s*[:=]\s*([^\s,;]+)"
)


def normalize_text(value: str | None) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold()
    value = _PUNCT_RE.sub(" ", value)
    return _SPACE_RE.sub(" ", value).strip()


def clip_discord(value: str | None, maximum: int = 128) -> str | None:
    value = _SPACE_RE.sub(" ", value or "").strip()
    if not value:
        return None
    if len(value) <= maximum:
        return value
    return value[: maximum - 1].rstrip() + "…"


def safe_template(template: str, values: Mapping[str, str | None]) -> str:
    allowed = {"title", "artist", "album", "version", "time", "date", "volume", "session_time"}
    safe_values = {key: values.get(key) or "" for key in allowed}
    try:
        fields = {field for _, field, _, _ in Formatter().parse(template) if field}
        if not fields.issubset(allowed):
            return ""
        return _SPACE_RE.sub(" ", template.format_map(safe_values)).strip(" -•")
    except (KeyError, ValueError):
        return ""


def redact_secrets(message: str) -> str:
    return _SECRET_RE.sub(lambda m: f"{m.group(1)}=<redacted>", message)
