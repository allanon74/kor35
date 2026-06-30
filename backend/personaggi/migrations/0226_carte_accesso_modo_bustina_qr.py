import django.db.models.deletion
from django.db import migrations, models


def migra_abilitata_a_accesso_modo(apps, schema_editor):
    Config = apps.get_model("personaggi", "ConfigurazioneCarteCollezionabili")
    Config.objects.filter(abilitata=True).update(accesso_modo="OPEN")


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0225_carte_abilitata_duello"),
    ]

    operations = [
        migrations.AddField(
            model_name="configurazionecartecollezionabili",
            name="accesso_modo",
            field=models.CharField(
                choices=[
                    ("OFF", "Disattivo (tutti)"),
                    ("TEST", "Testing (solo PnG staff)"),
                    ("OPEN", "Aperto (tutti)"),
                ],
                db_index=True,
                default="OFF",
                help_text="OFF=nessuno, TEST=solo PnG (tipologia non giocante), OPEN=tutti i PG.",
                max_length=4,
            ),
        ),
        migrations.AlterField(
            model_name="configurazionecartecollezionabili",
            name="abilitata",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Deprecato: usare accesso_modo.",
            ),
        ),
        migrations.AddField(
            model_name="bustinacarte",
            name="qr_code",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bustina_carte",
                to="personaggi.qrcode",
            ),
        ),
        migrations.CreateModel(
            name="BustinaCartePortale",
            fields=[
                (
                    "a_vista_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="personaggi.a_vista",
                    ),
                ),
                (
                    "bustina",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="portale_avista",
                        to="personaggi.bustinacarte",
                    ),
                ),
            ],
            options={
                "verbose_name": "Portale bustina carte",
                "verbose_name_plural": "Portali bustine carte",
            },
            bases=("personaggi.a_vista",),
        ),
        migrations.RunPython(migra_abilitata_a_accesso_modo, migrations.RunPython.noop),
    ]
