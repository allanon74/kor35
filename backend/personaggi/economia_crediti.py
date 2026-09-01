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
from django.db.models import Q, Sum

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
CATEGORIA_MOD = "mod"
CATEGORIA_INNESTI = "innesti"
CATEGORIA_MUTAZIONI = "mutazioni"
CATEGORIE_SPESA_DEPOSITO_DEFAULT = (
    CATEGORIA_OGGETTO,
    CATEGORIA_MATERIA,
    CATEGORIA_CONSUMABILE,
    CATEGORIA_MOD,
    CATEGORIA_INNESTI,
    CATEGORIA_MUTAZIONI,
    CATEGORIA_NEGOZIO,
)
CATEGORIE_SPESA_DEPOSITO_VALIDE = set(CATEGORIE_SPESA_DEPOSITO_DEFAULT)

# Alias legacy economia → codice RegolaTransazioneCategoria
_CATEGORIA_A_REGOLA = {
    CATEGORIA_OGGETTO: "oggetti",
    "oggetti": "oggetti",
    CATEGORIA_MATERIA: "materia",
    CATEGORIA_CONSUMABILE: "consumabili",
    "consumabili": "consumabili",
    CATEGORIA_NEGOZIO: "negozio",
    "negozio": "negozio",
    CATEGORIA_MOD: "mod",
    CATEGORIA_INNESTI: "innesti",
    CATEGORIA_MUTAZIONI: "mutazioni",
    "infusioni": "infusioni",
    "tessiture": "tessiture",
    "cerimoniali": "cerimoniali",
    "crediti": "crediti",
}

# Codice regola → chiave API economia (per retrocompatibilità UI/config)
_REGOLA_A_CATEGORIA_ECO = {
    "oggetti": CATEGORIA_OGGETTO,
    "materia": CATEGORIA_MATERIA,
    "consumabili": CATEGORIA_CONSUMABILE,
    "negozio": CATEGORIA_NEGOZIO,
    "mod": CATEGORIA_MOD,
    "innesti": CATEGORIA_INNESTI,
    "mutazioni": CATEGORIA_MUTAZIONI,
}

DEFAULT_FRAZIONE_TRASFERIMENTO = Decimal("1.00")
DEFAULT_FATTORE_VALORE_DEPOSITO = Decimal("0.90")

DEFAULT_ECONOMIA_CONFIG: dict[str, Any] = {
    "frazione_trasferimento_stipendio": str(DEFAULT_FRAZIONE_TRASFERIMENTO),
    "fattore_valore_deposito": str(DEFAULT_FATTORE_VALORE_DEPOSITO),
    "categorie_spesa_deposito": list(CATEGORIE_SPESA_DEPOSITO_DEFAULT),
}


