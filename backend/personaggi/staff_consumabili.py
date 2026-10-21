"""Gestione staff dei consumabili di un personaggio (fuori dal timer di alchimia)."""
from __future__ import annotations

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from personaggi.models import FEATURE_TESSITURE, ConsumabilePersonaggio, Tessitura

QUANTITA_MAX = 40
UTILIZZI_MAX = 999
GIORNI_SCADENZA_DEFAULT = 30


def messaggio_validazione(exc: ValidationError) -> str:
    if getattr(exc, "messages", None):
        return str(exc.messages[0])
    return str(exc)


def catalogo_tessiture_per_consumabili(request) -> list[dict]:
    """Elenco compatto delle tessiture della campagna, per generare consumabili."""
    from personaggi.views import _campaign_feature_filter

    qs = Tessitura.objects.select_related("aura_richiesta").annotate(
        livello_calc=Sum("componenti__valore")
    )
    if request is not None:
        qs = _campaign_feature_filter(request, qs, FEATURE_TESSITURE)
    rows = []
    for row in qs.order_by("nome")[:800]:
        aura = row.aura_richiesta
        rows.append(
            {
                "id": row.id,
                "nome": row.nome,
                "livello": int(row.livello_calc or 0),
                "aura": aura.nome if aura else "",
            }
        )
    return rows


def _intero(value, *, default: int, minimo: int, massimo: int, etichetta: str) -> int:
    if value in (None, ""):
        parsed = default
    else:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{etichetta.capitalize()} non valido.") from exc
    if parsed < minimo or parsed > massimo:
        raise ValidationError(f"{etichetta.capitalize()} deve essere tra {minimo} e {massimo}.")
    return parsed


def _data_scadenza(value, *, obbligatorio_default: bool) -> date:
    if value in (None, ""):
        if not obbligatorio_default:
            raise ValidationError("Data di scadenza obbligatoria.")
        return timezone.localdate() + timedelta(days=GIORNI_SCADENZA_DEFAULT)
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError as exc:
        raise ValidationError("Data di scadenza non valida (usa AAAA-MM-GG).") from exc


def serializza_consumabili_staff(personaggio) -> list[dict]:
    """Tutti i consumabili del PG, anche scaduti o a zero utilizzi."""
    oggi = timezone.localdate()
    rows = []
    qs = personaggio.consumabili.select_related("tessitura").order_by("-data_creazione", "-id")
    for row in qs:
        rows.append(
            {
                "id": row.id,
                "nome": row.nome,
                "descrizione": row.descrizione or "",
                "formula": row.formula or "",
                "utilizzi_rimanenti": row.utilizzi_rimanenti,
                "data_scadenza": row.data_scadenza.isoformat() if row.data_scadenza else None,
                "tessitura_id": row.tessitura_id,
                "tessitura_nome": row.tessitura.nome if row.tessitura_id else "",
                "scaduto": bool(row.data_scadenza and row.data_scadenza < oggi),
            }
        )
    return rows


