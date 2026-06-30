from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0229_scontro_carte_lobby"),
    ]

    operations = [
        migrations.AddField(
            model_name="keywordcarta",
            name="effect_script",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="EffectScript v1 (JSON) per automazione duello; opzionale.",
            ),
        ),
    ]
