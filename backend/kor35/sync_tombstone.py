"""
Tombstone di sincronizzazione: propaga le cancellazioni tra Master e mirror/edge.

Conflitti: deleted_at del tombstone vs updated_at del record (Last-Write-Wins).
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from django.apps import apps
from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_datetime

TOMBSTONE_PAYLOAD_KEY = "sync.tombstone"

_skip_tombstone_on_delete: ContextVar[bool] = ContextVar("skip_tombstone_on_delete", default=False)

EXCLUDED_SYNC_LABELS = frozenset({"personaggi.segnozodiacale", "personaggi.synctombstone"})

_tombstone_table_ready_cache: bool | None = None


def tombstone_table_ready() -> bool:
    """False durante migrazioni che girano prima di 0176_synctombstone."""
    global _tombstone_table_ready_cache
    if _tombstone_table_ready_cache is True:
        return True
    try:
        SyncTombstone = apps.get_model("personaggi", "SyncTombstone")
        from django.db import connection

        ready = SyncTombstone._meta.db_table in connection.introspection.table_names()
        if ready:
            _tombstone_table_ready_cache = True
        return ready
    except Exception:
        return False


def get_sync_model_registry(
    app_labels: tuple[str, ...] = ("personaggi", "gestione_plot", "social", "pilotaggio"),
) -> dict[str, type[models.Model]]:
    registry: dict[str, type[models.Model]] = {}
    for app_label in app_labels:
        app_config = apps.get_app_config(app_label)
        for model in app_config.get_models():
            if model._meta.abstract:
                continue
            if hasattr(model, "sync_id") and hasattr(model, "updated_at"):
                label = model._meta.label_lower
                if label in EXCLUDED_SYNC_LABELS:
                    continue
                registry[label] = model
    return registry


def instance_sync_label(instance: models.Model) -> str | None:
    if instance._meta.label_lower in EXCLUDED_SYNC_LABELS:
        return None
    if not hasattr(instance, "sync_id") or not getattr(instance, "sync_id", None):
        return None
    if not hasattr(instance, "updated_at"):
        return None
    return instance._meta.label_lower


@contextmanager
def suppress_tombstone_on_delete() -> Iterator[None]:
    token = _skip_tombstone_on_delete.set(True)
    try:
        yield
    finally:
        _skip_tombstone_on_delete.reset(token)


def tombstone_on_delete_suppressed() -> bool:
    return _skip_tombstone_on_delete.get()


def record_tombstone_for_instance(instance: models.Model, *, deleted_at=None) -> None:
    """Registra (o aggiorna) tombstone alla cancellazione locale."""
    if not tombstone_table_ready() or tombstone_on_delete_suppressed():
        return
    model_label = instance_sync_label(instance)
    if not model_label:
        return
    SyncTombstone = apps.get_model("personaggi", "SyncTombstone")
    when = deleted_at or timezone.now()
    sync_id = instance.sync_id
    existing = SyncTombstone.objects.filter(model_label=model_label, sync_id=sync_id).first()
    if existing and existing.deleted_at >= when:
        return
    SyncTombstone.objects.update_or_create(
        model_label=model_label,
        sync_id=sync_id,
        defaults={"deleted_at": when},
    )


def clear_tombstone(model_label: str, sync_id) -> None:
    if not tombstone_table_ready():
        return
    SyncTombstone = apps.get_model("personaggi", "SyncTombstone")
    SyncTombstone.objects.filter(model_label=model_label, sync_id=sync_id).delete()


def serialize_tombstone_row(tombstone: models.Model) -> dict[str, Any]:
    return {
        "model_label": tombstone.model_label,
        "sync_id": str(tombstone.sync_id),
        "deleted_at": tombstone.deleted_at.isoformat(),
    }


def build_tombstones_outgoing(since) -> list[dict[str, Any]]:
    if not tombstone_table_ready():
        return []
    SyncTombstone = apps.get_model("personaggi", "SyncTombstone")
    qs = SyncTombstone.objects.all().order_by("deleted_at")
    if since:
        qs = qs.filter(deleted_at__gt=since)
    return [serialize_tombstone_row(row) for row in qs.iterator()]


def tombstone_blocks_record_apply(
    model_label: str, sync_id, remote_updated_at
) -> bool:
    """True se un tombstone locale vince sul payload record in arrivo."""
    if not tombstone_table_ready() or not remote_updated_at or not sync_id:
        return False
    SyncTombstone = apps.get_model("personaggi", "SyncTombstone")
    try:
        sid = uuid.UUID(str(sync_id))
    except (TypeError, ValueError):
        return False
    tombstone = SyncTombstone.objects.filter(model_label=model_label, sync_id=sid).first()
    if tombstone and tombstone.deleted_at >= remote_updated_at:
        return True
    return False


def clear_stale_tombstone_before_record_apply(model_label: str, sync_id, remote_updated_at) -> None:
    """Rimuove tombstone superato da un record più recente (resurrezione LWW)."""
    if not tombstone_table_ready() or not remote_updated_at or not sync_id:
        return
    SyncTombstone = apps.get_model("personaggi", "SyncTombstone")
    try:
        sid = uuid.UUID(str(sync_id))
    except (TypeError, ValueError):
        return
    SyncTombstone.objects.filter(
        model_label=model_label, sync_id=sid, deleted_at__lt=remote_updated_at
    ).delete()


def apply_tombstone_rows(registry: dict[str, type[models.Model]], rows: list[dict[str, Any]]) -> None:
    if not tombstone_table_ready():
        return
    for row in rows:
        apply_one_tombstone_row(registry, row)


def apply_one_tombstone_row(registry: dict[str, type[models.Model]], row: dict[str, Any]) -> None:
    if not tombstone_table_ready():
        return
    model_label = row.get("model_label")
    sync_id_raw = row.get("sync_id")
    remote_deleted_at = parse_datetime(row.get("deleted_at")) if row.get("deleted_at") else None
    if not model_label or not sync_id_raw or not remote_deleted_at:
        return
    try:
        sync_id = uuid.UUID(str(sync_id_raw))
    except (TypeError, ValueError):
        return

    SyncTombstone = apps.get_model("personaggi", "SyncTombstone")
    existing = SyncTombstone.objects.filter(model_label=model_label, sync_id=sync_id).first()
    if existing and existing.deleted_at >= remote_deleted_at:
        remote_deleted_at = existing.deleted_at
    else:
        SyncTombstone.objects.update_or_create(
            model_label=model_label,
            sync_id=sync_id,
            defaults={"deleted_at": remote_deleted_at},
        )

    model = registry.get(model_label)
    if not model:
        return
    local = model.objects.filter(sync_id=sync_id).first()
    if not local:
        return
    local_updated = getattr(local, "updated_at", None)
    if local_updated is not None and remote_deleted_at < local_updated:
        return
    with suppress_tombstone_on_delete():
        local.delete()
