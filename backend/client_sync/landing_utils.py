"""Нормализация настроек лендинга клиентского портала."""

from __future__ import annotations

import re
from typing import Any

from django.utils.html import strip_tags

ALLOWED_CARD_ICONS = frozenset(
    {"status", "pricing", "map", "visit", "shield", "sparkle"}
)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _plain_text(value: Any, max_len: int) -> str:
    if value is None:
        return ""
    text = strip_tags(str(value))
    text = _CONTROL_CHARS_RE.sub("", text)
    return " ".join(text.split()).strip()[:max_len]


def normalize_landing_text(value: Any, max_len: int) -> str:
    return _plain_text(value, max_len)


def normalize_feature_cards(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw[:4]:
        if not isinstance(item, dict):
            continue
        title = _plain_text(item.get("title"), 200)
        body = _plain_text(item.get("body"), 1200)
        if not title or not body:
            continue
        icon = str(item.get("icon", "status")).strip().lower()
        if icon not in ALLOWED_CARD_ICONS:
            icon = "status"
        out.append({"title": title, "body": body, "icon": icon})
    return out


def normalize_promo_spotlight(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return _default_promo_spotlight()

    def _s(key: str, max_len: int = 500) -> str:
        return _plain_text(raw.get(key), max_len)

    cta = _s("cta_href", 500)
    if cta and len(cta) > 8 and not cta.startswith(("/", "http://", "https://")):
        cta = "/" + cta.lstrip("/")

    img = _s("image_url", 2000)
    if img and not (img.startswith("http://") or img.startswith("https://")):
        img = ""

    return {
        "enabled": bool(raw.get("enabled", False)),
        "title": _s("title", 200),
        "subtitle": _s("subtitle", 300),
        "body": _s("body", 2000),
        "badge": _s("badge", 80),
        "cta_label": _s("cta_label", 80),
        "cta_href": cta,
        "image_url": img or None,
    }


def _default_promo_spotlight() -> dict[str, Any]:
    return {
        "enabled": False,
        "title": "",
        "subtitle": "",
        "body": "",
        "badge": "",
        "cta_label": "",
        "cta_href": "",
        "image_url": None,
    }


def serialize_landing_for_portal(integration) -> dict[str, Any]:
    """Снимок настроек лендинга для API и синхронизации."""
    from client_sync.models import ClientPortalIntegration

    if not isinstance(integration, ClientPortalIntegration):
        raise TypeError("integration")
    promo = normalize_promo_spotlight(integration.landing_promo_spotlight or {})
    cards = normalize_feature_cards(integration.landing_feature_cards or [])
    return {
        "section_eyebrow": _plain_text(integration.landing_section_eyebrow, 120),
        "section_title": _plain_text(integration.landing_section_title, 200),
        "section_subtitle": _plain_text(integration.landing_section_subtitle, 4000),
        "feature_cards": cards,
        "promo_spotlight": promo,
    }
