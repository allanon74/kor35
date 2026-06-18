"""Validazione nickname InstaFame (emoji e sequenze Unicode)."""

from __future__ import annotations

import regex as re
from django.core.exceptions import ValidationError
from rest_framework import serializers

# Limite visibile al giocatore (grafemi: lettere + emoji = 1 ciascuno).
NICKNAME_MAX_GRAPHEMES = 40

_GRAPHEME_RE = re.compile(r"\X")


def grapheme_len(value: str) -> int:
    return len(_GRAPHEME_RE.findall(value or ""))


def clean_nickname_value(value) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if grapheme_len(cleaned) > NICKNAME_MAX_GRAPHEMES:
        raise serializers.ValidationError(
            f"Il nickname può avere al massimo {NICKNAME_MAX_GRAPHEMES} caratteri "
            f"(le emoji contano come un carattere ciascuna)."
        )
    return cleaned


def clean_nickname_value_model(value) -> str | None:
    """Stessa logica per `Model.clean` / admin."""
    try:
        return clean_nickname_value(value)
    except serializers.ValidationError as exc:
        detail = exc.detail
        if isinstance(detail, list):
            raise ValidationError(detail[0])
        raise ValidationError(detail)