def _d2(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _invalidate_campagna_eco_cache(campagna) -> None:
    if campagna is None:
        return
    for attr in ("_economia_config_cache", "_regole_tx_ensured"):
        if hasattr(campagna, attr):
            delattr(campagna, attr)


def _invalidate_personaggio_saldi_cache(personaggio) -> None:
    if personaggio is None:
        return
    if hasattr(personaggio, "_eco_aggregati"):
        delattr(personaggio, "_eco_aggregati")


def normalizza_categoria_spesa(categoria: str) -> str:
    """Normalizza alias (oggetto→oggetti) al codice RegolaTransazioneCategoria."""
    key = str(categoria or "").strip().lower()
    return _CATEGORIA_A_REGOLA.get(key, key)


def _categorie_da_regole(campagna) -> list[str] | None:
    """
    Elenco chiavi economia (oggetto/materia/mod/…) da RegolaTransazioneCategoria.
    None solo se campagna assente (fallback JSON/default).
    Con campagna valorizzata: dopo ensure restituisce sempre una lista
    (anche vuota = nessuna categoria pagabile).
    """
    if campagna is None:
        return None
    from personaggi.regole_transazione import ensure_regole_transazione_campagna

    ensure_regole_transazione_campagna(campagna)
    from personaggi.models import RegolaTransazioneCategoria

    qs = RegolaTransazioneCategoria.objects.filter(
        campagna=campagna, pagabile_con_deposito=True
    ).values_list("codice", flat=True)
    out = []
    for codice in qs:
        eco = _REGOLA_A_CATEGORIA_ECO.get(codice)
        if eco and eco not in out:
            out.append(eco)
        elif not eco and codice in CATEGORIE_SPESA_DEPOSITO_VALIDE and codice not in out:
            out.append(codice)
    return out


def sync_regole_pagabile_da_categorie(campagna, categorie: Iterable[str]) -> None:
    """Allinea pagabile_con_deposito sulle regole dalle chiavi economia."""
    if campagna is None:
        return
    from personaggi.models import REGOLA_TX_CODICI_DEFAULT, RegolaTransazioneCategoria
    from personaggi.regole_transazione import ensure_regole_transazione_campagna

    ensure_regole_transazione_campagna(campagna)
    wanted = {normalizza_categoria_spesa(c) for c in (categorie or [])}
    from django.utils import timezone

    to_update = []
    now = timezone.now()
    for regola in RegolaTransazioneCategoria.objects.filter(campagna=campagna):
        if regola.codice not in REGOLA_TX_CODICI_DEFAULT:
            continue
        # Solo categorie mappate in economia API aggiornano il flag via questo path;
        # le altre (infusioni, …) restano gestite solo da Regole transazioni.
        if regola.codice not in _REGOLA_A_CATEGORIA_ECO and regola.codice not in CATEGORIE_SPESA_DEPOSITO_VALIDE:
            continue
        nuovo = regola.codice in wanted
        if regola.pagabile_con_deposito != nuovo:
            regola.pagabile_con_deposito = nuovo
            regola.updated_at = now
            to_update.append(regola)
    if to_update:
        RegolaTransazioneCategoria.objects.bulk_update(
            to_update, ["pagabile_con_deposito", "updated_at"]
        )
    _invalidate_campagna_eco_cache(campagna)


def get_economia_config(campagna=None, *, force_refresh: bool = False) -> dict[str, Any]:
    """Merge default + override JSON su Campagna.economia_config; categorie da regole se presenti."""
    if campagna is not None and not force_refresh:
        cached = getattr(campagna, "_economia_config_cache", None)
        if isinstance(cached, dict):
            return cached

    cfg = dict(DEFAULT_ECONOMIA_CONFIG)
    cfg["categorie_spesa_deposito"] = list(CATEGORIE_SPESA_DEPOSITO_DEFAULT)
    raw = getattr(campagna, "economia_config", None) if campagna is not None else None
    if isinstance(raw, dict):
        if "frazione_trasferimento_stipendio" in raw and raw["frazione_trasferimento_stipendio"] is not None:
            cfg["frazione_trasferimento_stipendio"] = str(_d2(raw["frazione_trasferimento_stipendio"]))
        if "fattore_valore_deposito" in raw and raw["fattore_valore_deposito"] is not None:
            fattore = _d2(raw["fattore_valore_deposito"])
            if fattore <= 0:
                fattore = DEFAULT_FATTORE_VALORE_DEPOSITO
            cfg["fattore_valore_deposito"] = str(fattore)
        # Categorie JSON usate solo senza campagna / prima delle regole.
        if campagna is None:
            cats = raw.get("categorie_spesa_deposito")
            if isinstance(cats, list):
                cleaned = []
                for c in cats:
                    key = str(c).strip().lower()
                    if key in CATEGORIE_SPESA_DEPOSITO_VALIDE and key not in cleaned:
                        cleaned.append(key)
                    else:
                        eco = _REGOLA_A_CATEGORIA_ECO.get(normalizza_categoria_spesa(key))
                        if eco and eco not in cleaned:
                            cleaned.append(eco)
                cfg["categorie_spesa_deposito"] = cleaned

    from_regole = _categorie_da_regole(campagna)
    if from_regole is not None:
        # Fonte di verità: flag sulle regole (anche lista vuota = nessuna categoria).
        cfg["categorie_spesa_deposito"] = from_regole

    if campagna is not None:
        campagna._economia_config_cache = cfg
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
            eco = key if key in CATEGORIE_SPESA_DEPOSITO_VALIDE else _REGOLA_A_CATEGORIA_ECO.get(
                normalizza_categoria_spesa(key)
            )
            if not eco or eco not in CATEGORIE_SPESA_DEPOSITO_VALIDE:
                raise ValidationError({"categorie_spesa_deposito": f"Categoria sconosciuta: {c}"})
            if eco not in cleaned:
                cleaned.append(eco)
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
    _invalidate_campagna_eco_cache(campagna)
    if "categorie_spesa_deposito" in cleaned:
        sync_regole_pagabile_da_categorie(campagna, cleaned["categorie_spesa_deposito"])
    return get_economia_config(campagna, force_refresh=True)


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


def aggregati_conti(personaggio) -> tuple[Decimal, Decimal]:
    """
    Saldi corrente/deposito in una sola query aggregate (cache sull'istanza PG).
    """
    cached = getattr(personaggio, "_eco_aggregati", None)
    if cached is not None:
        return cached
    agg = personaggio.movimenti_credito.aggregate(
        corrente=Sum("importo", filter=Q(conto=CONTO_CORRENTE)),
        deposito=Sum("importo", filter=Q(conto=CONTO_DEPOSITO)),
    )
    base = _d2(personaggio.tipologia.crediti_iniziali if personaggio.tipologia_id else 0)
    corrente = _d2(base + _d2(agg["corrente"]))
    deposito = _d2(agg["deposito"])
    personaggio._eco_aggregati = (corrente, deposito)
    return corrente, deposito


def saldo_conto(personaggio, conto: str) -> Decimal:
    conto = (conto or CONTO_CORRENTE).upper()
    if conto not in CONTI_VALIDI:
        raise ValidationError(f"Conto non valido: {conto}")
    corrente, deposito = aggregati_conti(personaggio)
    return corrente if conto == CONTO_CORRENTE else deposito


def saldo_corrente(personaggio) -> Decimal:
    return aggregati_conti(personaggio)[0]


def saldo_deposito(personaggio) -> Decimal:
    return aggregati_conti(personaggio)[1]


def saldo_spendibile(personaggio, *, user=None, duale: bool | None = None) -> Decimal:
    """Con modulo ON = solo corrente; OFF = corrente + deposito (monoconto)."""
    corrente, deposito = aggregati_conti(personaggio)
    if duale is None:
        duale = modulo_conto_deposito_attivo(personaggio, user=user)
    if duale:
        return corrente
    return _d2(corrente + deposito)


def prezzo_da_deposito(prezzo, fattore=None, campagna=None, *, cfg=None) -> Decimal:
    """
    Potere d'acquisto ridotto: prezzo_deposito = prezzo_corrente / fattore.
    Default fattore 0.90 → si paga di più dal deposito.
    """
    prezzo = _d2(prezzo)
    if prezzo <= 0:
        return Decimal("0.00")
    if fattore is None:
        cfg = cfg or get_economia_config(campagna)
        fattore = Decimal(cfg["fattore_valore_deposito"])
    else:
        fattore = _d2(fattore)
    if fattore <= 0:
        fattore = DEFAULT_FATTORE_VALORE_DEPOSITO
    # ceil-like via quantize half-up on division
    return _d2(prezzo / fattore)


def categoria_ammessa_deposito(
    categoria: str,
    campagna=None,
    *,
    cfg=None,
    regole_map=None,
) -> bool:
    """True se la categoria può essere pagata col deposito (flag su RegolaTransazioneCategoria)."""
    codice = normalizza_categoria_spesa(categoria)
    if not codice:
        return False
    if regole_map is not None:
        regola = regole_map.get(codice)
        if regola is not None:
            return bool(regola.pagabile_con_deposito)
    elif campagna is not None:
        from personaggi.regole_transazione import get_regole_map

        regola = get_regole_map(campagna).get(codice)
        if regola is not None:
            return bool(regola.pagabile_con_deposito)
    cfg = cfg or get_economia_config(campagna)
    eco_key = _REGOLA_A_CATEGORIA_ECO.get(codice, codice)
    return eco_key in set(cfg.get("categorie_spesa_deposito") or [])


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
    mov = CreditoMovimento.objects.create(**kwargs)
    _invalidate_personaggio_saldi_cache(personaggio)
    return mov


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
        disponibile = saldo_spendibile(personaggio, user=user, duale=False)
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


def prepara_addebito_bene(
    prezzo_listino,
    *,
    conto: str = CONTO_CORRENTE,
    categoria: str,
    campagna=None,
    personaggio=None,
    user=None,
    cfg=None,
) -> Decimal:
    """
    Valida conto/categoria e restituisce l'importo da addebitare (senza scrivere il ledger).
    Utile per check saldo pre-mutazione (es. stock negozio).
    """
    prezzo = _d2(prezzo_listino)
    conto = (conto or CONTO_CORRENTE).upper()
    campagna = campagna or (getattr(personaggio, "campagna", None) if personaggio else None)
    duale = (
        modulo_conto_deposito_attivo(personaggio, user=user)
        if personaggio is not None
        else campagna_ha_conto_deposito(campagna)
    )

    if conto == CONTO_DEPOSITO:
        if not duale:
            raise ValidationError("Il conto di deposito non è attivo in questa campagna.")
        cfg = cfg or get_economia_config(campagna)
        if not categoria_ammessa_deposito(categoria, campagna, cfg=cfg):
            raise ValidationError("Questa spesa non può essere pagata con il conto di deposito.")
        return prezzo_da_deposito(prezzo, campagna=campagna, cfg=cfg)

    return prezzo


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
    importo_gia_calcolato: Decimal | None = None,
    cfg=None,
) -> Decimal:
    """
    Addebita un acquisto beni. Ritorna l'importo effettivamente scalato.
    Con deposito applica fattore valore e verifica categoria.
    Se ``importo_gia_calcolato`` è passato (da prepara_addebito_bene), salta la ri-validazione.
    """
    prezzo = _d2(prezzo_listino)
    conto = (conto or CONTO_CORRENTE).upper()
    campagna = campagna or getattr(personaggio, "campagna", None)

    if importo_gia_calcolato is not None:
        da_pagare = _d2(importo_gia_calcolato)
    else:
        da_pagare = prepara_addebito_bene(
            prezzo,
            conto=conto,
            categoria=categoria,
            campagna=campagna,
            personaggio=personaggio,
            user=user,
            cfg=cfg,
        )

    if conto == CONTO_DEPOSITO:
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
        da_pagare,
        descrizione,
        conto=CONTO_CORRENTE,
        evento=evento,
        user=user,
        allow_monoconto_fallback=True,
    )
    return da_pagare


