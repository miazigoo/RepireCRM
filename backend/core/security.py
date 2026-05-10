import html
import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
DANGEROUS_BLOCK_RE = re.compile(
    r"(?is)<\s*(script|style|iframe|object|embed|svg|math)\b[^>]*>.*?<\s*/\s*\1\s*>"
)
HTML_TAG_RE = re.compile(r"(?s)<[^>]*>")
DANGEROUS_URI_RE = re.compile(r"(?i)\b(?:javascript|vbscript|data)\s*:")
EVENT_HANDLER_RE = re.compile(r"(?i)\bon[a-z0-9_:-]+\s*=")


def clean_plain_text(value: str | None) -> str:
    """Normalize user-entered plain text and remove HTML/JS injection vectors."""
    if value is None:
        return ""

    text = str(value)
    for _ in range(2):
        text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = CONTROL_CHARS_RE.sub("", text)
    text = DANGEROUS_BLOCK_RE.sub("", text)
    text = HTML_TAG_RE.sub("", text)
    text = EVENT_HANDLER_RE.sub("", text)
    text = DANGEROUS_URI_RE.sub("", text)
    return text.strip()


def clean_payload(
    payload: Mapping[str, Any],
    fields: Iterable[str],
    *,
    keep_none: bool = True,
) -> dict[str, Any]:
    clean = dict(payload)
    for field in fields:
        if field not in clean:
            continue
        if clean[field] is None and keep_none:
            continue
        clean[field] = clean_plain_text(clean[field])
    return clean
