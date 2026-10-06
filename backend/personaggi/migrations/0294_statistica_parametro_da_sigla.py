from django.db import migrations, models
from django.utils import timezone


def riempi_parametro_da_sigla(apps, schema_editor):
    Statistica = apps.get_model("personaggi", "Statistica")
    occupati = {
        (p or "").strip().upper()
        for p in Statistica.objects.exclude(parametro__isnull=True)
        .exclude(parametro="")
        .values_list("parametro", flat=True)
    }
    now = timezone.now()
    for st in Statistica.objects.filter(models.Q(parametro__isnull=True) | models.Q(parametro="")):
        sigla = (st.sigla or "").strip()
        if not sigla:
            continue
        key = sigla.upper()
        if key in occupati:
            continue
        st.parametro = sigla
        update_fields = ["parametro"]
        if hasattr(st, "updated_at"):
            st.updated_at = now
            update_fields.append("updated_at")
        st.save(update_fields=update_fields)
        occupati.add(key)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0293_pool_pg_attivazione_giocatore"),
    ]

    operations = [
        migrations.AlterField(
            model_name="statistica",
            name="parametro",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Chiave nei modificatori e nelle formule {PARAM}. "
                    "Se vuoto, al salvataggio viene copiata la sigla."
                ),
                max_length=10,
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(riempi_parametro_da_sigla, noop_reverse),
    ]
