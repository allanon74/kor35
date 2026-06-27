import uuid
from decimal import Decimal
from typing import Any, Literal

from django.contrib.auth import get_user_model
from django.core.files.base import File
from django.db import models
from django.utils import timezone
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


def expand_paginaregolamento_queryset_with_ancestors(model: type[models.Model], qs):
    """
    Per PaginaRegolamento (FK parent -> self), estende il queryset includendo
    tutti gli antenati delle righe già selezionate. Serve ai delta incrementali:
    altrimenti il payload può contenere una pagina figlia senza il record padre.
    """
    pks = set(qs.values_list("pk", flat=True))
    if not pks:
        return qs
    depth_guard = 0
    while depth_guard < 256:
        depth_guard += 1
        parent_ids = set(
            model.objects.filter(pk__in=pks)
            .exclude(parent_id__isnull=True)
            .values_list("parent_id", flat=True)
        )
        new_parents = parent_ids - pks
        if not new_parents:
            break
        pks |= new_parents
    return model.objects.filter(pk__in=pks)


PAGINA_REGOLAMENTO_LABEL = "gestione_plot.paginaregolamento"
QRCODE_MODEL_LABEL = "personaggi.qrcode"
# Modelli il cui PK non è auto-increment e coincide con un identificatore esterno (es. QR stampato).
SYNC_NATURAL_PK_LABELS = frozenset({QRCODE_MODEL_LABEL})
SYNC_MENU_ONLY_KEY = "_sync_menu_only"
PAGINA_REGOLAMENTO_MENU_FIELD_NAMES = frozenset(
    {
        "titolo",
        "slug",
        "parent",
        "ordine",
        "public",
        "visibile_solo_staff",
        "includi_in_pdf",
        "manuali_pdf",
        "pdf_solo_indice",
        "pdf_forza_nuova_pagina",
        "pdf_titolo_capitolo",
    }
)


def touch_sync_updated_at(model: type[models.Model], pk) -> None:
    """
    Dopo patch parziali in sync (menu wiki, campi MTI figlio, M2M) non usare
    remote_updated_at: abbasserebbe il timestamp locale e aprirebbe a revert LWW.
    """
    model.objects.filter(pk=pk).update(updated_at=timezone.now())


def serialize_pagina_regolamento_menu_only(instance: models.Model) -> dict[str, Any]:
    """Antenati wiki nel delta: solo metadati menu, mai contenuto/immagine."""
    data = serialize_for_sync(instance)
    for heavy in ("contenuto", "immagine", "banner_y"):
        data.pop(heavy, None)
    data[SYNC_MENU_ONLY_KEY] = True
    return data


def build_model_sync_records(
    model: type[models.Model],
    model_key: str,
    since,
) -> list[dict[str, Any]]:
    qs = model.objects.all()
    if since:
        qs = qs.filter(updated_at__gt=since)
    if model_key == PAGINA_REGOLAMENTO_LABEL:
        delta_pks = set(qs.values_list("pk", flat=True))
        qs = expand_paginaregolamento_queryset_with_ancestors(model, qs)
        rows: list[dict[str, Any]] = []
        for obj in qs.iterator():
            if obj.pk in delta_pks:
                rows.append(serialize_for_sync(obj))
            else:
                rows.append(serialize_pagina_regolamento_menu_only(obj))
        return rows
    return [serialize_for_sync(obj) for obj in qs.iterator()]


def pagina_regolamento_row_is_menu_only(row: dict[str, Any]) -> bool:
    return bool(row.get(SYNC_MENU_ONLY_KEY))


def natural_primary_key_field(model: type[models.Model]) -> str | None:
    """
    PK non auto-increment da includere nel payload (es. QrCode.id corto stampato sul fisico).

    Modelli con UUIDField come PK usano sync_id come identità tra nodi — non esportare id.
    """
    pk = model._meta.pk
    if pk is None:
        return None
    if isinstance(pk, (models.AutoField, models.BigAutoField, models.SmallAutoField, models.UUIDField)):
        return None
    if isinstance(pk, models.ForeignKey) and getattr(pk.remote_field, "parent_link", False):
        return None
    return pk.name


def _qrcode_fk_models_updating_pk():
    """Modelli con FK/OneToOne verso QrCode.id (CharField PK)."""
    from gestione_plot.models import QuestVista
    from personaggi.models import MinigiocoQrConfig, QrInventarioScanSession, TimerQrCode
    from personaggi.negozio_mercante_models import NegozioMercante

    return (
        (QuestVista, "qr_code_id"),
        (NegozioMercante, "qr_code_id"),
        (TimerQrCode, "qr_code_id"),
        (MinigiocoQrConfig, "qr_code_id"),
        (QrInventarioScanSession, "qr_code_id"),
    )