def crea_consumabili_staff(personaggio, data: dict) -> list[ConsumabilePersonaggio]:
    """
    Crea una o più copie. Con tessitura_id copia nome, testo e formula della tessitura.
    ``quantita`` è il numero di consumabili distinti; ``utilizzi_rimanenti`` vale per ciascuna copia.
    """
    tessitura = None
    tessitura_id = data.get("tessitura_id")
    if tessitura_id not in (None, ""):
        tessitura = Tessitura.objects.filter(pk=tessitura_id).first()
        if tessitura is None:
            raise ValidationError("Tessitura non trovata.")

    nome = (data.get("nome") or "").strip()
    descrizione = data.get("descrizione")
    formula = data.get("formula")
    if tessitura is not None:
        if not nome:
            nome = tessitura.nome
        if descrizione in (None, ""):
            descrizione = tessitura.testo or ""
        if formula in (None, ""):
            formula = tessitura.formula or ""
    else:
        descrizione = descrizione or ""
        formula = formula or ""

    if not nome:
        raise ValidationError("Indica un nome oppure scegli una tessitura.")
    if len(nome) > 200:
        raise ValidationError("Il nome supera i 200 caratteri.")

    quantita = _intero(
        data.get("quantita"), default=1, minimo=1, massimo=QUANTITA_MAX, etichetta="quantità"
    )
    utilizzi = _intero(
        data.get("utilizzi_rimanenti"),
        default=1,
        minimo=1,
        massimo=UTILIZZI_MAX,
        etichetta="utilizzi",
    )
    scadenza = _data_scadenza(data.get("data_scadenza"), obbligatorio_default=True)
    motivo = (data.get("motivo") or "Assegnazione staff").strip() or "Assegnazione staff"
    origine = f" da «{tessitura.nome}»" if tessitura is not None else ""

    creati = []
    with transaction.atomic():
        for _ in range(quantita):
            creati.append(
                ConsumabilePersonaggio.objects.create(
                    personaggio=personaggio,
                    effetto_casuale=None,
                    tessitura=tessitura,
                    nome=nome,
                    descrizione=descrizione or "",
                    formula=formula or "",
                    utilizzi_rimanenti=utilizzi,
                    data_scadenza=scadenza,
                )
            )
        if quantita == 1:
            testo = (
                f"Staff: aggiunto consumabile «{nome}»{origine} "
                f"({utilizzi} utilizzi, scade {scadenza.isoformat()}) — {motivo}."
            )
        else:
            testo = (
                f"Staff: creati {quantita} consumabili «{nome}»{origine} "
                f"({utilizzi} utilizzi ciascuno, scade {scadenza.isoformat()}) — {motivo}."
            )
        personaggio.aggiungi_log(testo)
    return creati


def aggiorna_consumabile_staff(personaggio, data: dict) -> ConsumabilePersonaggio:
    cid = data.get("consumabile_id")
    row = ConsumabilePersonaggio.objects.filter(pk=cid, personaggio=personaggio).first()
    if row is None:
        raise ValidationError("Consumabile non trovato su questo personaggio.")

    if "nome" in data:
        nome = (data.get("nome") or "").strip()
        if not nome:
            raise ValidationError("Il nome non può essere vuoto.")
        if len(nome) > 200:
            raise ValidationError("Il nome supera i 200 caratteri.")
        row.nome = nome
    if "descrizione" in data and data.get("descrizione") is not None:
        row.descrizione = data.get("descrizione") or ""
    if "formula" in data and data.get("formula") is not None:
        row.formula = data.get("formula") or ""
    if data.get("utilizzi_rimanenti") not in (None, ""):
        row.utilizzi_rimanenti = _intero(
            data.get("utilizzi_rimanenti"),
            default=row.utilizzi_rimanenti,
            minimo=1,
            massimo=UTILIZZI_MAX,
            etichetta="utilizzi",
        )
    if data.get("data_scadenza") not in (None, ""):
        row.data_scadenza = _data_scadenza(data.get("data_scadenza"), obbligatorio_default=False)

    motivo = (data.get("motivo") or "Modifica staff").strip() or "Modifica staff"
    with transaction.atomic():
        row.save()
        personaggio.aggiungi_log(
            f"Staff: aggiornato consumabile «{row.nome}» "
            f"({row.utilizzi_rimanenti} utilizzi, scade {row.data_scadenza.isoformat()}) — {motivo}."
        )
    return row


def rimuovi_consumabile_staff(personaggio, consumabile_id, motivo: str = "") -> str:
    row = ConsumabilePersonaggio.objects.filter(pk=consumabile_id, personaggio=personaggio).first()
    if row is None:
        raise ValidationError("Consumabile non trovato su questo personaggio.")
    nome = row.nome
    motivo = (motivo or "Rimozione staff").strip() or "Rimozione staff"
    with transaction.atomic():
        row.delete()
        personaggio.aggiungi_log(f"Staff: rimosso consumabile «{nome}» — {motivo}.")
    return nome
