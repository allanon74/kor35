# Generated manually for Arcana SSO password reminder accuracy

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0144_arcanassoidentity_ad_profile_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="arcanassoidentity",
            name="local_password_configured",
            field=models.BooleanField(
                default=False,
                help_text="Impostata a True solo dopo POST /api/auth/arcana/set-local-password/.",
            ),
        ),
    ]
