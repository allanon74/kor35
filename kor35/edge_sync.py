from __future__ import annotations

import logging
from dataclasses import dataclass

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.db import IntegrityError, transaction
from django.db.models import ForeignKey
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from kor35.syncing import serialize_for_sync
from personaggi.models import AuthGroupSyncState, AuthUserSyncState

logger = logging.getLogger(__name__)


class HasEdgeSyncToken(permissions.BasePermission):
    """
    Accetta solo Authorization: EdgeToken <token>.
    """

    def has_permission(self, request, view):
        expected = (getattr(settings, "EDGE_SYNC_TOKEN", "") or "").strip()
        if not expected:
            return False

        auth_header = (request.headers.get("Authorization", "") or "").strip()
        if not auth_header.startswith("EdgeToken "):
            return False

        provided = auth_header.replace("EdgeToken ", "", 1).strip()
        return provided == expected


@dataclass
class PendingRecord:
    model_key: str
    model: type
    payload: dict


class EdgeSyncView(APIView):
    permission_classes = [HasEdgeSyncToken]
    authentication_classes = []

    def post(self, request):
        last_sync_raw = request.data.get("last_sync_timestamp") or request.data.get("since")
        last_sync_timestamp = parse_datetime(last_sync_raw) if last_sync_raw else None
        incoming_records = request.data.get("records", {}) or {}

        try:
            with transaction.atomic():
                self._apply_users(incoming_records.get("auth.user", []))
                self._apply_groups(incoming_records.get("auth.group", []))
                self._apply_sync_models(incoming_records)

            outgoing = self._build_outgoing(last_sync_timestamp)
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("Edge sync failed")
            verbose = getattr(settings, "EDGE_SYNC_VERBOSE_ERRORS", True)
            detail = str(exc) if (verbose or settings.DEBUG) else "Edge sync error"
            payload = {"detail": detail, "error_type": exc.__class__.__name__}
            if isinstance(exc, IntegrityError) and getattr(exc.__cause__, "pgcode", None):
                payload["pgcode"] = exc.__cause__.pgcode
            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "status": "ok",
                "server_timestamp": timezone.now().isoformat(),
                "records": outgoing,
            },
            status=status.HTTP_200_OK,
        )

    def _sync_model_registry(self):
        registry = {}
        for app_label in ("personaggi", "gestione_plot"):
            app_config = apps.get_app_config(app_label)
            for model in app_config.get_models():
                if model._meta.abstract:
                    continue
                if hasattr(model, "sync_id") and hasattr(model, "updated_at"):
                    registry[model._meta.label_lower] = model
        return registry

    def _build_outgoing(self, last_sync_timestamp):
        registry = self._sync_model_registry()
        payload = {}

        for key, model in registry.items():
            qs = model.objects.all()
            if last_sync_timestamp:
                qs = qs.filter(updated_at__gt=last_sync_timestamp)
            payload[key] = [serialize_for_sync(obj) for obj in qs.iterator()]

        payload["auth.user"] = self._serialize_users(last_sync_timestamp)
        payload["auth.group"] = self._serialize_groups(last_sync_timestamp)
        return payload

    def _serialize_users(self, last_sync_timestamp):
        # Solo utenti con riga AuthUserSyncState (evita OneToOne mancante -> 500).
        qs = User.objects.filter(pk__in=AuthUserSyncState.objects.values_list("user_id", flat=True))
        if last_sync_timestamp:
            qs = qs.filter(sync_state__updated_at__gt=last_sync_timestamp)
        qs = qs.select_related("sync_state")
        rows = []
        for u in qs.iterator():
            try:
                st = u.sync_state
            except ObjectDoesNotExist:
                continue
            if st is None:
                continue
            rows.append(
                {
                    "username": u.username,
                    "email": u.email,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "is_active": u.is_active,
                    "is_staff": u.is_staff,
                    "is_superuser": u.is_superuser,
                    "password": u.password,
                    "updated_at": st.updated_at.isoformat(),
                }
            )
        return rows

    def _serialize_groups(self, last_sync_timestamp):
        qs = Group.objects.filter(pk__in=AuthGroupSyncState.objects.values_list("group_id", flat=True))
        if last_sync_timestamp:
            qs = qs.filter(sync_state__updated_at__gt=last_sync_timestamp)
        qs = qs.select_related("sync_state")
        rows = []
        for group in qs.iterator():
            try:
                st = group.sync_state
            except ObjectDoesNotExist:
                continue
            if st is None:
                continue
            rows.append(
                {
                    "name": group.name,
                    "permissions": list(group.permissions.values_list("codename", flat=True)),
                    "updated_at": st.updated_at.isoformat(),
                }
            )
        return rows

    def _apply_users(self, rows):
        for row in rows:
            username = row.get("username")
            if not username:
                continue
            remote_updated_at = parse_datetime(row.get("updated_at")) if row.get("updated_at") else None
            local = User.objects.filter(username=username).select_related("sync_state").first()
            local_updated_at = getattr(getattr(local, "sync_state", None), "updated_at", None)
            if local and remote_updated_at and local_updated_at and remote_updated_at <= local_updated_at:
                continue

            defaults = {
                "email": row.get("email", ""),
                "first_name": row.get("first_name", ""),
                "last_name": row.get("last_name", ""),
                "is_active": row.get("is_active", True),
                "is_staff": row.get("is_staff", False),
                "is_superuser": row.get("is_superuser", False),
            }
            # Sincronizza anche l'hash password Django tra Master e Replica.
            if row.get("password"):
                defaults["password"] = row.get("password")

            user, _ = User.objects.update_or_create(
                username=username,
                defaults=defaults,
            )
            state, _ = AuthUserSyncState.objects.get_or_create(user=user)
            if remote_updated_at:
                AuthUserSyncState.objects.filter(pk=state.pk).update(updated_at=remote_updated_at)

    def _apply_groups(self, rows):
        for row in rows:
            name = row.get("name")
            if not name:
                continue
            remote_updated_at = parse_datetime(row.get("updated_at")) if row.get("updated_at") else None
            local = Group.objects.filter(name=name).select_related("sync_state").first()
            local_updated_at = getattr(getattr(local, "sync_state", None), "updated_at", None)
            if local and remote_updated_at and local_updated_at and remote_updated_at <= local_updated_at:
                continue

            group, _ = Group.objects.update_or_create(name=name)
            codenames = row.get("permissions", []) or []
            perms = Permission.objects.filter(codename__in=codenames)
            group.permissions.set(perms)
            state, _ = AuthGroupSyncState.objects.get_or_create(group=group)
            if remote_updated_at:
                AuthGroupSyncState.objects.filter(pk=state.pk).update(updated_at=remote_updated_at)

    def _apply_sync_models(self, incoming_records):
        registry = self._sync_model_registry()
        pending = []
        for model_key, rows in incoming_records.items():
            if model_key in {"auth.user", "auth.group"}:
                continue
            model = registry.get(model_key)
            if not model:
                continue
            for row in rows:
                pending.append(PendingRecord(model_key=model_key, model=model, payload=row))

        max_rounds = max(len(pending), 1)
        for _ in range(max_rounds):
            if not pending:
                return
            still_pending = []
            progressed = 0
            for item in pending:
                result = self._try_apply_one(item.model, item.payload)
                if result == "applied" or result == "skipped":
                    progressed += 1
                else:
                    still_pending.append(item)
            pending = still_pending
            if progressed == 0:
                break

        if pending:
            first = pending[0]
            raise ValidationError(
                f"Sync FK unresolved: model={first.model_key} sync_id={first.payload.get('sync_id')}"
            )

    def _try_apply_one(self, model, row):
        sync_id = row.get("sync_id")
        if not sync_id:
            return "skipped"

        remote_updated_at = parse_datetime(row.get("updated_at")) if row.get("updated_at") else None
        local = model.objects.filter(sync_id=sync_id).first()
        if local and remote_updated_at and local.updated_at and remote_updated_at <= local.updated_at:
            return "skipped"

        update_data = {}
        for field in model._meta.concrete_fields:
            if field.name in {"id", "sync_id", "updated_at"}:
                continue
            # Multi-table inheritance: valorizza automaticamente parent_link
            # (es. tabella_ptr) cercando il parent con lo stesso sync_id.
            if isinstance(field, ForeignKey) and getattr(field.remote_field, "parent_link", False):
                parent_obj = field.related_model.objects.filter(sync_id=sync_id).first()
                if parent_obj is None:
                    return "defer"
                update_data[field.name] = parent_obj
                continue
            if field.name not in row:
                continue

            value = row.get(field.name)
            if isinstance(field, ForeignKey):
                resolved = self._resolve_fk_value(field, value)
                if resolved is None and not field.null and value not in (None, ""):
                    return "defer"
                update_data[field.name] = resolved
            else:
                update_data[field.name] = value

        m2m_updates = {}
        for m2m_field in model._meta.many_to_many:
            if m2m_field.auto_created:
                continue
            if m2m_field.name not in row:
                continue
            raw_values = row.get(m2m_field.name) or []
            resolved_values = self._resolve_m2m_values(m2m_field, raw_values)
            m2m_updates[m2m_field.name] = resolved_values

        try:
            obj, _ = model.objects.update_or_create(sync_id=sync_id, defaults=update_data)
        except IntegrityError:
            if self._merge_by_natural_unique_key(
                model, sync_id, row, update_data, remote_updated_at
            ):
                obj = model.objects.filter(sync_id=sync_id).first()
                if not obj:
                    raise
            else:
                raise

        for field_name, related_list in m2m_updates.items():
            getattr(obj, field_name).set(related_list)

        if remote_updated_at and obj is not None:
            model.objects.filter(pk=obj.pk).update(updated_at=remote_updated_at)
        return "applied"

    def _merge_by_natural_unique_key(self, model, sync_id, row, update_data, remote_updated_at):
        """
        Replica ha sync_id nuovo ma un campo UNIQUE (es. nome) coincide col Master.
        Allinea la riga esistente al sync_id della replica e applica LWW sui campi.
        """
        try:
            from cms.models import CMSPlugin
        except ImportError:
            CMSPlugin = None
        if CMSPlugin and issubclass(model, CMSPlugin):
            return False

        for field in model._meta.concrete_fields:
            if field.name in ("id", "sync_id"):
                continue
            if not getattr(field, "unique", False):
                continue
            if isinstance(field, ForeignKey):
                continue
            val = row.get(field.name)
            if val in (None, ""):
                continue
            existing = (
                model.objects.filter(**{field.name: val})
                .exclude(sync_id=sync_id)
                .first()
            )
            if not existing:
                continue
            if model.objects.filter(sync_id=sync_id).exclude(pk=existing.pk).exists():
                continue

            if remote_updated_at and existing.updated_at and remote_updated_at <= existing.updated_at:
                model.objects.filter(pk=existing.pk).update(sync_id=sync_id)
            else:
                model.objects.filter(pk=existing.pk).update(sync_id=sync_id, **update_data)
                if remote_updated_at:
                    model.objects.filter(pk=existing.pk).update(updated_at=remote_updated_at)
            return True
        return False

    def _resolve_fk_value(self, field, raw_value):
        if raw_value in (None, ""):
            return None
        related_model = field.related_model
        if related_model._meta.label_lower == "auth.user":
            return related_model.objects.filter(email=raw_value).first() or related_model.objects.filter(username=raw_value).first()
        if hasattr(related_model, "sync_id"):
            return related_model.objects.filter(sync_id=raw_value).first()
        return None

    def _resolve_m2m_values(self, field, raw_values):
        if not raw_values:
            return []
        related_model = field.related_model
        resolved = []
        for raw_value in raw_values:
            if raw_value in (None, ""):
                continue
            if related_model._meta.label_lower == "auth.user":
                obj = related_model.objects.filter(email=raw_value).first() or related_model.objects.filter(username=raw_value).first()
            elif hasattr(related_model, "sync_id"):
                obj = related_model.objects.filter(sync_id=raw_value).first()
            else:
                obj = None
            if obj is not None:
                resolved.append(obj)
        return resolved