def prezzi_duali(
    prezzo_listino,
    campagna=None,
    *,
    categoria: str | None = None,
    cfg=None,
    deposito_ammesso: bool | None = None,
) -> dict[str, Any]:
    prezzo = _d2(prezzo_listino)
    cfg = cfg or get_economia_config(campagna)
    if deposito_ammesso is None:
        ammesso = categoria is None or categoria_ammessa_deposito(categoria, campagna, cfg=cfg)
    else:
        ammesso = bool(deposito_ammesso)
    out = {
        "prezzo_corrente": str(prezzo),
        "prezzo_deposito": None,
        "fattore_valore_deposito": cfg["fattore_valore_deposito"],
        "deposito_ammesso": bool(ammesso),
    }
    if ammesso:
        out["prezzo_deposito"] = str(prezzo_da_deposito(prezzo, campagna=campagna, cfg=cfg))
    return out


def stipendio_evento(personaggio, evento, ts=None) -> Decimal:
    from gestione_plot.evento_premi import calcola_crediti_premio_evento

    return _d2(calcola_crediti_premio_evento(evento, personaggio, ts=ts))


def tetto_trasferimento_deposito(
    personaggio,
    evento,
    campagna=None,
    ts=None,
    *,
    cfg=None,
    stipendio: Decimal | None = None,
) -> Decimal:
    campagna = campagna or getattr(personaggio, "campagna", None)
    cfg = cfg or get_economia_config(campagna)
    frazione = Decimal(cfg["frazione_trasferimento_stipendio"])
    if stipendio is None:
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
    evento=None,
    *,
    force: bool = False,
    user=None,
    descrizione: str | None = None,
) -> Decimal:
    """
    Sposta CR dal deposito al corrente.

    Giocatori (force=False): solo in evento attivo, 1× per evento, tetto frazione × stipendio.
    Staff (force=True): nessun evento, nessun tetto, non marca la quota evento del PG.
    """
    from gestione_plot.models import EventoTrasferimentoDeposito

    importo = _d2(importo)
    if importo <= 0:
        raise ValidationError("Importo trasferimento non valido.")

    if not force:
        if evento is None:
            raise ValidationError(
                "Trasferimento consentito solo durante un evento attivo a cui partecipi."
            )
        if not modulo_conto_deposito_attivo(personaggio, user=user):
            raise ValidationError("Il conto di deposito non è attivo.")

    with transaction.atomic():
        if not force:
            if trasferimento_gia_effettuato(personaggio, evento):
                raise ValidationError(
                    "Hai già effettuato il trasferimento deposito→corrente per questo evento."
                )
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
                raise ValidationError(
                    "Hai già effettuato il trasferimento deposito→corrente per questo evento."
                )

        if descrizione:
            desc = descrizione
        elif evento is not None:
            desc = (
                f"Trasferimento deposito→corrente "
                f"(evento «{getattr(evento, 'titolo', evento.pk)}»)"
            )
        else:
            desc = "Trasferimento staff deposito→corrente"
        modifica_crediti(personaggio, -importo, desc, conto=CONTO_DEPOSITO, evento=evento)
        modifica_crediti(personaggio, importo, desc, conto=CONTO_CORRENTE, evento=evento)
        return importo


