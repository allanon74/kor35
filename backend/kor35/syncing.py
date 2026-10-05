import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Iterator, Literal

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.db import IntegrityError, models, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
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


def coerce_sync_scalar_value(field: models.Field, value: Any) -> Any:
    """
    Il payload JSON serializza datetime/decimal/UUID come stringhe.
    Senza conversione, `Model.save()` che fa aritmetica su DateTimeField
    (es. StaffCompito.scadenza - timedelta) alza TypeError e il record resta defer.
    """
    if isinstance(field, (models.ForeignKey, models.OneToOneField, models.FileField)):
        return value
    if value is None:
        return None
    if value == "" and isinstance(
        field,
        (models.DateTimeField, models.DateField, models.TimeField, models.DecimalField),
    ):
        return None
    if not isinstance(
        field,
        (
            models.DateTimeField,
            models.DateField,
            models.TimeField,
            models.DecimalField,
            models.UUIDField,
        ),
    ):
        return value
    try:
        return field.to_python(value)
    except (TypeError, ValueError, ValidationError):
        if isinstance(field, models.DateTimeField) and isinstance(value, str):
            parsed = parse_datetime(value)
            if parsed is not None:
                if timezone.is_naive(parsed) and timezone.is_aware(timezone.now()):
                    return timezone.make_aware(parsed, timezone.get_current_timezone())
                return parsed
        return value


def restore_auto_now_add_from_sync(
    model: type[models.Model], obj: models.Model | None, update_data: dict[str, Any]
) -> None:
    """
    `auto_now_add` ignora il valore passato a `update_or_create` in creazione.
    Senza questo, `created_at` diventa l'istante dell'apply e i countdown
    (deadline - created) sugli eventi di pilotaggio risultano enormi o negativi.
    """
    if obj is None or not update_data:
        return
    patch: dict[str, Any] = {}
    for field in model._meta.concrete_fields:
        if not getattr(field, "auto_now_add", False):
            continue
        if field.name not in update_data:
            continue
        val = update_data[field.name]
        if val is None:
            continue
        patch[field.name] = val
    if patch:
        model.objects.filter(pk=obj.pk).update(**patch)


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
        "visibile_solo_autenticati",
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


# Stesso nome su due nodi (sync_id diversi) = lo stesso evento o la stessa rotta.
_PILOT_CATALOG_NATURAL_KEYS = {
    "pilotaggio.eventonave": ("nome",),
    "pilotaggio.percorsovolo": ("partenza", "arrivo"),
}


def find_pilot_catalog_counterpart(model: type[models.Model], sync_id, row: dict[str, Any]):
    """
    Evento o rotta già presente sull'altro nodo con un altro sync_id.
    Il confronto è sul nome (eventi) o sulla coppia partenza/arrivo (rotte).
    """
    fields = _PILOT_CATALOG_NATURAL_KEYS.get(model._meta.label_lower)
    if not fields or not sync_id:
        return None
    lookup = {}
    for fname in fields:
        raw = row.get(fname)
        text = str(raw or "").strip()
        if not text:
            return None
        lookup[f"{fname}__iexact"] = text
    return (
        model.objects.filter(**lookup)
        .exclude(sync_id=sync_id)
        .order_by("-updated_at")
        .first()
    )


def lww_update_existing(model, existing, update_data, remote_sync_id, remote_updated_at) -> str:
    """
    Conflitto sulla stessa riga logica. Vince `updated_at` più recente.

    Se vince il locale, i campi restano i suoi. Il sync_id remoto viene adottato
    quando è sicuro, e `updated_at` viene ripubblicato così il vincitore torna
    nel delta verso l'altro nodo. Senza timestamp remoto il payload si applica.
    """
    patch = dict(update_data or {})
    patch.pop("updated_at", None)
    patch.pop("sync_id", None)
    patch.pop("id", None)
    for field in model._meta.concrete_fields:
        if isinstance(field, models.ForeignKey) and getattr(field.remote_field, "parent_link", False):
            patch.pop(field.name, None)

    local_wins = bool(
        remote_updated_at
        and existing.updated_at
        and remote_updated_at <= existing.updated_at
    )
    if local_wins:
        if (
            remote_sync_id
            and str(existing.sync_id) != str(remote_sync_id)
            and can_align_sync_id_on_merge(model)
        ):
            try:
                with transaction.atomic():
                    model.objects.filter(pk=existing.pk).update(sync_id=remote_sync_id)
            except IntegrityError:
                pass
        touch_sync_updated_at(model, existing.pk)
        return "skipped"

    if can_align_sync_id_on_merge(model) and remote_sync_id:
        patch["sync_id"] = remote_sync_id
    if remote_updated_at is not None:
        patch["updated_at"] = remote_updated_at
    try:
        with transaction.atomic():
            model.objects.filter(pk=existing.pk).update(**patch)
    except IntegrityError:
        if remote_updated_at is not None:
            model.objects.filter(pk=existing.pk).update(updated_at=remote_updated_at)
    return "applied"


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


