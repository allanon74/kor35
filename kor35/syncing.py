import uuid
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.core.files.base import File
from django.db import models
from rest_framework import serializers


User = get_user_model()


class SyncableModel(models.Model):
    """
    Base astratta per record sincronizzabili tra nodi.
    """

    sync_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SyncForeignKeyField(serializers.RelatedField):
    """
    Espone FK come chiave funzionale per la sincronizzazione:
    - User -> email (fallback username)
    - altri modelli -> sync_id
    """

    def to_representation(self, value):
        if value is None:
            return None
        if isinstance(value, User):
            return value.email or value.username
        if hasattr(value, "sync_id"):
            return str(value.sync_id)
        return None


class SyncModelSerializer(serializers.ModelSerializer):
    """
    Serializer DRF per export/import sync-safe.
    """

    def build_relational_field(self, field_name, relation_info):
        kwargs = {
            "queryset": relation_info.related_model.objects.all(),
            "required": not relation_info.model_field.null,
            "allow_null": relation_info.model_field.null,
        }
        return SyncForeignKeyField, kwargs


def json_safe_for_sync(value: Any) -> Any:
    """
    Valori compatibili con json.dumps (replica -> Master e risposta Master).
    Gestisce UUID, Decimal, datetime, file upload, JSONField annidati.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): json_safe_for_sync(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe_for_sync(v) for v in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, memoryview)):
        return None
    if isinstance(value, File):
        try:
            name = getattr(value, "name", None)
            return name or None
        except Exception:
            return None
    if isinstance(value, models.Model):
        if hasattr(value, "sync_id"):
            return str(value.sync_id)
        return value.pk
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def serialize_for_sync(instance: models.Model) -> dict[str, Any]:
    """
    Export minimalista di un record con FK espresse tramite sync key.
    """

    data: dict[str, Any] = {}
    model = instance.__class__

    for field in model._meta.concrete_fields:
        if field.name == "id":
            continue

        if isinstance(field, models.ForeignKey):
            related_obj = getattr(instance, field.name, None)
            if related_obj is None:
                data[field.name] = None
            elif isinstance(related_obj, User):
                data[field.name] = related_obj.email or related_obj.username
            elif hasattr(related_obj, "sync_id"):
                data[field.name] = str(related_obj.sync_id)
            else:
                data[field.name] = None
            continue

        value = getattr(instance, field.name, None)
        data[field.name] = json_safe_for_sync(value)

    # Include anche le relazioni M2M espresse come chiavi di sync.
    for m2m_field in model._meta.many_to_many:
        if m2m_field.auto_created:
            continue
        related_items = []
        for related_obj in getattr(instance, m2m_field.name).all():
            if isinstance(related_obj, User):
                related_items.append(related_obj.email or related_obj.username)
            elif hasattr(related_obj, "sync_id"):
                related_items.append(str(related_obj.sync_id))
        data[m2m_field.name] = related_items

    return data
