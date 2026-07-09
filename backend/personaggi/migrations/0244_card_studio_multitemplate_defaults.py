from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0243_carte_platform_bridge"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartegiocodefinizione",
            name="modello_base",
            field=models.CharField(
                choices=[
                    ("kor35", "KOR35"),
                    ("mtg", "Magic: The Gathering (MSE-compatible)"),
                    ("custom", "Custom"),
                ],
                db_index=True,
                default="kor35",
                help_text="Preset modello regole/template (KOR35, MTG, custom).",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="cartestudiotemplate",
            name="is_default_for_new_cards",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Template default per nuove carte di questo gioco.",
            ),
        ),
        migrations.AddField(
            model_name="espansionecarte",
            name="default_studio_template",
            field=models.ForeignKey(
                blank=True,
                help_text="Template predefinito per nuove carte in questa espansione.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="espansioni_default",
                to="personaggi.cartestudiotemplate",
            ),
        ),
    ]

