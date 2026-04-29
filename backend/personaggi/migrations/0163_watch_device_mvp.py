from django.db import migrations, models
import django.db.models.deletion
import uuid

import personaggi.models


class Migration(migrations.Migration):
    dependencies = [
        ("personaggi", "0162_nodo_reward_cooldown_range"),
    ]

    operations = [
        migrations.AddField(
            model_name="personaggio",
            name="watch_enabled",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.CreateModel(
            name="WatchPairingCode",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, editable=False, null=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("device_id", models.CharField(db_index=True, max_length=96)),
                ("code_hash", models.CharField(db_index=True, max_length=128)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("used_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        db_index=True,
                        default=personaggi.models.get_default_campagna_id,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="watch_pairing_codes",
                        to="personaggi.campagna",
                    ),
                ),
            ],
            options={
                "verbose_name": "Watch Pairing Code",
                "verbose_name_plural": "Watch Pairing Codes",
                "indexes": [
                    models.Index(fields=["device_id", "expires_at"], name="personaggi_w_device__f3bfd6_idx"),
                    models.Index(fields=["campagna", "used_at"], name="personaggi_w_campagn_d453d2_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="WatchDeviceBinding",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, editable=False, null=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("device_id", models.CharField(db_index=True, max_length=96)),
                ("pair_token", models.CharField(db_index=True, max_length=96, unique=True)),
                ("firmware_version", models.CharField(blank=True, default="", max_length=64)),
                (
                    "transport_mode",
                    models.CharField(
                        choices=[("WIFI", "Wi-Fi diretto"), ("BT_BRIDGE", "Bluetooth bridge")],
                        default="WIFI",
                        max_length=16,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "campagna",
                    models.ForeignKey(
                        db_index=True,
                        default=personaggi.models.get_default_campagna_id,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="watch_bindings",
                        to="personaggi.campagna",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="watch_bindings",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Watch Device Binding",
                "verbose_name_plural": "Watch Device Bindings",
                "indexes": [
                    models.Index(fields=["personaggio", "is_active"], name="personaggi_w_personag_7adf02_idx"),
                    models.Index(fields=["device_id", "is_active"], name="personaggi_w_device__e43434_idx"),
                    models.Index(fields=["campagna", "is_active"], name="personaggi_w_campagn_8dbd66_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="WatchDeviceEventLog",
            fields=[
                ("sync_id", models.UUIDField(db_index=True, editable=False, null=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("client_event_id", models.CharField(db_index=True, max_length=80)),
                ("stat_sigla", models.CharField(blank=True, default="", max_length=16)),
                ("delta", models.SmallIntegerField(default=0)),
                ("applied", models.BooleanField(db_index=True, default=False)),
                ("server_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "binding",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="event_logs",
                        to="personaggi.watchdevicebinding",
                    ),
                ),
                (
                    "personaggio",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="watch_event_logs",
                        to="personaggi.personaggio",
                    ),
                ),
            ],
            options={
                "verbose_name": "Watch Device Event Log",
                "verbose_name_plural": "Watch Device Event Logs",
                "indexes": [
                    models.Index(fields=["personaggio", "created_at"], name="personaggi_w_personag_182502_idx"),
                    models.Index(fields=["binding", "applied"], name="personaggi_w_binding_042f53_idx"),
                ],
                "unique_together": {("binding", "client_event_id")},
            },
        ),
    ]