def economia_summary(personaggio, *, evento=None, user=None) -> dict[str, Any]:
    campagna = getattr(personaggio, "campagna", None)
    cfg = get_economia_config(campagna)
    duale = modulo_conto_deposito_attivo(personaggio, user=user)
    corrente, deposito = aggregati_conti(personaggio)
    spendibile = corrente if duale else _d2(corrente + deposito)
    summary: dict[str, Any] = {
        "modulo_attivo": duale,
        "crediti_corrente": str(corrente),
        "crediti_deposito": str(deposito),
        "crediti": str(spendibile),
        "config": {
            "frazione_trasferimento_stipendio": cfg["frazione_trasferimento_stipendio"],
            "fattore_valore_deposito": cfg["fattore_valore_deposito"],
            "categorie_spesa_deposito": list(cfg["categorie_spesa_deposito"]),
        },
        "trasferimento": None,
    }
    if evento is not None and duale:
        stipendio = stipendio_evento(personaggio, evento)
        tetto = tetto_trasferimento_deposito(
            personaggio, evento, campagna=campagna, cfg=cfg, stipendio=stipendio
        )
        gia = trasferimento_gia_effettuato(personaggio, evento)
        summary["trasferimento"] = {
            "evento_id": str(evento.pk),
            "stipendio_evento": str(stipendio),
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
