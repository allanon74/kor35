"""
Normalizzazione coordinate geografiche per Evento (lat/lng canonici).
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

COORD_DECIMAL_PLACES = 6
_LAT_RANGE = (-90, 90)
_LNG_RANGE = (-180, 180)

_GOOGLE_AT_PATTERN = re.compile(
    r"@(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_GOOGLE_Q_PATTERN = re.compile(
    r"[?&]q=(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_PAIR_PATTERN = re.compile(
    r"^\s*(-?\d+(?:[.,]\d+)?)\s*[,;\s]\s*(-?\d+(?:[.,]\d+)?)\s*$"
)


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        raw = value
    else:
        text = str(value).strip().replace(",", ".")
        if not text:
            return None
        try:
            raw = Decimal(text)
        except (InvalidOperation, ValueError):
            raise ValueError(f"Coordinate non valide: {value!r}")
    quantized = raw.quantize(
        Decimal("1").scaleb(-COORD_DECIMAL_PLACES),
        rounding=ROUND_HALF_UP,
    )
    return quantized


def _validate_range(lat: Decimal, lng: Decimal) -> None:
    if not (_LAT_RANGE[0] <= lat <= _LAT_RANGE[1]):
        raise ValueError(f"Latitudine fuori range ({_LAT_RANGE[0]} … {_LAT_RANGE[1]}).")
    if not (_LNG_RANGE[0] <= lng <= _LNG_RANGE[1]):
        raise ValueError(f"Longitudine fuori range ({_LNG_RANGE[0]} … {_LNG_RANGE[1]}).")


def parse_coordinates_from_text(text: str) -> tuple[Decimal, Decimal]:
    """Estrae lat/lng da testo libero, coppia numerica o URL mappe."""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Testo coordinate vuoto.")

    match = _PAIR_PATTERN.match(raw)
    if match:
        lat = _to_decimal(match.group(1))
        lng = _to_decimal(match.group(2))
        if lat is None or lng is None:
            raise ValueError("Coppia coordinate incompleta.")
        _validate_range(lat, lng)
        return lat, lng

    for pattern in (_GOOGLE_AT_PATTERN, _GOOGLE_Q_PATTERN):
        found = pattern.search(raw)
        if found:
            lat = _to_decimal(found.group(1))
            lng = _to_decimal(found.group(2))
            if lat is None or lng is None:
                raise ValueError("URL mappe senza coordinate valide.")
            _validate_range(lat, lng)
            return lat, lng

    raise ValueError(
        "Formato non riconosciuto. Usa «lat, lng» oppure un link Google Maps."
    )


def normalize_evento_coordinates(
    lat_raw: Any,
    lng_raw: Any,
) -> tuple[Decimal | None, Decimal | None]:
    """
    Restituisce (lat, lng) normalizzati oppure (None, None).
    Se uno solo dei due è valorizzato solleva ValueError.
    """
    lat = _to_decimal(lat_raw)
    lng = _to_decimal(lng_raw)
    if lat is None and lng is None:
        return None, None
    if lat is None or lng is None:
        raise ValueError("Latitudine e longitudine vanno indicate entrambe o lasciate vuote.")
    _validate_range(lat, lng)
    return lat, lng


def evento_ha_info_logistiche(
    logistiche_pubbliche: str | None,
    latitudine: Any,
    longitudine: Any,
) -> bool:
    from django.utils.html import strip_tags

    testo = strip_tags(logistiche_pubbliche or "").strip()
    if testo:
        return True
    try:
        lat, lng = normalize_evento_coordinates(latitudine, longitudine)
    except ValueError:
        return False
    return lat is not None and lng is not None


def build_navigatore_links(lat: Decimal, lng: Decimal) -> dict[str, str]:
    lat_s = format(lat, "f")
    lng_s = format(lng, "f")
    return {
        "geo": f"geo:{lat_s},{lng_s}",
        "google_maps": f"https://www.google.com/maps?q={lat_s},{lng_s}",
        "apple_maps": f"https://maps.apple.com/?ll={lat_s},{lng_s}",
        "waze": f"https://waze.com/ul?ll={lat_s},{lng_s}&navigate=yes",
    }


def geocode_address(query: str) -> tuple[Decimal, Decimal] | None:
    """Geocoding Nominatim (OpenStreetMap) per indirizzo o luogo testuale."""
    q = (query or "").strip()
    if not q:
        return None

    params = urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1},
        quote_via=urllib.parse.quote,
    )
    req = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={
            "User-Agent": "KOR35/1.0 (https://www.kor35.it; staff event geocoding)",
            "Accept-Language": "it",
        },
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if not data:
        return None

    try:
        lat = _to_decimal(data[0]["lat"])
        lng = _to_decimal(data[0]["lon"])
    except (KeyError, ValueError, IndexError):
        return None

    if lat is None or lng is None:
        return None
    _validate_range(lat, lng)
    return lat, lng
