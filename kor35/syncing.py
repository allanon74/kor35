import uuid
from typing import Any

from django.contrib.auth import get_user_model
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
        if hasattr(value, "isoformat"):
            data[field.name] = value.isoformat()
        else:
            data[field.name] = value

    return data
