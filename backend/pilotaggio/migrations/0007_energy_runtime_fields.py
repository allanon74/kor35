from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pilotaggio", "0006_comandocriticoglobale"),
    ]

    operations = [
        migrations.AddField(
            model_name="sessionevolo",
            name="carburante_attuale",
            field=models.FloatField(default=1000.0),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="carburante_massimo",
            field=models.FloatField(default=1000.0),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="coeff_rigenerazione_carburante_riposo",
            field=models.FloatField(default=1.0),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="consumo_ultimo_tick",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="distanza_percorsa",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="distanza_target",
            field=models.FloatField(default=1000.0),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="produzione_ultimo_tick",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="storage_energia_attuale",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="storage_energia_massimo",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="sessionevolo",
            name="tick_secondi",
            field=models.PositiveIntegerField(default=5),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="capacita_storage",
            field=models.FloatField(
                default=0.0, help_text="Capacita energetica (solo batterie)."
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="coeff_consumo_carburante",
            field=models.FloatField(
                default=0.0,
                help_text="Carburante usato per tick = livello * coeff_consumo_carburante.",
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="coeff_consumo_energia",
            field=models.FloatField(
                default=1.0,
                help_text="Energia assorbita per tick = livello * coeff_consumo_energia.",
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="coeff_produzione",
            field=models.FloatField(
                default=0.0,
                help_text="Energia prodotta per tick = livello * coeff_produzione.",
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="coeff_ricarica_storage",
            field=models.FloatField(
                default=0.5,
                help_text="Conversione energia->storage in riposo (es. 0.5 significa 2:1).",
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="gruppo",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Nome del sistema di appartenenza (es. Difesa, Alimentazione).",
                max_length=80,
            ),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="ordine",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="probabilita_guasto_7",
            field=models.FloatField(default=0.01),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="probabilita_guasto_8",
            field=models.FloatField(default=0.1),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="probabilita_guasto_9",
            field=models.FloatField(default=0.25),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="supporta_direzioni",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="supporta_espulsione",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="supporta_inversione",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="sottosistemanave",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("generatore", "Generatore"),
                    ("batteria", "Batteria"),
                    ("motore", "Motore principale"),
                    ("portale", "Portale transdimensionale"),
                    ("manovra", "Propulsori di manovra"),
                ],
                default="standard",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="statosottosistemasessione",
            name="direzione",
            field=models.CharField(
                choices=[
                    ("avanti", "Avanti"),
                    ("indietro", "Indietro"),
                    ("su", "Su"),
                    ("giu", "Giu"),
                    ("destra", "Destra"),
                    ("sinistra", "Sinistra"),
                ],
                default="avanti",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="statosottosistemasessione",
            name="espulso",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="statosottosistemasessione",
            name="invertito",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="statosottosistemasessione",
            name="livello_attuale",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="statosottosistemasessione",
            name="livello_target",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