def realign_natural_primary_key(
    model: type[models.Model],
    local_obj: models.Model,
    want_pk: str,
    pk_name: str,
) -> bool:
    """
    Allinea il PK naturale locale a quello remoto (es. id stampato sul QR fisico).
    Aggiorna prima le FK che puntano al vecchio id.
    """
    from django.db import transaction

    old_pk = getattr(local_obj, pk_name)
    want_pk = str(want_pk).strip()
    if not want_pk or str(old_pk) == want_pk:
        return True

    if model.objects.filter(**{pk_name: want_pk}).exclude(pk=local_obj.pk).exists():
        return False

    with transaction.atomic():
        if model._meta.label_lower == QRCODE_MODEL_LABEL:
            for related_model, field_name in _qrcode_fk_models_updating_pk():
                related_model.objects.filter(**{field_name: old_pk}).update(**{field_name: want_pk})
        model.objects.filter(pk=old_pk).update(**{pk_name: want_pk})
    return True


def apply_natural_pk_precheck(
    model: type[models.Model],
    sync_id,
    row: dict[str, Any],
    update_data: dict[str, Any],
    remote_updated_at,
    local_obj: models.Model | None,
) -> tuple[Literal["noop", "skipped", "applied", "defer"], models.Model | None]:
    """
    Allinea record con PK naturale (QrCode.id): merge per id se sync_id diverge,
    oppure prepara update_data per create con id esplicito.
    """
    pk_name = natural_primary_key_field(model)
    if not pk_name:
        return "noop", local_obj
    want_pk = row.get(pk_name)
    if not want_pk:
        return "noop", local_obj

    if local_obj is not None and getattr(local_obj, pk_name) != want_pk:
        by_pk = model.objects.filter(**{pk_name: want_pk}).first()
        if by_pk is not None and str(by_pk.sync_id) != str(sync_id):
            if (
                by_pk.updated_at
                and remote_updated_at
                and remote_updated_at <= by_pk.updated_at
            ):
                return "skipped", by_pk
            # Record con id fisico corretto ma sync_id locale errato: allinea sync_id e continua apply.
            patch = dict(update_data)
            patch["sync_id"] = sync_id
            if remote_updated_at:
                patch["updated_at"] = remote_updated_at
            model.objects.filter(pk=by_pk.pk).update(**patch)
            if str(local_obj.pk) != str(by_pk.pk):
                model.objects.filter(pk=local_obj.pk).delete()
            return "applied", model.objects.filter(pk=by_pk.pk).first()
        if by_pk is not None and str(by_pk.sync_id) == str(sync_id):
            local_obj = by_pk
        elif not realign_natural_primary_key(model, local_obj, want_pk, pk_name):
            return "defer", local_obj
        else:
            local_obj = model.objects.filter(sync_id=sync_id).first()

    if local_obj is None:
        by_pk = model.objects.filter(**{pk_name: want_pk}).first()
        if by_pk is not None:
            if str(by_pk.sync_id) == str(sync_id):
                return "noop", by_pk
            if (
                by_pk.updated_at
                and remote_updated_at
                and remote_updated_at <= by_pk.updated_at
            ):
                return "skipped", None
            patch = dict(update_data)
            patch["sync_id"] = sync_id
            if remote_updated_at:
                patch["updated_at"] = remote_updated_at
            model.objects.filter(pk=by_pk.pk).update(**patch)
            return "applied", model.objects.filter(pk=by_pk.pk).first()
        update_data[pk_name] = want_pk

    return "noop", local_obj


def serialize_for_sync(instance: models.Model) -> dict[str, Any]:
    """
    Export minimalista di un record con FK espresse tramite sync key.
    """

    data: dict[str, Any] = {}
    model = instance.__class__

    for field in model._meta.concrete_fields:
        if field.name == "id":
            if model._meta.label_lower in SYNC_NATURAL_PK_LABELS:
                data["id"] = getattr(instance, "id", None)
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

    pk_name = natural_primary_key_field(model)
    if pk_name:
        data[pk_name] = getattr(instance, pk_name, None)

    return data


# Modelli MTI per cui NON va forzato il merge dei campi figlio quando il branch LWW
# salta gli scalari: stato di gioco / conflitti intenzionali edge vs master.
_MTICHILD_PATCH_DENYLIST = frozenset(
    {
        "personaggi.personaggio",
    }
)


