"""
Allarme equipaggio nave (Giallo / Rosso / Nero / Blu / crociera).

Predisposizione LED WiFi: i dispositivi in LAN possono leggere lo stato cromatico
da GET /api/pilot/allarme-led/state/ (nessuna autenticazione; solo rete locale).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from django.utils import timezone

ALLARME_EQUIPAGGIO_CROCIERA = "crociera"
ALLARME_EQUIPAGGIO_GIALLO = "giallo"
ALLARME_EQUIPAGGIO_ROSSO = "rosso"
ALLARME_EQUIPAGGIO_NERO = "nero"
ALLARME_EQUIPAGGIO_BLU = "blu"

ALLARME_EQUIPAGGIO_CHOICES = [
    (ALLARME_EQUIPAGGIO_CROCIERA, "Crociera (nessun allarme)"),
    (ALLARME_EQUIPAGGIO_GIALLO, "Allarme giallo"),
    (ALLARME_EQUIPAGGIO_ROSSO, "Allarme rosso"),
    (ALLARME_EQUIPAGGIO_NERO, "Allarme nero"),
    (ALLARME_EQUIPAGGIO_BLU, "Allarme blu"),
]

ALLARME_EQUIPAGGIO_VALIDI = frozenset(
    c[0] for c in ALLARME_EQUIPAGGIO_CHOICES
)

# Frasi vocali console pilota
ANNUNCIO_VOCALE_ALLARME: Dict[str, str] = {
    ALLARME_EQUIPAGGIO_GIALLO: (
        "Allarme Giallo. Condizione di allerta dell'equipaggio."
    ),
    ALLARME_EQUIPAGGIO_ROSSO: (
        "Allarme Rosso. Tutti ai posti di combattimento. "
        "Questa non è un'esercitazione."
    ),
    ALLARME_EQUIPAGGIO_NERO: (
        "Allarme Nero. Sistema esotico in attivazione. "
        "Prepararsi a condizioni impreviste."
    ),
    ALLARME_EQUIPAGGIO_BLU: (
        "Allarme Blu. Manovre atmosferiche in corso, "
        "prepararsi a scompensi nel volo."
    ),
    ALLARME_EQUIPAGGIO_CROCIERA: (
        "Allarme Verde. Ripristino condizione di crociera. Nessun allarme attivo."
    ),
}

# Schema v1 per futuri controller LED WiFi (URL locale, polling HTTP)
LED_PROFILE_ALLARME: Dict[str, Dict[str, Any]] = {
    ALLARME_EQUIPAGGIO_CROCIERA: {
        "hex": "#4CAF50",
        "rgb": [76, 175, 80],
        "modalita": "steady",
        "luminosita": 0.85,
        "nome_led": "verde",
    },
    ALLARME_EQUIPAGGIO_GIALLO: {
        "hex": "#FFD700",
        "rgb": [255, 215, 0],
        "modalita": "pulse",
        "luminosita": 1.0,
        "pulse_ms": 1200,
    },
    ALLARME_EQUIPAGGIO_ROSSO: {
        "hex": "#FF3030",
        "rgb": [255, 48, 48],
        "modalita": "pulse",
        "luminosita": 1.0,
        "pulse_ms": 600,
    },
    ALLARME_EQUIPAGGIO_NERO: {
        "hex": "#120818",
        "rgb": [18, 8, 24],
        "modalita": "pulse",
        "luminosita": 0.9,
        "pulse_ms": 1800,
        "accent_hex": "#6A1B9A",
    },
    ALLARME_EQUIPAGGIO_BLU: {
        "hex": "#2979FF",
        "rgb": [41, 121, 255],
        "modalita": "pulse",
        "luminosita": 1.0,
        "pulse_ms": 900,
    },
}

LED_API_SCHEMA_VERSION = 1


def normalizza_allarme_equipaggio(valore: Optional[str]) -> str:
    key = str(valore or ALLARME_EQUIPAGGIO_CROCIERA).strip().lower()
    if key not in ALLARME_EQUIPAGGIO_VALIDI:
        raise ValueError(
            "Allarme non valido: usare crociera, giallo, rosso, nero o blu."
        )
    return key


def annuncio_vocale_allarme(allarme: str) -> str:
    return ANNUNCIO_VOCALE_ALLARME.get(
        normalizza_allarme_equipaggio(allarme),
        ANNUNCIO_VOCALE_ALLARME[ALLARME_EQUIPAGGIO_CROCIERA],
    )


def profilo_led_allarme(allarme: str) -> Dict[str, Any]:
    key = normalizza_allarme_equipaggio(allarme)
    profilo = dict(LED_PROFILE_ALLARME[key])
    profilo["nome"] = profilo.pop("nome_led", None) or key
    return profilo


def build_allarme_led_payload(sessione=None) -> Dict[str, Any]:
    """
    Payload per dispositivi LED WiFi (polling su URL relativo nginx).
    """
    allarme = ALLARME_EQUIPAGGIO_CROCIERA
    updated_at = None
    sessione_attiva = False
    sessione_id = None

    if sessione is not None:
        allarme = normalizza_allarme_equipaggio(
            getattr(sessione, "allarme_equipaggio", ALLARME_EQUIPAGGIO_CROCIERA)
        )
        updated_at = getattr(sessione, "allarme_equipaggio_at", None)
        sessione_attiva = bool(getattr(sessione, "is_attiva", False))
        sessione_id = str(sessione.pk)

    profilo = profilo_led_allarme(allarme)
    ts = updated_at or timezone.now()

    return {
        "schema_version": LED_API_SCHEMA_VERSION,
        "allarme": allarme,
        "crociera": allarme == ALLARME_EQUIPAGGIO_CROCIERA,
        "sessione_attiva": sessione_attiva,
        "sessione_id": sessione_id,
        "annuncio_vocale": annuncio_vocale_allarme(allarme),
        "colore": profilo,
        "updated_at": ts.isoformat(),
        "poll_hint_seconds": 2,
        "endpoint_doc": (
            "Dispositivi LED WiFi: GET /api/pilot/allarme-led/state/ "
            "(rete locale, senza auth). Applicare colore.hex e colore.modalita."
        ),
    }


def imposta_allarme_equipaggio_sessione(sessione, allarme: str) -> str:
    """Aggiorna allarme equipaggio sulla sessione; ritorna annuncio vocale."""
    from .models import SessioneVolo

    if not isinstance(sessione, SessioneVolo):
        raise ValueError("Sessione non valida.")
    if sessione.is_terminata:
        raise ValueError("Sessione terminata.")

    key = normalizza_allarme_equipaggio(allarme)
    now = timezone.now()
    sessione.allarme_equipaggio = key
    sessione.allarme_equipaggio_at = now
    sessione.save(
        update_fields=["allarme_equipaggio", "allarme_equipaggio_at", "updated_at"]
    )
    return annuncio_vocale_allarme(key)


def reset_allarme_equipaggio_sessione(sessione) -> None:
    """Ripristina crociera (es. fine volo)."""
    if getattr(sessione, "allarme_equipaggio", ALLARME_EQUIPAGGIO_CROCIERA) == (
        ALLARME_EQUIPAGGIO_CROCIERA
    ):
        return
    sessione.allarme_equipaggio = ALLARME_EQUIPAGGIO_CROCIERA
    sessione.allarme_equipaggio_at = timezone.now()
    sessione.save(
        update_fields=["allarme_equipaggio", "allarme_equipaggio_at", "updated_at"]
    )
