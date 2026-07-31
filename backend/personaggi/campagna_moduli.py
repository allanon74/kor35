"""
Accesso moduli per campagna: OFF / TEST / OPEN.

Pattern allineato a ConfigurazioneCarteCollezionabili.accesso_modo.
- OFF: nascosto a tutti (anche staff UI collegata al modulo)
- TEST: solo staff/master (ruolo campagna STAFFER+) o PnG non giocante / Django staff
- OPEN: tutti i personaggi della campagna

Le chiavi assenti in Campagna.moduli_accesso usano i default del registry
(tranne «carte», che in assenza di override legge la config carte legacy).
"""
from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError

MODULO_ACCESSO_OFF = "OFF"
MODULO_ACCESSO_TEST = "TEST"
MODULO_ACCESSO_OPEN = "OPEN"

MODULO_ACCESSO_CHOICES = [
    (MODULO_ACCESSO_OFF, "Disattivo"),
    (MODULO_ACCESSO_TEST, "Testing (solo staff/master)"),
    (MODULO_ACCESSO_OPEN, "Aperto (tutti)"),
]

MODULO_ACCESSO_VALIDI = {MODULO_ACCESSO_OFF, MODULO_ACCESSO_TEST, MODULO_ACCESSO_OPEN}

MODULO_TASKS = "tasks"
MODULO_PILOTAGGIO = "pilotaggio"
MODULO_CARTE = "carte"
MODULO_SCOMMESSE = "scommesse"
MODULO_SOCIAL = "social"
MODULO_NEGOZI = "negozi"
MODULO_CREAZIONE_GUIDATA = "creazione_guidata"

# tool staff id → chiave modulo (None = non gated)
STAFF_TOOL_TO_MODULO = {
    "tasks": MODULO_TASKS,
    "pilotaggio": MODULO_PILOTAGGIO,
    "carte-collezionabili": MODULO_CARTE,
    "scommesse": MODULO_SCOMMESSE,
    "negozi-mercante": MODULO_NEGOZI,
    "creazione-guidata": MODULO_CREAZIONE_GUIDATA,
    "social-report": MODULO_SOCIAL,
}

# tab player id → chiave modulo
PLAYER_TAB_TO_MODULO = {
    "scommesse": MODULO_SCOMMESSE,
    "carte": MODULO_CARTE,
    "negozi": MODULO_NEGOZI,
    "social": MODULO_SOCIAL,
}

CAMPAGNA_MODULI_REGISTRY: list[dict[str, Any]] = [
    {
        "key": MODULO_TASKS,
        "label": "Tasks (missioni)",
        "descrizione": "Missioni evento con premi Crediti/Prestigio.",
        "default": MODULO_ACCESSO_OFF,
    },
    {
        "key": MODULO_PILOTAGGIO,
        "label": "Pilotaggio",
        "descrizione": "Console nave, stiva, QR sottosistemi.",
        "default": MODULO_ACCESSO_OPEN,
    },
    {
        "key": MODULO_CARTE,
        "label": "Carte collezionabili",
        "descrizione": "Tab Carte e tool staff; sincronizzato con config carte.",
        "default": MODULO_ACCESSO_OFF,
        "bridge_carte": True,
    },
    {
        "key": MODULO_SCOMMESSE,
        "label": "Scommesse",
        "descrizione": "Allibratore e tab scommesse.",
        "default": MODULO_ACCESSO_OPEN,
    },
    {
        "key": MODULO_SOCIAL,
        "label": "Social (InstaFame)",
        "descrizione": "Feed social e report eventi.",
        "default": MODULO_ACCESSO_OPEN,
    },
    {
        "key": MODULO_NEGOZI,
        "label": "Negozi mercante",
        "descrizione": "Tab negozi e gestione listini staff.",
        "default": MODULO_ACCESSO_OPEN,
    },
    {
        "key": MODULO_CREAZIONE_GUIDATA,
        "label": "Creazione guidata PG",
        "descrizione": "Wizard creazione personaggio (staff).",
        "default": MODULO_ACCESSO_OPEN,
    },
]

_REGISTRY_BY_KEY = {row["key"]: row for row in CAMPAGNA_MODULI_REGISTRY}


def moduli_registry_public() -> list[dict[str, Any]]:
    return [
        {
            "key": row["key"],
            "label": row["label"],
            "descrizione": row.get("descrizione") or "",
            "default": row["default"],
        }
        for row in CAMPAGNA_MODULI_REGISTRY
    ]


def _raw_moduli(campagna) -> dict:
    raw = getattr(campagna, "moduli_accesso", None)
    return raw if isinstance(raw, dict) else {}


def has_explicit_modulo(campagna, key: str) -> bool:
    raw = _raw_moduli(campagna)
    val = raw.get(key)
    return val in MODULO_ACCESSO_VALIDI


def _carte_accesso_from_config(campagna) -> str:
    """Legge solo ConfigurazioneCarteCollezionabili (senza moduli_accesso)."""
    from personaggi.carte_collezionabili_models import (
        CARTE_ACCESSO_OFF,
        CARTE_ACCESSO_OPEN,
        ConfigurazioneCarteCollezionabili,
    )

    cfg = ConfigurazioneCarteCollezionabili.objects.filter(campagna=campagna).first()
    if not cfg:
        return CARTE_ACCESSO_OFF
    modo = getattr(cfg, "accesso_modo", None) or CARTE_ACCESSO_OFF
    if modo == CARTE_ACCESSO_OFF and getattr(cfg, "abilitata", False):
        return CARTE_ACCESSO_OPEN
    return modo


