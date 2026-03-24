import json
from pathlib import Path

import requests
from django.apps import apps
from django.contrib.auth.models import Group, User
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
from django.db.models import ForeignKey, UniqueConstraint
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from kor35.syncing import serialize_for_sync
from personaggi.models import AuthGroupSyncState, AuthUserSyncState


class Command(BaseCommand):
    help = "Sincronizzazione bidirezionale Replica <-> Master (LWW)."

    def add_arguments(self, parser):
        parser.add_argument("--since", type=str, default=None, help="ISO datetime override per l'export locale.")
        parser.add_argument(
            "--pull-only",
            action="store_true",
            help="Scarica e applica solo dati dal Master, senza inviare modifiche locali.",
        )

    def handle(self, *args, **options):
        sync_url = getattr(settings, "EDGE_SYNC_URL", "").strip()
        sync_token = getattr(settings, "EDGE_SYNC_TOKEN", "").strip()
        state_path = Path(getattr(settings, "EDGE_SYNC_STATE_FILE", settings.BASE_DIR / ".edge_sync_state.json"))

        if not sync_url:
            self.stderr.write("Config mancante: EDGE_SYNC_URL")
            return

        model_registry = self._model_registry()
        self._defer_errors = {}
        since = self._load_since(state_path, options.get("since"))
        pull_only = bool(options.get("pull_only"))
        outgoing = {} if pull_only else self._build_outgoing_payload(model_registry, since)

        headers = {"Content-Type": "application/json"}
        if sync_token:
            headers["Authorization"] = f"EdgeToken {sync_token}"

        payload = {
            "source_node": getattr(settings, "EDGE_NODE_NAME", "replica"),
            "last_sync_timestamp": since.isoformat() if since else None,
            "records": outgoing,
        }

        try:
            response = requests.post(sync_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
        except requests.HTTPError as exc:
            body = getattr(exc.response, "text", "") or ""
            self.stderr.write(self.style.ERROR(f"HTTP {exc.response.status_code} da Master"))
            self.stderr.write(body[:12000] if body else "(nessun body)")
            raise
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"Errore di rete: {exc}"))
            raise

        try:
            incoming_payload = response.json().get("records", {})
        except ValueError:
            self.stderr.write(self.style.ERROR("Risposta non JSON:"))
            self.stderr.write(response.text[:12000])
            raise

        self._apply_incoming_payload(model_registry, incoming_payload)
        self._save_state(state_path, timezone.now())
        self.stdout.write(self.style.SUCCESS("Sync completata."))

    def _model_registry(self):
        registry = {}
        for app_label in ("personaggi", "gestione_plot", "social"):
            app_config = apps.get_app_config(app_label)
            for model in app_config.get_models():
                if model._meta.abstract:
                    continue
                if hasattr(model, "sync_id") and hasattr(model, "updated_at"):
                    registry[model._meta.label_lower] = model
        return registry

    def _load_since(self, state_path: Path, since_override: str | None):
        if since_override:
            dt = parse_datetime(since_override)
            return dt if dt else None
        if not state_path.exists():
            return None
        try:
            data = json.loads(state_path.read_text())
            dt = parse_datetime(data.get("last_successful_sync"))
            return dt if dt else None
        except Exception:
            return None

    def _save_state(self, state_path: Path, timestamp):
        state_path.write_text(json.dumps({"last_successful_sync": timestamp.isoformat()}, indent=2))

    def _build_outgoing_payload(self, model_registry, since):
        payload = {}
        for key, model in model_registry.items():
            qs = model.objects.all()
            if since and hasattr(model, "updated_at"):
                qs = qs.filter(updated_at__gt=since)
            payload[key] = [serialize_for_sync(obj) for obj in qs.iterator()]

        payload["auth.user"] = self._build_users_payload(since)
        payload["auth.group"] = self._build_groups_payload(since)
        return payload

    def _apply_incoming_payload(self, model_registry, incoming_payload):
        self._apply_users_payload(incoming_payload.get("auth.user", []))
        self._apply_groups_payload(incoming_payload.get("auth.group", []))

        # Applicazione robusta con retry: processa record solo quando tutte le FK
        # obbligatorie (e parent link) sono risolvibili.
        pending = []
        for model_key, records in incoming_payload.items():
            if model_key in {"auth.user", "auth.group"}:
                continue
            model = model_registry.get(model_key)
            if not model:
                continue
            for row in records:
                pending.append((model, row))

        max_rounds = max(len(pending), 1)
        with transaction.atomic():
            for _ in range(max_rounds):
                if not pending:
                    return
                next_pending = []
                progressed = 0

                for model, row in pending:
                    status = self._try_apply_one(model, row)
                    if status == "defer":
                        next_pending.append((model, row))
                        continue
                    if status == "skipped":
                        progressed += 1
                        continue
                    progressed += 1

                pending = next_pending
                if progressed == 0:
                    break

        if pending:
            first_model, first_row = pending[0]
            self.stderr.write(
                self.style.WARNING(
                    f"Record non applicati ({len(pending)}). Primo: {first_model._meta.label_lower} sync_id={first_row.get('sync_id')}"
                )
            )
        if self._defer_errors:
            self.stderr.write(self.style.WARNING("Top errori defer:"))
            for key, count in sorted(self._defer_errors.items(), key=lambda x: x[1], reverse=True)[:10]:
                self.stderr.write(f" - {key}: {count}")

    def _try_apply_one(self, model, row):
        sync_id = row.get("sync_id")
        if not sync_id:
            return "skipped"

        remote_updated_at = parse_datetime(row.get("updated_at")) if row.get("updated_at") else None
        local_obj = model.objects.filter(sync_id=sync_id).first()

        # M2M (es. mattoni_materia_permessi) non aggiornano updated_at sul modello padre: se
        # saltiamo tutto il record per LWW, quei valori non verrebbero mai applicati.
        m2m_updates = {}
        for m2m_field in model._meta.many_to_many:
            if m2m_field.auto_created:
                continue
            if m2m_field.name not in row:
                continue
            m2m_updates[m2m_field.name] = row.get(m2m_field.name) or []

        skip_scalars = bool(
            local_obj
            and remote_updated_at
            and local_obj.updated_at
            and remote_updated_at <= local_obj.updated_at
        )
        if skip_scalars:
            if not m2m_updates:
                return "skipped"
            obj = local_obj
            for field_name, raw_values in m2m_updates.items():
                resolved_list, unresolved = self._resolve_m2m_values(model, field_name, raw_values)
                if unresolved:
                    return "defer"
                getattr(obj, field_name).set(resolved_list)
            if remote_updated_at:
                model.objects.filter(pk=obj.pk).update(updated_at=remote_updated_at)
            return "applied"

        update_data = {}

        for field in model._meta.concrete_fields:
            if field.name in {"id", "sync_id"}:
                continue
            # Multi-table inheritance: solo il parent_link *immediato* (field.model == model).
            # Altrimenti su Statistica/Mattone si valorizza anche tabella_ptr (modello Punteggio)
            # con un Tabella grezzo e Django va in errore (manca tabella_ptr_id sul tipo sbagliato).
            if isinstance(field, ForeignKey) and getattr(field.remote_field, "parent_link", False):
                # Never rewrite parent-link on existing rows: it effectively changes PK
                # and may break FK references (e.g. Personaggio -> SegnoZodiacale).
                if local_obj is not None:
                    continue
                if field.model != model:
                    continue
                parent_obj = field.related_model.objects.filter(sync_id=sync_id).first()
                if parent_obj is None:
                    return "defer"
                update_data[field.name] = parent_obj
                continue
            if field.name not in row:
                continue
            value = row[field.name]
            if isinstance(field, ForeignKey):
                resolved = self._resolve_fk_value(model, field.name, value)
                if resolved is None and not field.null and value not in (None, ""):
                    return "defer"
                update_data[field.name] = resolved
                continue
            if field.name == "updated_at":
                dt = parse_datetime(value) if value else None
                if dt:
                    update_data[field.name] = dt
                continue
            update_data[field.name] = value

        try:
            obj, _ = model.objects.update_or_create(sync_id=sync_id, defaults=update_data)
        except IntegrityError as exc:
            if self._merge_after_integrity_error(
                model, sync_id, row, update_data, remote_updated_at
            ):
                obj = model.objects.filter(sync_id=sync_id).first()
                if obj is None:
                    msg = str(exc).strip().replace("\n", " ")
                    err_key = f"{model._meta.label_lower}: {exc.__class__.__name__}: {msg}"
                    self._defer_errors[err_key] = self._defer_errors.get(err_key, 0) + 1
                    return "defer"
            else:
                msg = str(exc).strip().replace("\n", " ")
                if len(msg) > 120:
                    msg = msg[:120] + "..."
                err_key = f"{model._meta.label_lower}: {exc.__class__.__name__}: {msg}"
                self._defer_errors[err_key] = self._defer_errors.get(err_key, 0) + 1
                return "defer"
        except ValidationError as exc:
            if self._merge_after_validation_error(
                model, sync_id, update_data, remote_updated_at
            ):
                obj = model.objects.filter(sync_id=sync_id).first()
                if obj is None:
                    msg = str(exc).strip().replace("\n", " ")
                    if len(msg) > 120:
                        msg = msg[:120] + "..."
                    err_key = f"{model._meta.label_lower}: {exc.__class__.__name__}: {msg}"
                    self._defer_errors[err_key] = self._defer_errors.get(err_key, 0) + 1
                    return "defer"
            else:
                msg = str(exc).strip().replace("\n", " ")
                if len(msg) > 120:
                    msg = msg[:120] + "..."
                err_key = f"{model._meta.label_lower}: {exc.__class__.__name__}: {msg}"
                self._defer_errors[err_key] = self._defer_errors.get(err_key, 0) + 1
                return "defer"
        except Exception as exc:
            # Modelli complessi (es. ereditarieta' multi-table) possono richiedere
            # che altre righe siano gia' presenti. Rimanda e riprova al round successivo.
            msg = str(exc).strip().replace("\n", " ")
            if len(msg) > 120:
                msg = msg[:120] + "..."
            err_key = f"{model._meta.label_lower}: {exc.__class__.__name__}: {msg}"
            self._defer_errors[err_key] = self._defer_errors.get(err_key, 0) + 1
            return "defer"

        for field_name, raw_values in m2m_updates.items():
            resolved_list, unresolved = self._resolve_m2m_values(model, field_name, raw_values)
            if unresolved:
                return "defer"
            getattr(obj, field_name).set(resolved_list)

        if remote_updated_at:
            model.objects.filter(pk=obj.pk).update(updated_at=remote_updated_at)

        return "applied"

    def _iter_unique_field_groups(self, model):
        """Tuple di nomi campo per vincoli UNIQUE (legacy + UniqueConstraint)."""
        seen = set()
        for ut in model._meta.unique_together or ():
            group = tuple(ut) if not isinstance(ut, str) else (ut,)
            if group and group not in seen:
                seen.add(group)
                yield group
        for c in getattr(model._meta, "constraints", ()) or ():
            if isinstance(c, UniqueConstraint) and not c.condition and c.fields:
                group = tuple(c.fields)
                if group not in seen:
                    seen.add(group)
                    yield group

    def _merge_after_integrity_error(self, model, sync_id, row, update_data, remote_updated_at):
        """
        Replica: stessa chiave naturale (unique_together / unique) ma sync_id diverso
        rispetto al master -> allinea sync_id e campi sulla riga esistente.
        """
        if model._meta.label_lower == "personaggi.segnozodiacale":
            if self._merge_segno_zodiacale_by_numero(model, row, update_data, remote_updated_at):
                return True

        for group in self._iter_unique_field_groups(model):
            kwargs = {}
            for fname in group:
                if fname not in update_data:
                    break
                kwargs[fname] = update_data[fname]
            else:
                existing = model.objects.filter(**kwargs).first()
                if existing and str(existing.sync_id) != str(sync_id):
                    patch = dict(update_data)
                    patch["sync_id"] = sync_id
                    if remote_updated_at:
                        patch["updated_at"] = remote_updated_at
                    model.objects.filter(pk=existing.pk).update(**patch)
                    return True

        if self._merge_by_natural_unique_key(model, sync_id, row, update_data, remote_updated_at):
            return True
        return False

    def _merge_segno_zodiacale_by_numero(self, model, row, update_data, remote_updated_at):
        numero = row.get("numero")
        if numero in (None, ""):
            return False
        existing = model.objects.filter(numero=numero).first()
        if not existing:
            return False
        patch = dict(update_data)
        # Never patch parent-link fields on existing rows.
        for f in model._meta.concrete_fields:
            if isinstance(f, ForeignKey) and getattr(f.remote_field, "parent_link", False):
                patch.pop(f.name, None)
        if remote_updated_at:
            patch["updated_at"] = remote_updated_at
        try:
            with transaction.atomic():
                model.objects.filter(pk=existing.pk).update(**patch)
        except IntegrityError:
            if "updated_at" in patch:
                model.objects.filter(pk=existing.pk).update(updated_at=patch["updated_at"])
        return True

    def _merge_after_validation_error(self, model, sync_id, update_data, remote_updated_at):
        """
        Alcuni modelli applicano vincoli solo in clean()/save() (no unique_together DB).
        Es. PersonaggioModelloAura: un solo modello per (personaggio, aura).
        """
        if model._meta.label_lower == "personaggi.personaggiomodelloaura":
            return self._merge_personaggio_modello_aura(
                model, sync_id, update_data, remote_updated_at
            )
        return False

    def _merge_personaggio_modello_aura(self, model, sync_id, update_data, remote_updated_at):
        personaggio = update_data.get("personaggio")
        modello_aura = update_data.get("modello_aura")
        if personaggio is None or modello_aura is None:
            return False
        aura_id = getattr(modello_aura, "aura_id", None)
        if aura_id is None:
            aura = getattr(modello_aura, "aura", None)
            if aura is None:
                return False
            aura_id = aura.pk
        existing = model.objects.filter(
            personaggio=personaggio, modello_aura__aura_id=aura_id
        ).first()
        if existing is None:
            return False
        patch = dict(update_data)
        patch["sync_id"] = sync_id
        if remote_updated_at:
            patch["updated_at"] = remote_updated_at
        model.objects.filter(pk=existing.pk).update(**patch)
        return True

    def _merge_by_natural_unique_key(self, model, sync_id, row, update_data, remote_updated_at):
        """Campo scalare con unique=True (es. nome, sigla)."""
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

            # NOTE:
            # On natural-key merge we never force sync_id alignment for existing rows.
            # With multi-table inheritance (Tabella/Tier/*) sync_id uniqueness lives on parent
            # tables too, and forcing sync_id can trigger cross-table collisions.
            patch = dict(update_data)
            # Never patch parent-link fields on existing rows.
            for f in model._meta.concrete_fields:
                if isinstance(f, ForeignKey) and getattr(f.remote_field, "parent_link", False):
                    patch.pop(f.name, None)
            if remote_updated_at:
                patch["updated_at"] = remote_updated_at
            try:
                # Use a savepoint so IntegrityError doesn't poison outer transaction.
                with transaction.atomic():
                    model.objects.filter(pk=existing.pk).update(**patch)
            except IntegrityError:
                # Last-resort fallback: apply only updated_at if payload still conflicts.
                if "updated_at" in patch:
                    model.objects.filter(pk=existing.pk).update(updated_at=patch["updated_at"])
            return True
        return False

    def _resolve_fk_value(self, model, field_name, raw_value):
        if raw_value in (None, ""):
            return None
        field = model._meta.get_field(field_name)
        related_model = field.related_model

        # User: lookup natural key (email -> fallback username)
        if related_model._meta.label_lower == "auth.user":
            user = related_model.objects.filter(email=raw_value).first()
            return user or related_model.objects.filter(username=raw_value).first()

        if hasattr(related_model, "sync_id"):
            return related_model.objects.filter(sync_id=raw_value).first()

        return None

    def _resolve_m2m_values(self, model, field_name, raw_values):
        field = model._meta.get_field(field_name)
        related_model = field.related_model
        resolved = []
        unresolved = 0
        for raw_value in raw_values or []:
            if raw_value in (None, ""):
                continue
            if related_model._meta.label_lower == "auth.user":
                obj = related_model.objects.filter(email=raw_value).first()
                obj = obj or related_model.objects.filter(username=raw_value).first()
            elif hasattr(related_model, "sync_id"):
                obj = related_model.objects.filter(sync_id=raw_value).first()
            else:
                obj = None
            if obj is not None:
                resolved.append(obj)
            else:
                unresolved += 1
        return resolved, unresolved

    def _build_users_payload(self, since):
        qs = User.objects.all().select_related("sync_state")
        if since:
            qs = qs.filter(sync_state__updated_at__gt=since)
        return [
            {
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "password": user.password,
                "updated_at": user.sync_state.updated_at.isoformat() if hasattr(user, "sync_state") else timezone.now().isoformat(),
            }
            for user in qs.iterator()
        ]

    def _build_groups_payload(self, since):
        qs = Group.objects.all().select_related("sync_state")
        if since:
            qs = qs.filter(sync_state__updated_at__gt=since)
        payload = []
        for group in qs.iterator():
            payload.append(
                {
                    "name": group.name,
                    "permissions": list(group.permissions.values_list("codename", flat=True)),
                    "updated_at": group.sync_state.updated_at.isoformat() if hasattr(group, "sync_state") else timezone.now().isoformat(),
                }
            )
        return payload

    def _apply_users_payload(self, rows):
        for row in rows:
            username = row.get("username")
            if not username:
                continue

            remote_updated_at = parse_datetime(row.get("updated_at")) if row.get("updated_at") else None
            local_user = User.objects.filter(username=username).select_related("sync_state").first()
            local_updated_at = getattr(getattr(local_user, "sync_state", None), "updated_at", None)
            if local_user and remote_updated_at and local_updated_at and remote_updated_at <= local_updated_at:
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
            user, _ = User.objects.update_or_create(username=username, defaults=defaults)
            AuthUserSyncState.objects.update_or_create(
                user=user,
                defaults={"updated_at": remote_updated_at or timezone.now()},
            )

    def _apply_groups_payload(self, rows):
        from django.contrib.auth.models import Permission

        for row in rows:
            group_name = row.get("name")
            if not group_name:
                continue

            remote_updated_at = parse_datetime(row.get("updated_at")) if row.get("updated_at") else None
            local_group = Group.objects.filter(name=group_name).select_related("sync_state").first()
            local_updated_at = getattr(getattr(local_group, "sync_state", None), "updated_at", None)
            if local_group and remote_updated_at and local_updated_at and remote_updated_at <= local_updated_at:
                continue

            group, _ = Group.objects.update_or_create(name=group_name)
            codenames = row.get("permissions", [])
            if codenames:
                perms = Permission.objects.filter(codename__in=codenames)
                group.permissions.set(perms)
            AuthGroupSyncState.objects.update_or_create(
                group=group,
                defaults={"updated_at": remote_updated_at or timezone.now()},
            )
