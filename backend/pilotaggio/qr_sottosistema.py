"""
Scansione QR collegati a SottosistemaNave: telemetria runtime, sabotaggio e riparazione.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from personaggi.models import MinigiocoQrConfig, QrCode

SIGLA_SABOTAGGIO = "0SA"
SIGLA_RIPARAZIONE = "0RI"


def sottosistema_per_qr(qr_code: QrCode):
    from .models import SottosistemaNave

    if qr_code is None or qr_code.vista_id is None:
        return None
    return SottosistemaNave.objects.filter(a_vista_id=qr_code.vista_id).first()


def sessione_attiva_corrente():
    from .views import _sessione_attiva_corrente

    return _sessione_attiva_corrente()


def _valore_statistica_pg(personaggio, sigla: str) -> int:
    if personaggio is None:
        return 0
    return int(personaggio.get_valore_statistica(sigla) or 0)


def minigioco_richiesto_per_ripara(qr_code: QrCode) -> bool:
    from personaggi.qr_minigioco import _config_attiva, _sezione_minigioco_attiva

    try:
        config = qr_code.configurazione_minigioco
    except MinigiocoQrConfig.DoesNotExist:
        return False
    if not _sezione_minigioco_attiva(config):
        return False
    return _config_attiva(config)


def _stato_runtime_payload(stato) -> Optional[dict]:
    if stato is None:
        return None
    from .serializers import StatoSottosistemaRuntimeSerializer

    data = dict(StatoSottosistemaRuntimeSerializer(stato).data)
    recovery_at = getattr(stato, "recovery_at", None)
    if recovery_at and recovery_at > timezone.now():
        data["recovery_remaining_seconds"] = max(
            0, int((recovery_at - timezone.now()).total_seconds())
        )
    else:
        data["recovery_remaining_seconds"] = 0
    data["guasto"] = not bool(stato.online)
    data["in_ripristino"] = bool(
        not stato.online and recovery_at and recovery_at > timezone.now()
    )
    return data


def stato_immersivo_payload(stato, stato_data: Optional[dict], sessione_attiva: bool) -> dict:
    """Etichette telemetria per la UI scanner (terminologia di bordo)."""
    if not sessione_attiva or stato is None or not stato_data:
        return {
            "codice": "no_bus",
            "etichetta": "Bus telemetria assente",
            "descrizione": "Nessuna sessione di volo attiva — dati di catalogo soltanto.",
            "classe": "muted",
            "livello_potenza": None,
        }

    if stato_data.get("in_ripristino"):
        sec = stato_data.get("recovery_remaining_seconds") or 0
        return {
            "codice": "ricalibrazione",
            "etichetta": "Ricalibrazione in corso",
            "descrizione": f"Matrice sottosistema in ripristino automatico — ETA {sec}s.",
            "classe": "warning",
            "livello_potenza": 0,
        }

    if getattr(stato, "espulso", False):
        return {
            "codice": "espulso",
            "etichetta": "Modulo espulso",
            "descrizione": "Subsistema isolato dal bus primario — intervento plancia richiesto.",
            "classe": "danger",
            "livello_potenza": 0,
        }

    if stato_data.get("guasto") or not getattr(stato, "online", True):
        return {
            "codice": "fault",
            "etichetta": "Fault critico",
            "descrizione": "Anomalia strutturale — erogazione interrotta, linea fuori servizio.",
            "classe": "danger",
            "livello_potenza": 0,
        }

    livello = int(stato.livello_attuale or 0)
    target = int(stato.livello_target or 0)
    if livello <= 0:
        return {
            "codice": "standby",
            "etichetta": "Standby",
            "descrizione": "Subsistema in risparmio energetico — erogazione nulla.",
            "classe": "muted",
            "livello_potenza": 0,
            "livello_target": target,
        }

    rampa = livello != target
    desc = (
        f"Flusso operativo — erogazione {livello}/9"
        + (f" (rampa verso {target})" if rampa else "")
        + "."
    )
    return {
        "codice": "operativo",
        "etichetta": f"Erogazione {livello}/9",
        "descrizione": desc,
        "classe": "ok",
        "livello_potenza": livello,
        "livello_target": target,
    }


def build_scan_payload(
    *,
    qr_code: QrCode,
    sottosistema,
    scanner_pg=None,
) -> Dict[str, Any]:
    from .engine import applica_recoveries_pendenti, get_o_crea_stato_sottosistema
    from .serializers import SottosistemaNaveSerializer

    sessione = sessione_attiva_corrente()
    stato = None
    if sessione is not None:
        applica_recoveries_pendenti(sessione)
        stato = get_o_crea_stato_sottosistema(sessione, sottosistema)

    stato_data = _stato_runtime_payload(stato)
    guasto = bool(stato_data and stato_data.get("guasto"))
    in_ripristino = bool(stato_data and stato_data.get("in_ripristino"))
    sessione_attiva = sessione is not None

    v_sa = _valore_statistica_pg(scanner_pg, SIGLA_SABOTAGGIO)
    v_ri = _valore_statistica_pg(scanner_pg, SIGLA_RIPARAZIONE)
    minigioco_riparazione = minigioco_richiesto_per_ripara(qr_code)

    puo_sabotare = bool(
        sessione_attiva
        and scanner_pg is not None
        and v_sa > 0
        and stato is not None
        and stato.online
        and not in_ripristino
        and not getattr(stato, "espulso", False)
    )
    puo_riparare = bool(
        sessione_attiva
        and scanner_pg is not None
        and v_ri > 0
        and guasto
        and not in_ripristino
    )

    manifesto_testo = ""
    if qr_code.vista_id:
        try:
            from personaggi.models import Manifesto

            man = Manifesto.objects.filter(pk=qr_code.vista_id).first()
            if man:
                manifesto_testo = man.testo or ""
        except Exception:
            pass

    telemetria = stato_immersivo_payload(stato, stato_data, sessione_attiva)

    return {
        "tipo_modello": "pilot_sottosistema",
        "qrcode_id": qr_code.id,
        "messaggio": f"Nodo {sottosistema.codice} — {sottosistema.nome}",
        "dati": {
            "sottosistema": SottosistemaNaveSerializer(sottosistema).data,
            "stato": stato_data,
            "telemetria": telemetria,
            "sessione_attiva": sessione_attiva,
            "sessione_id": str(sessione.pk) if sessione else None,
            "guasto": guasto,
            "in_ripristino": in_ripristino,
            "puo_sabotare": puo_sabotare,
            "puo_riparare": puo_riparare,
            "statistiche_scanner": {
                SIGLA_SABOTAGGIO: v_sa,
                SIGLA_RIPARAZIONE: v_ri,
            },
            "minigioco_riparazione": minigioco_riparazione,
            "manifesto_testo": manifesto_testo,
        },
    }


def _verifica_minigioco_completato(personaggio, qr_code, minigioco_session_id: Optional[str]) -> tuple[bool, str]:
    if not minigioco_richiesto_per_ripara(qr_code):
        return True, ""

    from personaggi.qr_minigioco import session_allows_bypass

    if not minigioco_session_id:
        return False, "Completa il minigioco prima di riparare."
    if not session_allows_bypass(minigioco_session_id, personaggio, qr_code):
        return False, "Sessione minigioco non valida o non completata."
    return True, ""


@transaction.atomic
def sabota_sottosistema_da_qr(*, qr_code: QrCode, personaggio) -> Dict[str, Any]:
    """Guasto immediato sul sottosistema (richiede 0SA > 0 sul PG scanner)."""
    from .engine import applica_effetto_guasto, get_o_crea_stato_sottosistema
    from .flight_log import log_guasto_sottosistema
    from .views import _ensure_runtime_subsystems

    if _valore_statistica_pg(personaggio, SIGLA_SABOTAGGIO) <= 0:
        return {
            "ok": False,
            "error": f"Servono punti {SIGLA_SABOTAGGIO} per sabotare un subsistema.",
        }

    sottosistema = sottosistema_per_qr(qr_code)
    if sottosistema is None:
        return {"ok": False, "error": "QR non collegato a un sottosistema nave."}

    sessione = sessione_attiva_corrente()
    if sessione is None:
        return {"ok": False, "error": "Nessuna sessione di volo attiva."}

    _ensure_runtime_subsystems(sessione)
    stato = get_o_crea_stato_sottosistema(sessione, sottosistema)

    if not stato.online:
        return {"ok": False, "error": "Il subsistema è già in fault."}

    if stato.recovery_at and stato.recovery_at > timezone.now():
        remain = int((stato.recovery_at - timezone.now()).total_seconds())
        return {
            "ok": False,
            "error": f"Ricalibrazione in corso ({remain}s rimanenti).",
        }

    now = timezone.now()
    stato.online = False
    stato.guasto_at = now
    stato.recovery_at = None
    stato.save(update_fields=["online", "guasto_at", "recovery_at", "updated_at"])
    applica_effetto_guasto(sessione, stato)
    log_guasto_sottosistema(sessione, stato, causa="qr")

    payload = build_scan_payload(
        qr_code=qr_code,
        sottosistema=sottosistema,
        scanner_pg=personaggio,
    )
    payload["messaggio"] = (
        f"Subsistema {sottosistema.codice} sabotato — fault critico registrato sul bus."
    )
    payload["azione"] = "sabotato"
    return {"ok": True, **payload}


@transaction.atomic
def ripristina_sottosistema_da_qr(
    *,
    qr_code: QrCode,
    personaggio,
    minigioco_session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ripara un sottosistema guasto dopo (eventuale) minigioco (richiede 0RI > 0).
    """
    from personaggi.qr_minigioco import verifica_accesso_qr_minigioco

    from .engine import get_o_crea_stato_sottosistema
    from .views import _ensure_runtime_subsystems

    if _valore_statistica_pg(personaggio, SIGLA_RIPARAZIONE) <= 0:
        return {
            "ok": False,
            "error": f"Servono punti {SIGLA_RIPARAZIONE} per riparare un subsistema.",
        }

    sottosistema = sottosistema_per_qr(qr_code)
    if sottosistema is None:
        return {"ok": False, "error": "QR non collegato a un sottosistema nave."}

    sessione = sessione_attiva_corrente()
    if sessione is None:
        return {"ok": False, "error": "Nessuna sessione di volo attiva."}

    try:
        config = qr_code.configurazione_minigioco
    except MinigiocoQrConfig.DoesNotExist:
        config = None

    if config and getattr(config, "sezione_attiva", False) and config.requisiti_attivazione:
        ok, msg = verifica_accesso_qr_minigioco(personaggio, config)
        if not ok:
            return {"ok": False, "error": msg or "Requisiti non soddisfatti."}

    ok_mg, err_mg = _verifica_minigioco_completato(personaggio, qr_code, minigioco_session_id)
    if not ok_mg:
        return {"ok": False, "error": err_mg}

    _ensure_runtime_subsystems(sessione)
    stato = get_o_crea_stato_sottosistema(sessione, sottosistema)

    if stato.online:
        return {"ok": False, "error": "Il subsistema è già operativo."}

    if stato.recovery_at and stato.recovery_at > timezone.now():
        remain = int((stato.recovery_at - timezone.now()).total_seconds())
        return {
            "ok": False,
            "error": f"Ricalibrazione già in corso ({remain}s rimanenti).",
        }

    from .engine import _clamp_livello

    stato.online = True
    stato.guasto_at = None
    stato.recovery_at = None
    stato.livello_attuale = _clamp_livello(stato.livello_target)
    stato.save(
        update_fields=[
            "online",
            "guasto_at",
            "recovery_at",
            "livello_attuale",
            "updated_at",
        ]
    )

    payload = build_scan_payload(
        qr_code=qr_code,
        sottosistema=sottosistema,
        scanner_pg=personaggio,
    )
    payload["messaggio"] = (
        f"Subsistema {sottosistema.codice} riparato — erogazione ripristinata a "
        f"{stato.livello_attuale}/9."
    )
    payload["azione"] = "riparato"
    return {"ok": True, **payload}
