from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0300_sondaggi"),
    ]

    operations = [
        migrations.AddField(
            model_name="sondaggio",
            name="premio_pc",
            field=models.PositiveIntegerField(
                default=0,
                help_text="PC accreditati al personaggio al primo invio del sondaggio.",
            ),
        ),
        migrations.AddField(
            model_name="sondaggio",
            name="premio_crediti_correnti",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Crediti del conto corrente accreditati al primo invio.",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="sondaggio",
            name="premio_crediti_deposito",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Crediti del conto deposito accreditati al primo invio.",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="rispostasondaggio",
            name="premio_pc",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="rispostasondaggio",
            name="premio_crediti_correnti",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="rispostasondaggio",
            name="premio_crediti_deposito",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="rispostasondaggio",
            name="premio_erogato_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Quando il premio di questo invio è stato accreditato. Vuoto se non c'era premio.",
                null=True,
            ),
        ),
    ]
