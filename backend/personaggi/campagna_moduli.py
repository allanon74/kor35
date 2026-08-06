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

# Sentinella in scrittura: rimuove l'override e torna al default del registry
# (per «carte» torna al bridge con ConfigurazioneCarteCollezionabili).
MODULO_ACCESSO_DEFAULT = "DEFAULT"

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
MODULO_CONTO_DEPOSITO = "conto_deposito"

# tool staff id → chiave modulo (None = non gated)
STAFF_TOOL_TO_MODULO = {
    "tasks": MODULO_TASKS,
    "pilotaggio": MODULO_PILOTAGGIO,
    "carte-collezionabili": MODULO_CARTE,
    "scommesse": MODULO_SCOMMESSE,
    "negozi-mercante": MODULO_NEGOZI,
    "creazione-guidata": MODULO_CREAZIONE_GUIDATA,
    "social-report": MODULO_SOCIAL,
    "economia-crediti": MODULO_CONTO_DEPOSITO,
}

# tab player id → chiave modulo
PLAYER_TAB_TO_MODULO = {
    "scommesse": MODULO_SCOMMESSE,
    "carte": MODULO_CARTE,
    "negozi": MODULO_NEGOZI,
    "social": MODULO_SOCIAL,
    "tasks": MODULO_TASKS,
    "economia": MODULO_CONTO_DEPOSITO,
}

CAMPAGNA_MODULI_REGISTRY: list[dict[str, Any]] = [
    {
        "key": MODULO_TASKS,
        "label": "Tasks (missioni)",
        "descrizione": "Tab Tasks: missioni evento con premi Crediti/Prestigio.",
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
    {
        "key": MODULO_CONTO_DEPOSITO,
        "label": "Conto di deposito",
        "descrizione": "Economia duale: conto corrente (stipendio) e deposito (altri guadagni), trasferimento per evento.",
        "default": MODULO_ACCESSO_OFF,
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


def validate_moduli_accesso_payload(payload) -> dict[str, str | None]:
    """
    Normalizza il payload di scrittura.

    Valore `None` nel dict risultante = «rimuovi override, torna al default»
    (accettato in ingresso come null, stringa vuota o «DEFAULT»).
    """
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValidationError({"moduli_accesso": "Deve essere un oggetto JSON."})
    cleaned: dict[str, str | None] = {}
    unknown = []
    invalid = []
    for key, val in payload.items():
        key = str(key).strip()
        if key not in _REGISTRY_BY_KEY:
            unknown.append(key)
            continue
        modo = str(val if val is not None else "").strip().upper()
        if modo in ("", MODULO_ACCESSO_DEFAULT):
            cleaned[key] = None
            continue
        if modo not in MODULO_ACCESSO_VALIDI:
            invalid.append(f"{key}={val}")
            continue
        cleaned[key] = modo
    errors = []
    if unknown:
        errors.append(f"Moduli sconosciuti: {', '.join(sorted(unknown))}")
    if invalid:
        errors.append(f"Valori non validi (usa OFF/TEST/OPEN/DEFAULT): {', '.join(invalid)}")
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
    Valore None su una chiave = rimuove l'override (torna al default registry).
    """
    cleaned = validate_moduli_accesso_payload(payload)
    if merge:
        next_map = dict(_raw_moduli(campagna))
        for key, modo in cleaned.items():
            if modo is None:
                next_map.pop(key, None)
            else:
                next_map[key] = modo
    else:
        next_map = {k: v for k, v in cleaned.items() if v is not None}
    # tieni solo chiavi note
    next_map = {k: v for k, v in next_map.items() if k in _REGISTRY_BY_KEY and v in MODULO_ACCESSO_VALIDI}
    campagna.moduli_accesso = next_map
    campagna.save(update_fields=["moduli_accesso", "updated_at"])
    if cleaned.get(MODULO_CARTE):
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


def user_puo_accedere_modulo(user, campagna, key: str) -> bool:
    """
    Accesso a livello utente (tool senza personaggio: wizard, console staff).
    OPEN: tutti; OFF: nessuno; TEST: solo staff/master di campagna.
    """
    modo = get_modulo_accesso(campagna, key)
    if modo == MODULO_ACCESSO_OPEN:
        return True
    if modo == MODULO_ACCESSO_OFF:
        return False
    return user_is_modulo_tester(user, campagna)


def modulo_label(key: str) -> str:
    return _REGISTRY_BY_KEY.get(key, {}).get("label") or key


def modulo_accesso_error(personaggio, key: str, *, user=None) -> str | None:
    """None se il personaggio può usare il modulo, altrimenti il messaggio di rifiuto."""
    if personaggio_puo_accedere_modulo(personaggio, key, user=user):
        return None
    label = modulo_label(key)
    modo = get_modulo_accesso(getattr(personaggio, "campagna", None), key)
    if modo == MODULO_ACCESSO_TEST:
        return f"{label}: in testing — accesso solo per staff/master."
    return f"{label}: modulo non attivo in questa campagna."


def assert_personaggio_puo_accedere_modulo(personaggio, key: str, *, user=None):
    msg = modulo_accesso_error(personaggio, key, user=user)
    if msg:
        raise ValidationError(msg)


def modulo_gate_response(personaggio, key: str, *, user=None, error_key: str = "error"):
    """
    Gate DRF pronto all'uso nelle view: restituisce None se l'accesso è consentito,
    altrimenti una Response 403 con il messaggio del modulo.
    """
    msg = modulo_accesso_error(personaggio, key, user=user)
    if not msg:
        return None
    from rest_framework import status as drf_status
    from rest_framework.response import Response

    return Response({error_key: msg}, status=drf_status.HTTP_403_FORBIDDEN)


def modulo_visibile_in_staff(campagna, key: str) -> bool:
    """Staff tool collegato: nascosto solo se OFF."""
    return get_modulo_accesso(campagna, key) != MODULO_ACCESSO_OFF


def staff_tool_abilitato(campagna, tool_id: str) -> bool:
    key = STAFF_TOOL_TO_MODULO.get(tool_id)
    if not key:
        return True
    return modulo_visibile_in_staff(campagna, key)


def campagna_da_request(request):
    """Campagna attiva della richiesta (header X-Campagna / query, con fallback default)."""
    from personaggi.models import Campagna

    params = getattr(request, "query_params", None) or getattr(request, "GET", {})
    slug = (
        request.headers.get("X-Campagna")
        or params.get("campagna")
        or "kor35"
    ).strip().lower()
    campagna = Campagna.objects.filter(slug=slug, attiva=True).first()
    if campagna:
        return campagna
    return (
        Campagna.objects.filter(attiva=True, is_default=True).first()
        or Campagna.objects.filter(slug="kor35").first()
    )


class ModuloStaffGateMixin:
    """
    Mixin per ViewSet/APIView staff: 403 se il modulo campagna è OFF.
    In TEST il tool staff resta accessibile (serve proprio per il collaudo).
    """

    modulo_key: str = ""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        key = getattr(self, "modulo_key", "")
        if not key:
            return
        campagna = campagna_da_request(request)
        if campagna and not modulo_visibile_in_staff(campagna, key):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                f"{modulo_label(key)}: modulo non attivo in questa campagna."
            )