def can_align_sync_id_on_merge(model: type[models.Model]) -> bool:
    """
    Dice se, in un merge per chiave naturale, la riga locale può adottare il sync_id remoto.

    Con l'ereditarietà multi-tabella (Tessitura → A_vista, Tier → Tabella) il campo
    sync_id vive sulla tabella genitore, che ha una propria identità di sync: riscriverlo
    dal payload del figlio corromperebbe il record padre e può violare l'unique.
    """
    return any(field.name == "sync_id" for field in model._meta.local_concrete_fields)


def _iter_qrcode_referencing_fk_fields() -> Iterator[tuple[type[models.Model], str]]:
    """Modelli con FK/OneToOne verso QrCode.id (codice corto stampato)."""
    QrCode = apps.get_model("personaggi", "QrCode")
    for rel in QrCode._meta.related_objects:
        field = rel.field
        if isinstance(field, (models.ForeignKey, models.OneToOneField)):
            yield rel.related_model, field.name


def rekey_qrcode_primary_key(
    *,
    old_id: str,
    new_id: str,
    sync_id,
    update_data: dict[str, Any] | None = None,
    remote_updated_at=None,
) -> models.Model:
    """
    Allinea l'id corto stampato sul QR fisico quando il mirror ha lo stesso sync_id
    ma PK locale diversa (regressione sync pre-fix natural PK).
    """
    from kor35.sync_tombstone import suppress_tombstone_on_delete

    QrCode = apps.get_model("personaggi", "QrCode")
    patch = dict(update_data or {})

    with transaction.atomic():
        old = QrCode.objects.select_for_update().get(pk=old_id)
        if str(old.sync_id) != str(sync_id):
            raise IntegrityError("sync_id non corrisponde durante rekey QrCode")

        if QrCode.objects.filter(pk=new_id).exists():
            raise IntegrityError(f"QrCode id={new_id} già esistente")

        saved_vista_id = old.vista_id
        create_data = {f.name: getattr(old, f.name) for f in QrCode._meta.concrete_fields}
        create_data.update(patch)

        # Libera UNIQUE su sync_id e vista_id (OneToOne) prima di inserire la riga con id master.
        temp_sync_id = uuid.uuid4()
        QrCode.objects.filter(pk=old_id).update(sync_id=temp_sync_id, vista_id=None)

        create_data["id"] = new_id
        create_data["sync_id"] = sync_id
        if remote_updated_at:
            create_data["updated_at"] = remote_updated_at
        if "vista" not in patch:
            create_data["vista_id"] = saved_vista_id

        qr = QrCode(**create_data)
        qr.save()

        for related_model, field_name in _iter_qrcode_referencing_fk_fields():
            related_model.objects.filter(**{field_name: old_id}).update(**{field_name: new_id})

        with suppress_tombstone_on_delete():
            QrCode.objects.filter(pk=old_id).delete()

        return qr


def realign_natural_primary_key(
    model: type[models.Model],
    local_obj: models.Model,
    want_pk: str,
    pk_name: str,
    *,
    sync_id=None,
    update_data: dict[str, Any] | None = None,
    remote_updated_at=None,
) -> bool:
    """
    Allinea il PK naturale locale a quello remoto (es. id stampato sul QR fisico).
    Per QrCode usa rekey (create+migra FK+delete) per rispettare UNIQUE su sync_id.
    """
    old_pk = getattr(local_obj, pk_name)
    want_pk = str(want_pk).strip()
    if not want_pk or str(old_pk) == want_pk:
        return True

    if model.objects.filter(**{pk_name: want_pk}).exclude(pk=local_obj.pk).exists():
        return False

    if model._meta.label_lower == QRCODE_MODEL_LABEL and sync_id is not None:
        try:
            rekey_qrcode_primary_key(
                old_id=str(old_pk),
                new_id=want_pk,
                sync_id=sync_id,
                update_data=update_data,
                remote_updated_at=remote_updated_at,
            )
            return True
        except IntegrityError:
            return False

    with transaction.atomic():
        model.objects.filter(pk=old_pk).update(**{pk_name: want_pk})
    return True


