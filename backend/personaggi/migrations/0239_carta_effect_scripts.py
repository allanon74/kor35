from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0238_tag_carte"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartacollezionabile",
            name="effect_scripts",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    "EffectScript v1 sulla carta (senza keyword nel testo). "
                    "Ogni elemento: {codice?, nome?, script: {version, trigger, steps, params?}}."
                ),
            ),
        ),
    ]
