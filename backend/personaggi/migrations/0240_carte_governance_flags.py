from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0239_carta_effect_scripts"),
    ]

    operations = [
        migrations.AddField(
            model_name="cartacollezionabile",
            name="ban_reason",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Motivazione ban mostrata in staff/UI.",
            ),
        ),
        migrations.AddField(
            model_name="cartacollezionabile",
            name="bandita",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Se true, carta bandita dai mazzi duello.",
            ),
        ),
        migrations.AddField(
            model_name="cartacollezionabile",
            name="legale_duello",
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text="Se false, carta non legale nei mazzi duello.",
            ),
        ),
        migrations.AddField(
            model_name="espansionecarte",
            name="disclaimer_disattiva",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Nota staff mostrata quando si disattiva l'espansione.",
            ),
        ),
        migrations.AddField(
            model_name="espansionecarte",
            name="in_vendita",
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text="Se false, le bustine dell'espansione non sono acquistabili.",
            ),
        ),
        migrations.AddField(
            model_name="espansionecarte",
            name="legale_duello",
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text="Se false, carte dell'espansione non legali nei mazzi duello.",
            ),
        ),
        migrations.AddField(
            model_name="espansionecarte",
            name="vendita_al",
            field=models.DateTimeField(
                blank=True,
                help_text="Fine finestra vendita bustine (opzionale).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="espansionecarte",
            name="vendita_dal",
            field=models.DateTimeField(
                blank=True,
                help_text="Inizio finestra vendita bustine (opzionale).",
                null=True,
            ),
        ),
    ]