def get_modulo_accesso(campagna, key: str) -> str:
    if not campagna:
        return MODULO_ACCESSO_OFF
    if key not in _REGISTRY_BY_KEY:
        return MODULO_ACCESSO_OFF
    if has_explicit_modulo(campagna, key):
        return _raw_moduli(campagna)[key]
    if key == MODULO_CARTE:
        return _carte_accesso_from_config(campagna)
    return _REGISTRY_BY_KEY[key]["default"]


def normalize_moduli_accesso(campagna) -> dict[str, str]:
    """Mappa completa chiave → modo effettivo (con default/bridge)."""
    return {row["key"]: get_modulo_accesso(campagna, row["key"]) for row in CAMPAGNA_MODULI_REGISTRY}


def validate_moduli_accesso_payload(payload) -> dict[str, str]:
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValidationError({"moduli_accesso": "Deve essere un oggetto JSON."})
    cleaned: dict[str, str] = {}
    unknown = []
    invalid = []
    for key, val in payload.items():
        key = str(key).strip()
        if key not in _REGISTRY_BY_KEY:
            unknown.append(key)
            continue
        modo = str(val or "").strip().upper()
        if modo not in MODULO_ACCESSO_VALIDI:
            invalid.append(f"{key}={val}")
            continue
        cleaned[key] = modo
    errors = {}
    if unknown:
        errors["unknown"] = f"Moduli sconosciuti: {', '.join(sorted(unknown))}"
    if invalid:
        errors["invalid"] = f"Valori non validi (usa OFF/TEST/OPEN): {', '.join(invalid)}"
    if errors:
        raise ValidationError({"moduli_accesso": errors})
    return cleaned


def sync_carte_config_from_moduli(campagna, modo: str) -> None:
    """Allinea ConfigurazioneCarteCollezionabili quando si salva il modulo carte."""
    from personaggi.carte_collezionabili_models import ConfigurazioneCarteCollezionabili

    cfg, _ = ConfigurazioneCarteCollezionabili.objects.get_or_create(campagna=campagna)
    cfg.accesso_modo = modo
    cfg.abilitata = modo != MODULO_ACCESSO_OFF
    cfg.save(update_fields=["accesso_modo", "abilitata", "updated_at"])


def apply_moduli_accesso(campagna, payload, *, merge: bool = True) -> dict[str, str]:
    """
    Scrive moduli_accesso sul modello campagna.
    merge=True: aggiorna solo le chiavi passate; False: sostituisce l'intero dict.
    """
    cleaned = validate_moduli_accesso_payload(payload)
    if merge:
        next_map = dict(_raw_moduli(campagna))
        next_map.update(cleaned)
    else:
        next_map = cleaned
    # tieni solo chiavi note
    next_map = {k: v for k, v in next_map.items() if k in _REGISTRY_BY_KEY and v in MODULO_ACCESSO_VALIDI}
    campagna.moduli_accesso = next_map
    campagna.save(update_fields=["moduli_accesso", "updated_at"])
    if MODULO_CARTE in cleaned:
        sync_carte_config_from_moduli(campagna, cleaned[MODULO_CARTE])
    return normalize_moduli_accesso(campagna)


def user_is_modulo_tester(user, campagna) -> bool:
    """True se l'utente può vedere moduli in modalità TEST."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    if not campagna:
        return False
    from personaggi.models import (
        CAMPAGNA_ROLE_HEAD_MASTER,
        CAMPAGNA_ROLE_MASTER,
        CAMPAGNA_ROLE_STAFFER,
        CampagnaUtente,
    )

    ruolo = (
        CampagnaUtente.objects.filter(campagna=campagna, user=user, attivo=True)
        .values_list("ruolo", flat=True)
        .first()
    )
    return ruolo in (CAMPAGNA_ROLE_STAFFER, CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER)


def is_png_non_giocante(personaggio) -> bool:
    return bool(
        personaggio
        and personaggio.tipologia_id
        and personaggio.tipologia
        and not personaggio.tipologia.giocante
    )


def personaggio_puo_accedere_modulo(personaggio, key: str, *, user=None) -> bool:
    if not personaggio:
        return False
    campagna = getattr(personaggio, "campagna", None)
    modo = get_modulo_accesso(campagna, key)
    if modo == MODULO_ACCESSO_OPEN:
        return True
    if modo == MODULO_ACCESSO_OFF:
        return False
    # TEST
    u = user if user is not None else getattr(personaggio, "proprietario", None)
    if user_is_modulo_tester(u, campagna):
        return True
    if is_png_non_giocante(personaggio):
        return True
    return False


def assert_personaggio_puo_accedere_modulo(personaggio, key: str, *, user=None):
    if personaggio_puo_accedere_modulo(personaggio, key, user=user):
        return
    label = _REGISTRY_BY_KEY.get(key, {}).get("label") or key
    modo = get_modulo_accesso(getattr(personaggio, "campagna", None), key)
    if modo == MODULO_ACCESSO_TEST:
        raise ValidationError(f"{label}: in testing — accesso solo per staff/master.")
    raise ValidationError(f"{label}: modulo non attivo in questa campagna.")


def modulo_visibile_in_staff(campagna, key: str) -> bool:
    """Staff tool collegato: nascosto solo se OFF."""
    return get_modulo_accesso(campagna, key) != MODULO_ACCESSO_OFF


def staff_tool_abilitato(campagna, tool_id: str) -> bool:
    key = STAFF_TOOL_TO_MODULO.get(tool_id)
    if not key:
        return True
    return modulo_visibile_in_staff(campagna, key)
