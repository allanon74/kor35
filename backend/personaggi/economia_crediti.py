"""
Economia duale: conti corrente / deposito.

Il ledger resta CreditoMovimento; il campo ``conto`` distingue i saldi.
La riserva scommesse è assorbita nel deposito.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

CONTO_CORRENTE = "CORRENTE"
CONTO_DEPOSITO = "DEPOSITO"
CONTO_CHOICES = [
    (CONTO_CORRENTE, "Conto corrente"),
    (CONTO_DEPOSITO, "Conto di deposito"),
]
CONTI_VALIDI = {CONTO_CORRENTE, CONTO_DEPOSITO}

CATEGORIA_OGGETTO = "oggetto"
CATEGORIA_MATERIA = "materia"
CATEGORIA_CONSUMABILE = "consumabile"
CATEGORIA_NEGOZIO = "negozio"
CATEGORIE_SPESA_DEPOSITO_DEFAULT = (
    CATEGORIA_OGGETTO,
    CATEGORIA_MATERIA,
    CATEGORIA_CONSUMABILE,
    CATEGORIA_NEGOZIO,
)
CATEGORIE_SPESA_DEPOSITO_VALIDE = set(CATEGORIE_SPESA_DEPOSITO_DEFAULT)

DEFAULT_FRAZIONE_TRASFERIMENTO = Decimal("1.00")
DEFAULT_FATTORE_VALORE_DEPOSITO = Decimal("0.90")

DEFAULT_ECONOMIA_CONFIG: dict[str, Any] = {
    "frazione_trasferimento_stipendio": str(DEFAULT_FRAZIONE_TRASFERIMENTO),
    "fattore_valore_deposito": str(DEFAULT_FATTORE_VALORE_DEPOSITO),
    "categorie_spesa_deposito": list(CATEGORIE_SPESA_DEPOSITO_DEFAULT),
}


def _d2(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_economia_config(campagna=None) -> dict[str, Any]:
    """Merge default + override JSON su Campagna.economia_config."""
    cfg = dict(DEFAULT_ECONOMIA_CONFIG)
    cfg["categorie_spesa_deposito"] = list(CATEGORIE_SPESA_DEPOSITO_DEFAULT)
    raw = getattr(campagna, "economia_config", None) if campagna is not None else None
    if not isinstance(raw, dict):
        return cfg

    if "frazione_trasferimento_stipendio" in raw and raw["frazione_trasferimento_stipendio"] is not None:
        cfg["frazione_trasferimento_stipendio"] = str(_d2(raw["frazione_trasferimento_stipendio"]))
    if "fattore_valore_deposito" in raw and raw["fattore_valore_deposito"] is not None:
        fattore = _d2(raw["fattore_valore_deposito"])
        if fattore <= 0:
            fattore = DEFAULT_FATTORE_VALORE_DEPOSITO
        cfg["fattore_valore_deposito"] = str(fattore)
    cats = raw.get("categorie_spesa_deposito")
    if isinstance(cats, list):
        cleaned = [str(c).strip().lower() for c in cats if str(c).strip().lower() in CATEGORIE_SPESA_DEPOSITO_VALIDE]
        cfg["categorie_spesa_deposito"] = cleaned
    return cfg


def validate_economia_config_payload(payload) -> dict[str, Any]:
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValidationError({"economia_config": "Deve essere un oggetto JSON."})
    out: dict[str, Any] = {}
    if "frazione_trasferimento_stipendio" in payload:
        try:
            out["frazione_trasferimento_stipendio"] = str(_d2(payload["frazione_trasferimento_stipendio"]))
        except Exception as exc:
            raise ValidationError({"frazione_trasferimento_stipendio": "Valore non valido."}) from exc
    if "fattore_valore_deposito" in payload:
        try:
            fattore = _d2(payload["fattore_valore_deposito"])
        except Exception as exc:
            raise ValidationError({"fattore_valore_deposito": "Valore non valido."}) from exc
        if fattore <= 0 or fattore > Decimal("1.00"):
            raise ValidationError({"fattore_valore_deposito": "Deve essere tra 0.01 e 1.00."})
        out["fattore_valore_deposito"] = str(fattore)
    if "categorie_spesa_deposito" in payload:
        cats = payload["categorie_spesa_deposito"]
        if not isinstance(cats, list):
            raise ValidationError({"categorie_spesa_deposito": "Deve essere una lista."})
        cleaned = []
        for c in cats:
            key = str(c).strip().lower()
            if key not in CATEGORIE_SPESA_DEPOSITO_VALIDE:
                raise ValidationError({"categorie_spesa_deposito": f"Categoria sconosciuta: {c}"})
            if key not in cleaned:
                cleaned.append(key)
        out["categorie_spesa_deposito"] = cleaned
    return out


def apply_economia_config(campagna, payload, *, merge: bool = True) -> dict[str, Any]:
    cleaned = validate_economia_config_payload(payload)
    if merge:
        current = dict(campagna.economia_config or {}) if isinstance(campagna.economia_config, dict) else {}
        current.update(cleaned)
        campagna.economia_config = current
    else:
        campagna.economia_config = cleaned
    campagna.save(update_fields=["economia_config", "updated_at"])
    return get_economia_config(campagna)


def modulo_conto_deposito_attivo(personaggio, user=None) -> bool:
    """True se il modulo campagna ``conto_deposito`` è accessibile al PG/user."""
    from personaggi.campagna_moduli import MODULO_CONTO_DEPOSITO, personaggio_puo_accedere_modulo

    if personaggio is None:
        return False
    return personaggio_puo_accedere_modulo(personaggio, MODULO_CONTO_DEPOSITO, user=user)


def campagna_ha_conto_deposito(campagna) -> bool:
    """True se il modulo non è OFF (TEST/OPEN) — utile per staff/config."""
    from personaggi.campagna_moduli import (
        MODULO_ACCESSO_OFF,
        MODULO_CONTO_DEPOSITO,
        get_modulo_accesso,
    )

    if campagna is None:
        return False
    return get_modulo_accesso(campagna, MODULO_CONTO_DEPOSITO) != MODULO_ACCESSO_OFF


def saldo_conto(personaggio, conto: str) -> Decimal:
    conto = (conto or CONTO_CORRENTE).upper()
    if conto not in CONTI_VALIDI:
        raise ValidationError(f"Conto non valido: {conto}")
    totale = (
        personaggio.movimenti_credito.filter(conto=conto).aggregate(totale=Sum("importo"))["totale"]
        or Decimal("0")
    )
    totale = _d2(totale)
    if conto == CONTO_CORRENTE:
        base = _d2(personaggio.tipologia.crediti_iniziali if personaggio.tipologia_id else 0)
        return _d2(base + totale)
    return totale


def saldo_corrente(personaggio) -> Decimal:
    return saldo_conto(personaggio, CONTO_CORRENTE)


def saldo_deposito(personaggio) -> Decimal:
    return saldo_conto(personaggio, CONTO_DEPOSITO)


def saldo_spendibile(personaggio, *, user=None) -> Decimal:
    """Con modulo ON = solo corrente; OFF = corrente + deposito (monoconto)."""
    corrente = saldo_corrente(personaggio)
    if modulo_conto_deposito_attivo(personaggio, user=user):
        return corrente
    return _d2(corrente + saldo_deposito(personaggio))


def prezzo_da_deposito(prezzo, fattore=None, campagna=None) -> Decimal:
    """
    Potere d'acquisto ridotto: prezzo_deposito = prezzo_corrente / fattore.
    Default fattore 0.90 → si paga di più dal deposito.
    """
    prezzo = _d2(prezzo)
    if prezzo <= 0:
        return Decimal("0.00")
    if fattore is None:
        cfg = get_economia_config(campagna)
        fattore = Decimal(cfg["fattore_valore_deposito"])
    else:
        fattore = _d2(fattore)
    if fattore <= 0:
        fattore = DEFAULT_FATTORE_VALORE_DEPOSITO
    # ceil-like via quantize half-up on division
    return _d2(prezzo / fattore)


def categoria_ammessa_deposito(categoria: str, campagna=None) -> bool:
    cfg = get_economia_config(campagna)
    return str(categoria or "").strip().lower() in set(cfg.get("categorie_spesa_deposito") or [])


def modifica_crediti(
    personaggio,
    importo,
    descrizione: str,
    *,
    conto: str = CONTO_CORRENTE,
    evento=None,
):
    """Crea un CreditoMovimento sul conto indicato."""
    from personaggi.models import CreditoMovimento

    conto = (conto or CONTO_CORRENTE).upper()
    if conto not in CONTI_VALIDI:
        raise ValidationError(f"Conto non valido: {conto}")
    importo = _d2(importo)
    if importo == 0:
        return None
    kwargs = {
        "personaggio": personaggio,
        "importo": importo,
        "descrizione": (descrizione or "")[:200],
        "conto": conto,
    }
    if evento is not None:
        kwargs["evento_id"] = getattr(evento, "pk", evento)
    return CreditoMovimento.objects.create(**kwargs)


def addebita(
    personaggio,
    importo,
    descrizione: str,
    *,
    conto: str = CONTO_CORRENTE,
    evento=None,
    user=None,
    allow_monoconto_fallback: bool = True,
):
    """
    Scala crediti dal conto richiesto.
    Con modulo OFF e conto corrente, se allow_monoconto_fallback e saldo corrente
    insufficiente ma totale (corrente+deposito) ok, addebita prima corrente poi deposito.
    """
    importo = _d2(importo)
    if importo <= 0:
        raise ValidationError("Importo addebito non valido.")
    conto = (conto or CONTO_CORRENTE).upper()
    if conto not in CONTI_VALIDI:
        raise ValidationError(f"Conto non valido: {conto}")

    duale = modulo_conto_deposito_attivo(personaggio, user=user)
    if not duale and conto == CONTO_CORRENTE and allow_monoconto_fallback:
        disponibile = saldo_spendibile(personaggio, user=user)
        if disponibile < importo:
            raise ValidationError(
                f"Crediti insufficienti. Posseduti: {disponibile}, richiesti: {importo}."
            )
        corrente = saldo_corrente(personaggio)
        da_corrente = min(corrente, importo)
        resto = _d2(importo - da_corrente)
        if da_corrente > 0:
            modifica_crediti(personaggio, -da_corrente, descrizione, conto=CONTO_CORRENTE, evento=evento)
        if resto > 0:
            modifica_crediti(personaggio, -resto, descrizione, conto=CONTO_DEPOSITO, evento=evento)
        return

    disponibile = saldo_conto(personaggio, conto)
    if disponibile < importo:
        label = "corrente" if conto == CONTO_CORRENTE else "deposito"
        raise ValidationError(
            f"Crediti {label} insufficienti. Posseduti: {disponibile}, richiesti: {importo}."
        )
    modifica_crediti(personaggio, -importo, descrizione, conto=conto, evento=evento)


def addebita_bene(
    personaggio,
    prezzo_listino,
    descrizione: str,
    *,
    conto: str = CONTO_CORRENTE,
    categoria: str,
    campagna=None,
    evento=None,
    user=None,
) -> Decimal:
    """
    Addebita un acquisto beni. Ritorna l'importo effettivamente scalato.
    Con deposito applica fattore valore e verifica categoria.
    """
    prezzo = _d2(prezzo_listino)
    conto = (conto or CONTO_CORRENTE).upper()
    campagna = campagna or getattr(personaggio, "campagna", None)
    duale = modulo_conto_deposito_attivo(personaggio, user=user)

    if conto == CONTO_DEPOSITO:
        if not duale:
            raise ValidationError("Il conto di deposito non è attivo in questa campagna.")
        if not categoria_ammessa_deposito(categoria, campagna):
            raise ValidationError("Questa spesa non può essere pagata con il conto di deposito.")
        da_pagare = prezzo_da_deposito(prezzo, campagna=campagna)
        addebita(
            personaggio,
            da_pagare,
            descrizione,
            conto=CONTO_DEPOSITO,
            evento=evento,
            user=user,
            allow_monoconto_fallback=False,
        )
        return da_pagare

    addebita(
        personaggio,
        prezzo,
        descrizione,
        conto=CONTO_CORRENTE,
        evento=evento,
        user=user,
        allow_monoconto_fallback=True,
    )
    return prezzo


def prezzi_duali(prezzo_listino, campagna=None, *, categoria: str | None = None) -> dict[str, Any]:
    prezzo = _d2(prezzo_listino)
    cfg = get_economia_config(campagna)
    ammesso = categoria is None or categoria_ammessa_deposito(categoria, campagna)
    out = {
        "prezzo_corrente": str(prezzo),
        "prezzo_deposito": None,
        "fattore_valore_deposito": cfg["fattore_valore_deposito"],
        "deposito_ammesso": bool(ammesso),
    }
    if ammesso:
        out["prezzo_deposito"] = str(prezzo_da_deposito(prezzo, campagna=campagna))
    return out


def stipendio_evento(personaggio, evento, ts=None) -> Decimal:
    from gestione_plot.evento_premi import calcola_crediti_premio_evento

    return _d2(calcola_crediti_premio_evento(evento, personaggio, ts=ts))


def tetto_trasferimento_deposito(personaggio, evento, campagna=None, ts=None) -> Decimal:
    campagna = campagna or getattr(personaggio, "campagna", None)
    cfg = get_economia_config(campagna)
    frazione = Decimal(cfg["frazione_trasferimento_stipendio"])
    stipendio = stipendio_evento(personaggio, evento, ts=ts)
    return _d2(frazione * stipendio)


def trasferimento_gia_effettuato(personaggio, evento) -> bool:
    from gestione_plot.models import EventoTrasferimentoDeposito

    return EventoTrasferimentoDeposito.objects.filter(
        evento=evento, personaggio=personaggio
    ).exists()


def trasferisci_deposito_a_corrente(
    personaggio,
    importo,
    evento,
    *,
    force: bool = False,
    user=None,
    descrizione: str | None = None,
) -> Decimal:
    """
    Sposta CR dal deposito al corrente (1× per evento salvo force staff).
    Ritorna l'importo trasferito.
    """
    from gestione_plot.models import EventoTrasferimentoDeposito

    importo = _d2(importo)
    if importo <= 0:
        raise ValidationError("Importo trasferimento non valido.")
    if evento is None:
        raise ValidationError("Evento richiesto per il trasferimento.")

    if not force and not modulo_conto_deposito_attivo(personaggio, user=user):
        raise ValidationError("Il conto di deposito non è attivo.")

    with transaction.atomic():
        if not force and trasferimento_gia_effettuato(personaggio, evento):
            raise ValidationError("Hai già effettuato il trasferimento deposito→corrente per questo evento.")

        tetto = tetto_trasferimento_deposito(personaggio, evento)
        if importo > tetto:
            raise ValidationError(
                f"Importo oltre il tetto consentito ({tetto} CR = frazione × stipendio evento)."
            )
        disp = saldo_deposito(personaggio)
        if importo > disp:
            raise ValidationError(f"Deposito insufficiente. Disponibile: {disp} CR.")

        if not force:
            _row, created = EventoTrasferimentoDeposito.objects.get_or_create(
                evento=evento,
                personaggio=personaggio,
                defaults={"importo": importo},
            )
            if not created:
                raise ValidationError("Hai già effettuato il trasferimento deposito→corrente per questo evento.")
        else:
            EventoTrasferimentoDeposito.objects.update_or_create(
                evento=evento,
                personaggio=personaggio,
                defaults={"importo": importo},
            )

        desc = descrizione or f"Trasferimento deposito→corrente (evento «{getattr(evento, 'titolo', evento.pk)}»)"
        modifica_crediti(personaggio, -importo, desc, conto=CONTO_DEPOSITO, evento=evento)
        modifica_crediti(personaggio, importo, desc, conto=CONTO_CORRENTE, evento=evento)
        return importo


def economia_summary(personaggio, *, evento=None, user=None) -> dict[str, Any]:
    campagna = getattr(personaggio, "campagna", None)
    cfg = get_economia_config(campagna)
    duale = modulo_conto_deposito_attivo(personaggio, user=user)
    corrente = saldo_corrente(personaggio)
    deposito = saldo_deposito(personaggio)
    summary: dict[str, Any] = {
        "modulo_attivo": duale,
        "crediti_corrente": str(corrente),
        "crediti_deposito": str(deposito),
        "crediti": str(saldo_spendibile(personaggio, user=user)),
        "config": {
            "frazione_trasferimento_stipendio": cfg["frazione_trasferimento_stipendio"],
            "fattore_valore_deposito": cfg["fattore_valore_deposito"],
            "categorie_spesa_deposito": list(cfg["categorie_spesa_deposito"]),
        },
        "trasferimento": None,
    }
    if evento is not None and duale:
        tetto = tetto_trasferimento_deposito(personaggio, evento, campagna=campagna)
        gia = trasferimento_gia_effettuato(personaggio, evento)
        summary["trasferimento"] = {
            "evento_id": str(evento.pk),
            "stipendio_evento": str(stipendio_evento(personaggio, evento)),
            "tetto": str(tetto),
            "gia_effettuato": gia,
            "importo_max": str(min(tetto, deposito) if not gia else Decimal("0.00")),
        }
    return summary


def normalize_conto(value, default: str = CONTO_CORRENTE) -> str:
    if value is None or value == "":
        return default
    v = str(value).strip().upper()
    # alias legacy
    if v in ("RISERVA", "DEPOSIT", "DEPOSITO"):
        return CONTO_DEPOSITO
    if v in ("CORRENTE", "CURRENT", "LIBERI", "CREDITI"):
        return CONTO_CORRENTE
    if v not in CONTI_VALIDI:
        raise ValidationError(f"Conto non valido: {value}")
    return v