def try_apply_mti_child_fields_when_skipped(
    local_obj: models.Model,
    row: dict[str, Any],
    resolve_fk,
    *,
    remote_updated_at=None,
    local_updated_at=None,
) -> Literal["defer", "applied", "noop"]:
    """
    Ereditarietà multi-tabella (es. Tecnica -> A_vista, Tabella -> Punteggio): i campi
    sulla tabella figlia possono cambiare senza far avanzare `updated_at` sul genitore,
    oppure restare con lo stesso timestamp del master mentre il payload contiene valori
    diversi. In quel caso il branch LWW (remote_updated_at <= locale) salterebbe tutti
    gli scalari e il mirror resterebbe indietro.

    Allinea i campi *solo sulla tabella del modello concreto* (local_concrete_fields),
    per tutti i modelli MTI tranne quelli in denylist (es. Personaggio).

    Se il record locale è più recente del payload (remote < local), non applicare:
    altrimenti un mirror/edge in ritardo può azzerare modifiche già salvate sul Master
    (es. usa_effetto_temporaneo su Tessitura).
    """
    label = local_obj._meta.label_lower
    if label in _MTICHILD_PATCH_DENYLIST:
        return "noop"
    if not local_obj._meta.parents:
        return "noop"
    if (
        remote_updated_at is not None
        and local_updated_at is not None
        and remote_updated_at < local_updated_at
    ):
        return "noop"

    patch: dict[str, Any] = {}
    for field in local_obj._meta.local_concrete_fields:
        if field.name == "id":
            continue
        if isinstance(field, models.ForeignKey) and getattr(field.remote_field, "parent_link", False):
            continue
        if field.name not in row:
            continue
        value = row[field.name]
        if isinstance(field, models.ForeignKey):
            resolved = resolve_fk(field, value)
            if resolved is None and not field.null and value not in (None, ""):
                return "defer"
            current = getattr(local_obj, field.name)
            cur_pk = getattr(current, "pk", None)
            new_pk = getattr(resolved, "pk", None) if resolved is not None else None
            if cur_pk != new_pk:
                patch[field.name] = resolved
            continue

        current = getattr(local_obj, field.name)
        if json_safe_for_sync(current) != json_safe_for_sync(value):
            patch[field.name] = value

    if not patch:
        return "noop"

    type(local_obj).objects.filter(pk=local_obj.pk).update(**patch)
    touch_sync_updated_at(type(local_obj), local_obj.pk)
    return "applied"


def try_apply_pagina_regolamento_structure_when_skipped(
    local_obj: models.Model, row: dict[str, Any], resolve_fk=None
) -> Literal["defer", "applied", "noop"]:
    """
    Con Last-Write-Wins il record intero può essere saltato pur essendo il payload remoto
    l'unica fonte corretta per l'albero del menu wiki (parent / ordine e metadati menu).

    Allinea i campi menu dal payload quando la riga locale esiste già e il sync avrebbe
    ignorato gli scalari per timestamp. Non tocca contenuto / immagine.
    """
    Model = local_obj.__class__
    patch: dict[str, Any] = {}

    if "titolo" in row and row.get("titolo") != local_obj.titolo:
        patch["titolo"] = row.get("titolo")
    if "slug" in row and row.get("slug") != local_obj.slug:
        patch["slug"] = row.get("slug")
    if "public" in row and bool(row.get("public")) != bool(local_obj.public):
        patch["public"] = bool(row.get("public"))
    if "visibile_solo_staff" in row and bool(row.get("visibile_solo_staff")) != bool(
        local_obj.visibile_solo_staff
    ):
        patch["visibile_solo_staff"] = bool(row.get("visibile_solo_staff"))

    raw_parent = row.get("parent")
    resolved_parent = None
    if raw_parent not in (None, ""):
        if resolve_fk is not None:
            parent_field = Model._meta.get_field("parent")
            resolved_parent = resolve_fk(parent_field, raw_parent)
        else:
            resolved_parent = Model.objects.filter(sync_id=raw_parent).first()
        if resolved_parent is None:
            return "defer"
    target_parent_id = resolved_parent.pk if resolved_parent is not None else None
    if local_obj.parent_id != target_parent_id:
        patch["parent"] = resolved_parent

    if "ordine" in row:
        try:
            ordine = int(row.get("ordine"))
        except (TypeError, ValueError):
            ordine = local_obj.ordine
        if local_obj.ordine != ordine:
            patch["ordine"] = ordine

    if not patch:
        return "noop"

    Model.objects.filter(pk=local_obj.pk).update(**patch)
    touch_sync_updated_at(Model, local_obj.pk)
    return "applied"


def pagina_regolamento_sync_field_allowed(field_name: str, row: dict[str, Any]) -> bool:
    if not pagina_regolamento_row_is_menu_only(row):
        return True
    return field_name in PAGINA_REGOLAMENTO_MENU_FIELD_NAMES
