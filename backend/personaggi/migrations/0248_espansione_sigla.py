# Generated manually for EspansioneCarte.sigla

from django.db import migrations, models


def backfill_sigla(apps, schema_editor):
    EspansioneCarte = apps.get_model("personaggi", "EspansioneCarte")
    # Import locale della logica (copia minimale: non usare carte_set_codice
    # che dipende dal modello aggiornato in runtime).
    import re
    import unicodedata

    stop = {
        "a", "an", "and", "at", "by", "da", "dei", "del", "della", "delle", "di",
        "e", "for", "from", "il", "in", "into", "la", "le", "lo", "of", "on", "or",
        "the", "to", "un", "una", "uno",
    }

    def suggest(nome: str) -> str:
        raw = unicodedata.normalize("NFD", str(nome or ""))
        raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
        tokens = [t for t in re.split(r"[^A-Za-z0-9]+", raw) if t]
        words = [t for t in tokens if t.lower() not in stop] or tokens
        if not words:
            return "SET"
        if len(words) == 1:
            return re.sub(r"[^A-Za-z0-9]", "", words[0]).upper()[:3] or "SET"
        initials = "".join(w[0] for w in words).upper()
        initials = re.sub(r"[^A-Z0-9]", "", initials)
        if len(initials) >= 3:
            return initials[:3]
        last = re.sub(r"[^A-Za-z0-9]", "", words[-1])
        extra = last[1:]
        while len(initials) < 3 and extra:
            initials += extra[0].upper()
            extra = extra[1:]
        return (initials or "SET")[:3]

    for esp in EspansioneCarte.objects.all().only("id", "nome", "slug", "sigla"):
        if (esp.sigla or "").strip():
            continue
        sigla = suggest(esp.nome) if esp.nome else suggest((esp.slug or "").replace("-", " "))
        EspansioneCarte.objects.filter(pk=esp.pk).update(sigla=sigla)


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0247_multigame_carte_gioco_definizione"),
    ]

    operations = [
        migrations.AddField(
            model_name="espansionecarte",
            name="sigla",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Sigla corta del set per i codici carta (es. KBE → KBE-001). Solo A-Z0-9.",
                max_length=8,
            ),
        ),
        migrations.RunPython(backfill_sigla, migrations.RunPython.noop),
    ]
