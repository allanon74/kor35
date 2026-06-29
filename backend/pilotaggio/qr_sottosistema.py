"""
Scansione QR collegati a SottosistemaNave: telemetria runtime, sabotaggio e riparazione.

Stato persistente sulla nave (riposo o volo): guasti e livelli sopravvivono al cambio sessione.
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


def sessione_console_corrente():
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
    data["espulso"] = bool(getattr(stato, "espulso", False))
    return data


def stato_immersivo_payload(
    stato,
    stato_data: Optional[dict],
    *,
    fase_operativa: str,
) -> dict:
    """Etichette telemetria per la UI scanner (terminologia di bordo)."""
    if stato is None or not stato_data:
        return {
            "codice": "no_bus",
            "etichetta": "Telemetria non disponibile",
            "descrizione": "Stato subsistema non ancora inizializzato.",
            "classe": "muted",
            "livello_potenza": None,
        }

    if fase_operativa == "riposo":
        base_desc = "Nave in riposo — bus di bordo attivo."
    elif fase_operativa == "volo":
        base_desc = "Sessione di volo attiva."
    else:
        base_desc = "Telemetria da registro nave persistente."

    if stato_data.get("in_ripristino"):
        sec = stato_data.get("recovery_remaining_seconds") or 0
        return {
            "codice": "ricalibrazione",
            "etichetta": "Ricalibrazione in corso",
            "descrizione": f"Matrice in ripristino programmato — ETA {sec}s. {base_desc}",
            "classe": "warning",
            "livello_potenza": 0,
        }

    if stato_data.get("espulso"):
        return {
            "codice": "espulso",
            "etichetta": "Modulo espulso",
            "descrizione": (
                "Subsistema isolato dal bus primario — reintegrazione solo da plancia master."
            ),
            "classe": "danger",
            "livello_potenza": 0,
        }

    if stato_data.get("guasto") or not getattr(stato, "online", True):
        return {
            "codice": "fault",
            "etichetta": "Fault critico",
            "descrizione": (
                "Anomalia strutturale — erogazione interrotta fino a riparazione manuale. "
                + base_desc
            ),
            "classe": "danger",
            "livello_potenza": 0,
        }

    livello = int(stato.livello_attuale or 0)
    target = int(stato.livello_target or 0)
    if livello <= 0:
        return {
            "codice": "standby",
            "etichetta": "Standby",
            "descrizione": f"Subsistema in risparmio energetico. {base_desc}",
            "classe": "muted",
            "livello_potenza": 0,
            "livello_target": target,
        }

    rampa = livello != target
    desc = (
        f"Flusso operativo — erogazione {livello}/9"
        + (f" (rampa verso {target})" if rampa else "")
        + f". {base_desc}"
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
    from .engine import applica_recoveries_pendenti
    from .serializers import SottosistemaNaveSerializer
    from .stato_nave import fase_operativa_sessione, stato_operativo_sottosistema

    sessione = sessione_console_corrente()
    if sessione is not None:
        applica_recoveries_pendenti(sessione)
    stato = stato_operativo_sottosistema(sottosistema, sessione)

    stato_data = _stato_runtime_payload(stato)
    guasto = bool(stato_data and stato_data.get("guasto"))
    in_ripristino = bool(stato_data and stato_data.get("in_ripristino"))
    espulso = bool(stato_data and stato_data.get("espulso"))
    fase = fase_operativa_sessione(sessione)
    bus_attivo = stato is not None

    v_sa = _valore_statistica_pg(scanner_pg, SIGLA_SABOTAGGIO)
    v_ri = _valore_statistica_pg(scanner_pg, SIGLA_RIPARAZIONE)
    minigioco_riparazione = minigioco_richiesto_per_ripara(qr_code)

    puo_sabotare = bool(
        bus_attivo
        and scanner_pg is not None
        and v_sa > 0
        and stato is not None
        and stato.online
        and not in_ripristino
        and not espulso
    )
    puo_riparare = bool(
        bus_attivo
        and scanner_pg is not None
        and v_ri > 0
        and guasto
        and not in_ripristino
        and not espulso
    )

    from .componenti_ricarica import build_requisiti_ricarica_payload, ricarica_componenti_attiva_per

    requisiti_ricarica = build_requisiti_ricarica_payload(sottosistema)
    puo_ricaricare = bool(
        bus_attivo
        and sessione is not None
        and scanner_pg is not None
        and v_ri > 0
        and not guasto
        and not in_ripristino
        and not espulso
        and ricarica_componenti_attiva_per(sottosistema)
    )

    from .componenti_riparazione import build_requisiti_riparazione_payload

    requisiti_componenti = build_requisiti_riparazione_payload(sottosistema)

    manifesto_testo = ""
    if qr_code.vista_id:
        try:
            from personaggi.models import Manifesto

            man = Manifesto.objects.filter(pk=qr_code.vista_id).first()
            if man:
                manifesto_testo = man.testo or ""
        except Exception:
            pass

    telemetria = stato_immersivo_payload(stato, stato_data, fase_operativa=fase)

    return {
        "tipo_modello": "pilot_sottosistema",
        "qrcode_id": qr_code.id,
        "messaggio": f"Nodo {sottosistema.codice} — {sottosistema.nome}",
        "dati": {
            "sottosistema": SottosistemaNaveSerializer(sottosistema).data,
            "stato": stato_data,
            "telemetria": telemetria,
            "fase_operativa": fase,
            "sessione_attiva": sessione is not None,
            "bus_telemetria_attivo": bus_attivo,
            "sessione_id": str(sessione.pk) if sessione else None,
            "guasto": guasto,
            "in_ripristino": in_ripristino,
            "espulso": espulso,
            "puo_sabotare": puo_sabotare,
            "puo_riparare": puo_riparare,
            "statistiche_scanner": {
                SIGLA_SABOTAGGIO: v_sa,
                SIGLA_RIPARAZIONE: v_ri,
            },
            "minigioco_riparazione": minigioco_riparazione,
            "requisiti_componenti": requisiti_componenti,
            "puo_ricaricare": puo_ricaricare,
            "requisiti_ricarica_componenti": requisiti_ricarica,
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


def _applica_guasto_stato(stato, sessione) -> None:
    from .engine import applica_effetto_guasto
    from .flight_log import log_guasto_sottosistema

    now = timezone.now()
    stato.online = False
    stato.guasto_at = now
    stato.recovery_at = None
    stato.save(update_fields=["online", "guasto_at", "recovery_at", "updated_at"])
    if sessione is not None:
        applica_effetto_guasto(sessione, stato)
        log_guasto_sottosistema(sessione, stato, causa="qr")


@transaction.atomic
def sabota_sottosistema_da_qr(*, qr_code: QrCode, personaggio) -> Dict[str, Any]:
    """Guasto immediato (0SA > 0); persiste sulla nave e sulla sessione idle/volo se presente."""
    from .stato_nave import stato_operativo_sottosistema
    from .views import _ensure_runtime_subsystems

    if _valore_statistica_pg(personaggio, SIGLA_SABOTAGGIO) <= 0:
        return {
            "ok": False,
            "error": f"Servono punti {SIGLA_SABOTAGGIO} per sabotare un subsistema.",
        }

    sottosistema = sottosistema_per_qr(qr_code)
    if sottosistema is None:
        return {"ok": False, "error": "QR non collegato a un sottosistema nave."}

    sessione = sessione_console_corrente()
    if sessione is not None:
        _ensure_runtime_subsystems(sessione)
    stato = stato_operativo_sottosistema(sottosistema, sessione)

    if getattr(stato, "espulso", False):
        return {"ok": False, "error": "Il modulo è espulso: non sabotabile da QR."}

    if not stato.online:
        return {"ok": False, "error": "Il subsistema è già in fault."}

    if stato.recovery_at and stato.recovery_at > timezone.now():
        remain = int((stato.recovery_at - timezone.now()).total_seconds())
        return {
            "ok": False,
            "error": f"Ricalibrazione in corso ({remain}s rimanenti).",
        }

    _applica_guasto_stato(stato, sessione)

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
    componenti_scelti: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Ripara un subsistema in fault (0RI > 0, minigioco se configurato).
    Non reintegra moduli espulsi (solo plancia master).
    """
    from personaggi.qr_minigioco import verifica_accesso_qr_minigioco

    from .engine import _clamp_livello
    from .stato_nave import stato_operativo_sottosistema
    from .views import _ensure_runtime_subsystems

    if _valore_statistica_pg(personaggio, SIGLA_RIPARAZIONE) <= 0:
        return {
            "ok": False,
            "error": f"Servono punti {SIGLA_RIPARAZIONE} per riparare un subsistema.",
        }

    sottosistema = sottosistema_per_qr(qr_code)
    if sottosistema is None:
        return {"ok": False, "error": "QR non collegato a un sottosistema nave."}

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

    from .componenti_riparazione import (
        riparazione_componenti_attiva_per,
        valida_selezione_componenti,
    )
    from .componenti_stiva import consuma_mattoni_stiva

    if riparazione_componenti_attiva_per(sottosistema):
        ok_sel, err_sel, allocazioni = valida_selezione_componenti(
            sottosistema, componenti_scelti or []
        )
        if not ok_sel:
            return {"ok": False, "error": err_sel}
        try:
            consuma_mattoni_stiva(allocazioni)
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}

    sessione = sessione_console_corrente()
    if sessione is not None:
        _ensure_runtime_subsystems(sessione)
    stato = stato_operativo_sottosistema(sottosistema, sessione)

    if getattr(stato, "espulso", False):
        return {
            "ok": False,
            "error": "Modulo espulso: reintegrazione solo dalla console di pilotaggio.",
        }

    if stato.online:
        return {"ok": False, "error": "Il subsistema è già operativo."}

    if stato.recovery_at and stato.recovery_at > timezone.now():
        remain = int((stato.recovery_at - timezone.now()).total_seconds())
        return {
            "ok": False,
            "error": f"Ricalibrazione già in corso ({remain}s rimanenti).",
        }

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
    if sessione is not None:
        from .engine import marca_immunita_riparazione

        marca_immunita_riparazione(sessione, sottosistema.pk)

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


