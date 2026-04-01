"""
Adapter write-through: aggiornano TimerRuntime insieme ai modelli legacy.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.utils import timezone


def _parse_dt_iso(value):
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except Exception:
            return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt

from .models import (
    TIMER_RENDER_CRAFTING_TAB,
    TIMER_RENDER_GAME_PANEL,
    TIMER_RENDER_GLOBAL_OVERLAY,
    TIMER_SCOPE_ALL,
    TIMER_SOURCE_COMA,
    TIMER_SOURCE_CREAZIONE_CONSUMABILE,
    TIMER_SOURCE_FORGIATURA,
    TIMER_SOURCE_QR_TIPOLOGIA,
    TIMER_SOURCE_RECUPERO_RISORSA,
    TIMER_SOURCE_RIANIMAZIONE,
    TIMER_STATUS_ACTIVE,
    TIMER_STATUS_CANCELLED,
    TIMER_STATUS_DONE,
    TIMER_STATUS_PAUSED,
    CreazioneConsumabileInCorso,
    ForgiaturaInCorso,
    RecuperoRisorsaAttivo,
    StatoTimerAttivo,
    TimerRuntime,
    TipologiaTimer,
)
from .timers import TimerService


def _tipologia_source_id(tipologia: TipologiaTimer) -> str:
    sid = getattr(tipologia, "sync_id", None)
    if sid:
        return str(sid)
    return f"id:{tipologia.pk}"


def tipologia_timer_source_id(tipologia: TipologiaTimer) -> str:
    """Pubblico: chiave sorgente per dedup legacy/unified."""
    return _tipologia_source_id(tipologia)


def sync_qr_global_timer_from_stato(stato: StatoTimerAttivo, tipologia: TipologiaTimer) -> TimerRuntime:
    """Mirror timer QR globale (un record StatoTimerAttivo per tipologia)."""
    source_id = _tipologia_source_id(tipologia)
    defaults = {
        "personaggio": None,
        "end_at": stato.data_fine,
        "status": TIMER_STATUS_ACTIVE,
        "render_slot": TIMER_RENDER_GLOBAL_OVERLAY,
        "scope_kind": TIMER_SCOPE_ALL,
        "scope_payload": {
            "alert_suono": tipologia.alert_suono,
            "notifica_push": tipologia.notifica_push,
            "messaggio_in_app": tipologia.messaggio_in_app,
        },
        "label": tipologia.nome,
        "description": "",
        "action_key": "noop",
        "action_payload": {
            "tipologia_sync_id": source_id,
            "stato_timer_id": stato.id,
        },
        "is_master_timer": True,
        "started_at": stato.updated_at or timezone.now(),
        "action_executed_at": None,
    }
    tr, _created = TimerRuntime.objects.update_or_create(
        source_kind=TIMER_SOURCE_QR_TIPOLOGIA,
        source_id=source_id,
        defaults=defaults,
    )
    return tr


def sync_recupero_risorsa_timer(rec: RecuperoRisorsaAttivo) -> Optional[TimerRuntime]:
    """Mirror tick recupero pool sul personaggio owner."""
    if not rec.is_active:
        TimerRuntime.objects.filter(
            source_kind=TIMER_SOURCE_RECUPERO_RISORSA,
            source_id=str(rec.sync_id),
        ).update(status=TIMER_STATUS_DONE, updated_at=timezone.now())
        return None

    source_id = str(rec.sync_id)
    label = f"Recupero {rec.statistica_sigla}"
    end_at = rec.next_tick_at
    payload = {
        "recupero_sync_id": str(rec.sync_id),
        "statistica_sigla": rec.statistica_sigla,
        "personaggio_id": rec.personaggio_id,
    }
    tr, _ = TimerRuntime.objects.update_or_create(
        source_kind=TIMER_SOURCE_RECUPERO_RISORSA,
        source_id=source_id,
        defaults={
            "personaggio": rec.personaggio,
            "end_at": end_at,
            "status": TIMER_STATUS_PAUSED if rec.pause_started_at else TIMER_STATUS_ACTIVE,
            "render_slot": TIMER_RENDER_GAME_PANEL,
            "scope_kind": TIMER_SCOPE_ALL,
            "label": label,
            "action_key": "recupero_risorsa_tick",
            "action_payload": payload,
            "is_master_timer": False,
            "started_at": rec.started_at,
            "pause_started_at": rec.pause_started_at,
            "action_executed_at": None,
        },
    )
    return tr


def sync_coma_and_rianimazione_timers(personaggio) -> None:
    """
    Legge impostazioni_ui e crea/aggiorna TimerRuntime per coma e rianimazione.
    Chiamare dopo _sync_coma_state o quando cambia l'UI.
    """
    ui = dict(personaggio.impostazioni_ui or {})
    coma = dict(ui.get("coma_state") or {})
    rianim = dict(ui.get("rianimazione_state") or {})

    def _parse_iso(key, d):
        return _parse_dt_iso(d.get(key))

    # Coma
    if coma and str(coma.get("status") or "").lower() not in {"idle", "resolved", "dead"}:
        end_at = _parse_iso("end_at", coma)
        if end_at and not coma.get("is_paused"):
            TimerService.start_or_update_mirror(
                source_kind=TIMER_SOURCE_COMA,
                source_id=f"pg{personaggio.pk}",
                personaggio=personaggio,
                end_at=end_at,
                label="Coma",
                render_slot=TIMER_RENDER_GAME_PANEL,
                action_key="sync_coma_state",
                action_payload={"personaggio_id": personaggio.pk},
                is_master_timer=False,
            )
        else:
            _cancel_kind(TIMER_SOURCE_COMA, f"pg{personaggio.pk}")
    else:
        _cancel_kind(TIMER_SOURCE_COMA, f"pg{personaggio.pk}")

    # Rianimazione
    if rianim and str(rianim.get("status") or "").lower() == "counting":
        end_at = _parse_iso("end_at", rianim)
        if end_at:
            TimerService.start_or_update_mirror(
                source_kind=TIMER_SOURCE_RIANIMAZIONE,
                source_id=f"pg{personaggio.pk}",
                personaggio=personaggio,
                end_at=end_at,
                label="Rianimazione",
                render_slot=TIMER_RENDER_GAME_PANEL,
                action_key="sync_coma_state",
                action_payload={"personaggio_id": personaggio.pk},
                is_master_timer=False,
            )
        else:
            _cancel_kind(TIMER_SOURCE_RIANIMAZIONE, f"pg{personaggio.pk}")
    else:
        _cancel_kind(TIMER_SOURCE_RIANIMAZIONE, f"pg{personaggio.pk}")


def _cancel_kind(kind: str, source_id: str) -> None:
    TimerRuntime.objects.filter(
        source_kind=kind,
        source_id=source_id,
        status__in=[TIMER_STATUS_ACTIVE, TIMER_STATUS_PAUSED],
    ).update(status=TIMER_STATUS_CANCELLED)


def sync_forgiatura_timer(f: ForgiaturaInCorso) -> TimerRuntime:
    source_id = str(f.sync_id)
    label = f"Forgiatura: {f.infusione.nome}"
    return TimerService.start_or_update_mirror(
        source_kind=TIMER_SOURCE_FORGIATURA,
        source_id=source_id,
        personaggio=f.personaggio,
        end_at=f.data_fine_prevista,
        label=label,
        render_slot=TIMER_RENDER_CRAFTING_TAB,
        action_key="forge_complete_reminder",
        action_payload={"forgiatura_sync_id": str(f.sync_id)},
        is_master_timer=False,
    )


def sync_creazione_consumabile_timer(cc: CreazioneConsumabileInCorso) -> TimerRuntime:
    source_id = str(cc.sync_id)
    label = f"Alchimia: {cc.tessitura.nome}"
    return TimerService.start_or_update_mirror(
        source_kind=TIMER_SOURCE_CREAZIONE_CONSUMABILE,
        source_id=source_id,
        personaggio=cc.personaggio,
        end_at=cc.data_fine_creazione,
        label=label,
        render_slot=TIMER_RENDER_CRAFTING_TAB,
        action_key="consumabile_ready_reminder",
        action_payload={"creazione_sync_id": str(cc.sync_id)},
        is_master_timer=False,
    )


def cancel_timer_by_source(kind: str, source_id: str) -> None:
    _cancel_kind(kind, source_id)
