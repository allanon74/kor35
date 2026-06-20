"""
Scansione QR collegati a SottosistemaNave: stato runtime + riparazione via minigioco.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

from personaggi.models import MinigiocoQrConfig, QrCode


def sottosistema_per_qr(qr_code: QrCode):
    from .models import SottosistemaNave

    if qr_code is None or qr_code.vista_id is None:
        return None
    return SottosistemaNave.objects.filter(a_vista_id=qr_code.vista_id).first()


def sessione_attiva_corrente():
    from .views import _sessione_attiva_corrente

    return _sessione_attiva_corrente()


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

    minigioco_riparazione = minigioco_richiesto_per_ripara(qr_code)
    puo_riparare = bool(
        sessione is not None
        and scanner_pg is not None
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

    return {
        "tipo_modello": "pilot_sottosistema",
        "qrcode_id": qr_code.id,
        "messaggio": f"Sottosistema {sottosistema.codice} — {sottosistema.nome}",
        "dati": {
            "sottosistema": SottosistemaNaveSerializer(sottosistema).data,
            "stato": stato_data,
            "sessione_attiva": sessione is not None,
            "sessione_id": str(sessione.pk) if sessione else None,
            "guasto": guasto,
            "in_ripristino": in_ripristino,
            "puo_riparare": puo_riparare,
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
def ripristina_sottosistema_da_qr(
    *,
    qr_code: QrCode,
    personaggio,
    minigioco_session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ripara un sottosistema guasto dopo (eventuale) minigioco.
    """
    from personaggi.qr_minigioco import verifica_accesso_qr_minigioco

    from .engine import get_o_crea_stato_sottosistema
    from .views import _ensure_runtime_subsystems

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
        return {"ok": False, "error": "Il sottosistema è già online."}

    if stato.recovery_at and stato.recovery_at > timezone.now():
        remain = int((stato.recovery_at - timezone.now()).total_seconds())
        return {
            "ok": False,
            "error": f"Ripristino già in corso ({remain}s rimanenti).",
        }

    from .engine import _clamp_livello

    now = timezone.now()
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
        f"Sottosistema {sottosistema.codice} riparato. "
        f"Livello operativo: {stato.livello_attuale}."
    )
    payload["azione"] = "riparato"
    return {"ok": True, **payload}