@transaction.atomic
def ricarica_sottosistema_da_qr(
    *,
    qr_code: QrCode,
    personaggio,
    componenti_scelti: Optional[list] = None,
) -> Dict[str, Any]:
    """Ricarica storage (batteria) o carburante (serbatoio) consumando componenti da stiva."""
    from .componenti_ricarica import valida_selezione_ricarica
    from .componenti_stiva import consuma_mattoni_stiva
    from .models import SessioneVolo
    from .stato_nave import stato_operativo_sottosistema
    from .views import _ensure_runtime_subsystems

    if _valore_statistica_pg(personaggio, SIGLA_RIPARAZIONE) <= 0:
        return {
            "ok": False,
            "error": f"Servono punti {SIGLA_RIPARAZIONE} per operare sui subsistemi.",
        }

    sottosistema = sottosistema_per_qr(qr_code)
    if sottosistema is None:
        return {"ok": False, "error": "QR non collegato a un sottosistema nave."}

    tipo = str(sottosistema.tipo or "").strip().lower()
    if tipo not in {"batteria", "serbatoio"}:
        return {"ok": False, "error": "Ricarica a componenti solo su batterie o serbatoi."}

    from .componenti_ricarica import ricarica_componenti_attiva_per

    if not ricarica_componenti_attiva_per(sottosistema):
        return {"ok": False, "error": "Ricarica a componenti non abilitata per questo nodo."}

    sessione = sessione_console_corrente()
    if sessione is None:
        return {"ok": False, "error": "Serve una sessione console attiva per ricaricare."}

    _ensure_runtime_subsystems(sessione)
    stato = stato_operativo_sottosistema(sottosistema, sessione)

    if getattr(stato, "espulso", False):
        return {"ok": False, "error": "Modulo espulso: ricarica non disponibile."}
    if not stato.online:
        return {"ok": False, "error": "Subsistema in fault: ripara prima di ricaricare."}
    if stato.recovery_at and stato.recovery_at > timezone.now():
        remain = int((stato.recovery_at - timezone.now()).total_seconds())
        return {"ok": False, "error": f"Ricalibrazione in corso ({remain}s rimanenti)."}

    ok_sel, err_sel, allocazioni, importo = valida_selezione_ricarica(
        sottosistema, componenti_scelti or []
    )
    if not ok_sel:
        return {"ok": False, "error": err_sel}
    try:
        consuma_mattoni_stiva(allocazioni)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    sessione = SessioneVolo.objects.select_for_update().get(pk=sessione.pk)
    if tipo == "batteria":
        sessione.storage_energia_attuale = min(
            float(sessione.storage_energia_massimo or 0),
            float(sessione.storage_energia_attuale or 0) + importo,
        )
        sessione.save(update_fields=["storage_energia_attuale", "updated_at"])
        unita = "energia storage"
    else:
        sessione.carburante_attuale = min(
            float(sessione.carburante_massimo or 0),
            float(sessione.carburante_attuale or 0) + importo,
        )
        sessione.save(update_fields=["carburante_attuale", "updated_at"])
        unita = "carburante"

    payload = build_scan_payload(
        qr_code=qr_code,
        sottosistema=sottosistema,
        scanner_pg=personaggio,
    )
    payload["messaggio"] = (
        f"Ricarica completata — +{importo:g} {unita} "
        f"(storage {round(float(sessione.storage_energia_attuale or 0))}/{round(float(sessione.storage_energia_massimo or 0))} · "
        f"carburante {round(float(sessione.carburante_attuale or 0))}/{round(float(sessione.carburante_massimo or 0))})."
    )
    payload["azione"] = "ricaricato"
    payload["ricarica"] = {
        "importo": importo,
        "unita": unita,
        "tipo_sottosistema": tipo,
        "storage_energia_attuale": float(sessione.storage_energia_attuale or 0),
        "carburante_attuale": float(sessione.carburante_attuale or 0),
    }
    return {"ok": True, **payload}
