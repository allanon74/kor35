# Generated manually for FcmDeviceToken (shell Android Capacitor / FCM)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("personaggi", "0269_chiamata_vocale"),
    ]

    operations = [
        migrations.CreateModel(
            name="FcmDeviceToken",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("token", models.CharField(max_length=512, unique=True)),
                (
                    "platform",
                    models.CharField(
                        choices=[("android", "Android"), ("ios", "iOS")],
                        default="android",
                        max_length=16,
                    ),
                ),
                ("app_id", models.CharField(blank=True, default="", max_length=128)),
                ("user_agent", models.CharField(blank=True, default="", max_length=256)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fcm_device_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Token FCM dispositivo",
                "verbose_name_plural": "Token FCM dispositivi",
            },
        ),
        migrations.AddIndex(
            model_name="fcmdevicetoken",
            index=models.Index(fields=["user", "is_active"], name="personaggi__user_id_fcm_idx"),
        ),
    ]