def ensure_qrcode_natural_pk_aligned(
    sync_id,
    row: dict[str, Any],
    local_obj: models.Model | None,
    update_data: dict[str, Any] | None = None,
    remote_updated_at=None,
) -> models.Model | None:
    """
    Se sync_id coincide ma l'id stampato differisce, riallinea subito la PK.
    L'id fisico sul QR ha priorità su LWW scalare (altrimenti skip_scalars blocca il fix).
    """
    if local_obj is None:
        return local_obj
    want_id = row.get("id")
    if not want_id or local_obj.pk == want_id:
        return local_obj

    QrCode = apps.get_model("personaggi", "QrCode")
    if QrCode.objects.filter(pk=want_id).exclude(sync_id=sync_id).exists():
        return local_obj
    if QrCode.objects.filter(pk=want_id).exists():
        return local_obj

    try:
        return rekey_qrcode_primary_key(
            old_id=local_obj.pk,
            new_id=want_id,
            sync_id=sync_id,
            update_data=update_data,
            remote_updated_at=remote_updated_at,
        )
    except IntegrityError:
        return local_obj


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
        elif not realign_natural_primary_key(
            model,
            local_obj,
            want_pk,
            pk_name,
            sync_id=sync_id,
            update_data=update_data,
            remote_updated_at=remote_updated_at,
        ):
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

# Eccezione alla denylist / al skip per payload stale: campi staff/catalogo sulla
# tabella figlia che devono convergere anche se un touch locale (M2M, inventario,
# login) ha reso `updated_at` più recente. Prestigio e punti allineamento usano
# max-wins così un premio assegnato sul master non viene perso, e un premio
# assegnato sull'edge durante l'evento non viene ribassato da un pull stale.
_MTI_CHILD_ALWAYS_SYNC_FIELDS = {
    "personaggi.personaggio": frozenset(
        {
            "prestigio",
            "punti_luminosi",
            "punti_oscuri",
            "punti_grigi",
        }
    ),
    "personaggi.carriera": frozenset(
        {
            "fattore_task_crediti",
            "fattore_task_prestigio",
            "sottoscrive_contratti",
            "slot_contratto_base",
            "bonus_crediti_evento",
        }
    ),
}

_MTI_CHILD_MAX_WINS_FIELDS = frozenset(
    {
        "prestigio",
        "punti_luminosi",
        "punti_oscuri",
        "punti_grigi",
    }
)


def _mti_remote_numeric_wins(remote_value: Any, local_value: Any) -> bool:
    try:
        remote_n = Decimal(str(remote_value))
        local_n = Decimal(str(local_value if local_value is not None else 0))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return remote_n > local_n


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

    Eccezione: `_MTI_CHILD_ALWAYS_SYNC_FIELDS` (prestigio, fattori KORP). Senza di essa
    un touch locale sul Personaggio/Carriera lascia il mirror con timestamp più nuovo
    e valori staff/catalogo vecchi; la denylist Personaggio bloccherebbe anche il
    caso di timestamp uguale. Prestigio/punti: solo se il remoto è maggiore.
    """
    label = local_obj._meta.label_lower
    always_fields = _MTI_CHILD_ALWAYS_SYNC_FIELDS.get(label, frozenset())
    denied = label in _MTICHILD_PATCH_DENYLIST
    stale_remote = (
        remote_updated_at is not None
        and local_updated_at is not None
        and remote_updated_at < local_updated_at
    )
    if not local_obj._meta.parents:
        return "noop"
    if (denied or stale_remote) and not always_fields:
        return "noop"

    patch: dict[str, Any] = {}
    for field in local_obj._meta.local_concrete_fields:
        if field.name == "id":
            continue
        if isinstance(field, models.ForeignKey) and getattr(field.remote_field, "parent_link", False):
            continue
        if field.name not in row:
            continue
        if (denied or stale_remote) and field.name not in always_fields:
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

        value = coerce_sync_scalar_value(field, value)
        current = getattr(local_obj, field.name)
        if field.name in _MTI_CHILD_MAX_WINS_FIELDS and (denied or stale_remote):
            if not _mti_remote_numeric_wins(value, current):
                continue
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
    if "visibile_solo_autenticati" in row and bool(row.get("visibile_solo_autenticati")) != bool(
        getattr(local_obj, "visibile_solo_autenticati", False)
    ):
        patch["visibile_solo_autenticati"] = bool(row.get("visibile_solo_autenticati"))

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
