"""
Acquisti, vendite e listino negozi mercante.
"""
from __future__ import annotations

import random
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from personaggi.negozio_mercante_apertura import negozio_e_aperto
from personaggi.negozio_mercante_models import (
    STOCK_DISPONIBILE,
    STOCK_VENDUTO,
    VOCE_ABILITA,
    VOCE_CERIMONIALE,
    VOCE_CONSUMABILE,
    VOCE_INFUSIONE,
    VOCE_OGGETTO,
    VOCE_OGGETTO_BASE,
    VOCE_TESSITURA,
    NegozioMercante,
    NegozioMercanteMovimento,
    NegozioMercanteStock,
    NegozioMercanteVoce,
    NEGOZIO_TIPO_CORPORATIVO,
)
from personaggi.models import (
    SCELTA_RISULTATO_AUMENTO,
    SLOT_CORPO_CHOICES,
    TIPO_OGGETTO_INNESTO,
    TIPO_OGGETTO_MUTAZIONE,
    ConsumabilePersonaggio,
    Oggetto,
    Personaggio,
    PersonaggioAbilita,
    PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO,
)


def _registra_movimento(negozio, *, tipo, importo, personaggio=None, voce=None, stock=None, nota=""):
    NegozioMercanteMovimento.objects.create(
        negozio=negozio,
        personaggio=personaggio,
        tipo=tipo,
        importo=Decimal(importo),
        saldo_dopo=negozio.saldo_crediti,
        nota=nota[:255],
        riferimento_voce=voce,
        riferimento_stock=stock,
    )


def _aggiorna_saldo(negozio, delta: Decimal, *, tipo, personaggio=None, voce=None, stock=None, nota=""):
    negozio.saldo_crediti = (negozio.saldo_crediti or Decimal("0")) + delta
    negozio.save(update_fields=["saldo_crediti", "updated_at"])
    _registra_movimento(
        negozio,
        tipo=tipo,
        importo=delta,
        personaggio=personaggio,
        voce=voce,
        stock=stock,
        nota=nota,
    )


def _config(negozio) -> dict:
    return negozio.get_config_economia()


def _inventario_corrente_pk(oggetto) -> int | None:
    inv = oggetto.inventario_corrente
    return inv.pk if inv else None


def valore_riferimento_oggetto(oggetto, config: dict) -> int:
    livello = max(0, int(getattr(oggetto, "livello", 0) or 0))
    base = int(config.get("cr_per_livello_oggetto") or 200)
    stored = int(getattr(oggetto, "costo_acquisto", 0) or 0)
    if stored > 0:
        return stored
    return max(base, livello * base) if livello else base


def _random_pct(config: dict, min_key: str, max_key: str) -> float:
    lo = float(config.get(min_key) or 0)
    hi = float(config.get(max_key) or lo)
    if hi < lo:
        lo, hi = hi, lo
    return random.uniform(lo, hi) / 100.0


def _voce_entita(voce: NegozioMercanteVoce):
    mapping = {
        VOCE_OGGETTO_BASE: voce.oggetto_base,
        VOCE_OGGETTO: voce.oggetto,
        VOCE_ABILITA: voce.abilita,
        VOCE_INFUSIONE: voce.infusione,
        VOCE_TESSITURA: voce.tessitura,
        VOCE_CERIMONIALE: voce.cerimoniale,
    }
    return mapping.get(voce.tipo_voce)


def _assert_voce_globally_vendibile(entita) -> None:
    if entita is None:
        raise ValidationError("Voce catalogo incompleta.")
    if getattr(entita, "non_vendibile", False):
        raise ValidationError("Questo contenuto non è vendibile.")


def _tecnica_listino_extra(personaggio, tecnica) -> dict:
    from personaggi.models import Infusione, Tessitura, Cerimoniale

    if not isinstance(tecnica, (Infusione, Tessitura, Cerimoniale)):
        return {}
    ok, msg = personaggio.valida_acquisto_tecnica(tecnica)
    gia = False
    if isinstance(tecnica, Infusione):
        gia = personaggio.infusioni_possedute.filter(pk=tecnica.pk).exists()
    elif isinstance(tecnica, Tessitura):
        gia = personaggio.tessiture_possedute.filter(pk=tecnica.pk).exists()
    else:
        gia = personaggio.cerimoniali_posseduti.filter(pk=tecnica.pk).exists()
    return {
        "acquistabile": ok and not gia,
        "messaggio_usabilita": msg if not ok else ("" if not gia else "Già posseduta."),
        "gia_posseduta": gia,
    }


def _slot_permessi_codes(infusione) -> set[str] | None:
    if not infusione or not getattr(infusione, "slot_corpo_permessi", None):
        return None
    permessi = {
        s.strip()
        for s in infusione.slot_corpo_permessi.split(",")
        if s.strip()
    }
    return permessi or None


def _voce_consegna_istanza(voce: NegozioMercanteVoce) -> bool:
    if voce.tipo_voce != VOCE_INFUSIONE or voce.infusione_id is None:
        return False
    if voce.consegna_istanza:
        return True
    return voce.infusione.tipo_risultato == SCELTA_RISULTATO_AUMENTO


def _oggetto_e_aumento(oggetto) -> bool:
    return bool(oggetto) and oggetto.tipo_oggetto in (
        TIPO_OGGETTO_INNESTO,
        TIPO_OGGETTO_MUTAZIONE,
    )


def _voce_richiede_montaggio(voce: NegozioMercanteVoce) -> bool:
    if voce.tipo_voce == VOCE_OGGETTO:
        return _oggetto_e_aumento(voce.oggetto)
    if voce.tipo_voce == VOCE_INFUSIONE and voce.infusione_id:
        return voce.infusione.tipo_risultato == SCELTA_RISULTATO_AUMENTO
    return False


def slot_aumento_disponibili(personaggio, *, infusione=None, oggetto=None) -> list:
    """Slot corpo liberi sul personaggio, eventualmente filtrati dall'infusione."""
    inf = infusione
    if oggetto is not None:
        if not _oggetto_e_aumento(oggetto) and not (
            inf and getattr(inf, "tipo_risultato", None) == SCELTA_RISULTATO_AUMENTO
        ):
            return []
        inf = inf or oggetto.infusione_generatrice
    elif inf is None or inf.tipo_risultato != SCELTA_RISULTATO_AUMENTO:
        return []
    permessi = _slot_permessi_codes(inf)
    liberi = []
    for code, label in SLOT_CORPO_CHOICES:
        if permessi and code not in permessi:
            continue
        occupante = Oggetto.objects.filter(
            tracciamento_inventario__inventario=personaggio,
            tracciamento_inventario__data_fine__isnull=True,
            slot_corpo=code,
            is_equipaggiato=True,
        ).exists()
        if not occupante:
            liberi.append({"code": code, "label": label})
    return liberi


def _risolve_destinatario_montaggio(acquirente, destinatario_id):
    if not destinatario_id or str(destinatario_id) == str(acquirente.id):
        return acquirente
    try:
        dest = Personaggio.objects.get(pk=destinatario_id)
    except (Personaggio.DoesNotExist, ValueError, TypeError) as exc:
        raise ValidationError("Destinatario del montaggio non trovato.") from exc
    if dest.eliminato_at:
        raise ValidationError("Il destinatario non è più disponibile.")
    if dest.campagna_id != acquirente.campagna_id:
        raise ValidationError("Il destinatario deve appartenere alla stessa campagna.")
    return dest


def _monta_aumento_o_annulla(destinatario, oggetto, slot_corpo):
    """
    Installa innesto/mutazione sul destinatario.
    Qualsiasi fallimento alza ValidationError: in transazione atomica
    l'acquisto intero viene annullato.
    """
    from personaggi.services import GestioneOggettiService

    if not slot_corpo:
        raise ValidationError(
            "Per innesti e mutazioni indica lo slot corpo su cui montare l'aumento."
        )
    inf = oggetto.infusione_generatrice
    if inf and not GestioneOggettiService.verifica_requisiti_supporto_innesto(
        destinatario, inf
    ):
        raise ValidationError(
            f"{destinatario.nome} non può sostenere questo aumento corporeo."
        )
    if _inventario_corrente_pk(oggetto) != destinatario.id:
        oggetto.sposta_in_inventario(destinatario)
    GestioneOggettiService.installa_innesto(destinatario, oggetto, slot_corpo)


def _meta_montaggio_listino(personaggio, *, infusione=None, oggetto=None) -> dict:
    inf = infusione or (oggetto.infusione_generatrice if oggetto else None)
    richiede = _oggetto_e_aumento(oggetto) or (
        inf is not None and inf.tipo_risultato == SCELTA_RISULTATO_AUMENTO
    )
    if not richiede:
        return {
            "richiede_montaggio": False,
            "infusione_id": str(inf.id) if inf else None,
            "tipo_risultato": getattr(inf, "tipo_risultato", None),
        }
    permessi = _slot_permessi_codes(inf)
    return {
        "richiede_montaggio": True,
        "infusione_id": str(inf.id) if inf else None,
        "tipo_risultato": getattr(inf, "tipo_risultato", None),
        "slot_corpo_permessi": sorted(permessi) if permessi else [
            code for code, _label in SLOT_CORPO_CHOICES
        ],
        "slot_disponibili": slot_aumento_disponibili(
            personaggio, infusione=inf, oggetto=oggetto
        ),
    }


def serializza_voce_listino(voce: NegozioMercanteVoce, personaggio, *, prezzi_ctx=None) -> dict:
    from personaggi.economia_crediti import CATEGORIA_NEGOZIO, prezzi_duali

    ent = _voce_entita(voce)
    nome = getattr(ent, "nome", voce.consumabile_nome or "Consumabile")
    campagna = getattr(personaggio, "campagna", None)
    if prezzi_ctx:
        duali = prezzi_duali(
            voce.prezzo_crediti,
            campagna,
            categoria=CATEGORIA_NEGOZIO,
            cfg=prezzi_ctx.get("cfg"),
            deposito_ammesso=prezzi_ctx.get("deposito_ammesso"),
        )
    else:
        duali = prezzi_duali(
            voce.prezzo_crediti,
            campagna,
            categoria=CATEGORIA_NEGOZIO,
        )
    consegna_istanza = _voce_consegna_istanza(voce)
    payload = {
        "id": str(voce.id),
        "tipo": "voce",
        "tipo_voce": voce.tipo_voce,
        "nome": nome,
        "prezzo_crediti": voce.prezzo_crediti,
        "prezzo_corrente": duali["prezzo_corrente"],
        "prezzo_deposito": duali["prezzo_deposito"],
        "deposito_ammesso": duali["deposito_ammesso"],
        "quantita_residua": voce.quantita_residua,
        "acquistabile": True,
        "messaggio_usabilita": "",
        "consegna_istanza": consegna_istanza,
        "richiede_montaggio": False,
    }
    if voce.tipo_voce in (VOCE_INFUSIONE, VOCE_TESSITURA, VOCE_CERIMONIALE):
        if voce.tipo_voce == VOCE_INFUSIONE and consegna_istanza:
            payload.update(
                _meta_montaggio_listino(personaggio, infusione=voce.infusione)
            )
            if payload.get("richiede_montaggio") and not payload.get("slot_disponibili"):
                payload["messaggio_usabilita"] = (
                    "Nessuno slot libero sul tuo corpo: scegli un altro destinatario "
                    "oppure libera una locazione."
                )
        else:
            payload.update(_tecnica_listino_extra(personaggio, ent))
    elif voce.tipo_voce == VOCE_ABILITA:
        if personaggio.abilita_possedute.filter(pk=ent.pk).exists():
            payload["acquistabile"] = False
            payload["messaggio_usabilita"] = "Abilità già posseduta."
            payload["gia_posseduta"] = True
        else:
            payload["gia_posseduta"] = False
    elif voce.tipo_voce == VOCE_OGGETTO:
        if voce.oggetto_id and _inventario_corrente_pk(voce.oggetto) != voce.negozio.inventario_id:
            payload["acquistabile"] = False
            payload["messaggio_usabilita"] = "Non più disponibile."
        payload.update(_meta_montaggio_listino(personaggio, oggetto=voce.oggetto))
    elif voce.quantita_residua is not None and voce.quantita_residua <= 0:
        payload["acquistabile"] = False
        payload["messaggio_usabilita"] = "Esaurito."
    return payload


def serializza_stock_listino(stock: NegozioMercanteStock, personaggio=None, *, prezzi_ctx=None) -> dict:
    from personaggi.economia_crediti import CATEGORIA_NEGOZIO, prezzi_duali

    campagna = getattr(personaggio, "campagna", None) if personaggio else None
    if prezzi_ctx:
        duali = prezzi_duali(
            stock.prezzo_rivendita,
            campagna,
            categoria=CATEGORIA_NEGOZIO,
            cfg=prezzi_ctx.get("cfg"),
            deposito_ammesso=prezzi_ctx.get("deposito_ammesso"),
        )
    else:
        duali = prezzi_duali(stock.prezzo_rivendita, campagna, categoria=CATEGORIA_NEGOZIO)
    payload = {
        "id": str(stock.id),
        "tipo": "stock",
        "tipo_voce": VOCE_OGGETTO,
        "nome": stock.oggetto.nome,
        "prezzo_crediti": stock.prezzo_rivendita,
        "prezzo_corrente": duali["prezzo_corrente"],
        "prezzo_deposito": duali["prezzo_deposito"],
        "deposito_ammesso": duali["deposito_ammesso"],
        "acquistabile": stock.stato == STOCK_DISPONIBILE,
        "messaggio_usabilita": "Usato — rivendita" if stock.stato == STOCK_DISPONIBILE else "",
        "usato": True,
        "consegna_istanza": True,
        "richiede_montaggio": False,
    }
    if personaggio is not None:
        payload.update(_meta_montaggio_listino(personaggio, oggetto=stock.oggetto))
    return payload


def build_listino(negozio: NegozioMercante, personaggio) -> dict:
    from personaggi.economia_crediti import (
        CATEGORIA_NEGOZIO,
        categoria_ammessa_deposito,
        get_economia_config,
        modulo_conto_deposito_attivo,
        saldo_corrente,
        saldo_deposito,
    )

    ok, msg = negozio_e_aperto(negozio, personaggio)
    campagna = getattr(personaggio, "campagna", None)
    cfg = get_economia_config(campagna) if campagna is not None else None
    prezzi_ctx = None
    if cfg is not None:
        prezzi_ctx = {
            "cfg": cfg,
            "deposito_ammesso": categoria_ammessa_deposito(
                CATEGORIA_NEGOZIO, campagna, cfg=cfg
            ),
        }
    voci = []
    if ok:
        for voce in negozio.voci.filter(attivo=True).select_related(
            "oggetto_base",
            "oggetto",
            "oggetto__infusione_generatrice",
            "abilita",
            "infusione",
            "tessitura",
            "cerimoniale",
            "consumabile_tessitura",
        ):
            try:
                ent = _voce_entita(voce)
                if voce.tipo_voce != VOCE_CONSUMABILE:
                    _assert_voce_globally_vendibile(ent)
            except ValidationError:
                continue
            voci.append(serializza_voce_listino(voce, personaggio, prezzi_ctx=prezzi_ctx))
        for stock in negozio.stock.filter(stato=STOCK_DISPONIBILE).select_related(
            "oggetto", "oggetto__infusione_generatrice"
        ):
            voci.append(serializza_stock_listino(stock, personaggio, prezzi_ctx=prezzi_ctx))
    return {
        "negozio_id": str(negozio.id),
        "nome": negozio.nome,
        "descrizione": negozio.descrizione,
        "descrizione_immersiva": negozio.descrizione_immersiva or negozio.descrizione or "",
        "tipo_negozio": negozio.tipo_negozio,
        "aperto": ok,
        "messaggio_accesso": msg,
        "saldo_crediti": float(negozio.saldo_crediti or 0),
        "voci": voci,
        "economia": {
            "modulo_attivo": modulo_conto_deposito_attivo(personaggio),
            "crediti_corrente": str(saldo_corrente(personaggio)),
            "crediti_deposito": str(saldo_deposito(personaggio)),
        },
    }


def slot_innesto_disponibili(personaggio, oggetto) -> list:
    """Alias storico: slot liberi per un oggetto innesto/mutazione già esistente."""
    return slot_aumento_disponibili(personaggio, oggetto=oggetto)


@transaction.atomic
def acquista_voce(
    negozio: NegozioMercante,
    personaggio,
    voce_id,
    *,
    slot_corpo: str | None = None,
    conto: str = "CORRENTE",
    destinatario_id=None,
) -> dict:
    from personaggi.economia_crediti import (
        CATEGORIA_NEGOZIO,
        CONTO_DEPOSITO,
        addebita_bene,
        get_economia_config,
        normalize_conto,
        prepara_addebito_bene,
        saldo_conto,
        saldo_spendibile,
    )
    from personaggi.services import GestioneCraftingService, GestioneOggettiService

    ok, msg = negozio_e_aperto(negozio, personaggio)
    if not ok:
        raise ValidationError(msg or "Negozio chiuso.")

    conto = normalize_conto(conto)
    voce = (
        NegozioMercanteVoce.objects.select_for_update(of=("self",))
        .select_related(
            "negozio",
            "oggetto_base",
            "oggetto",
            "abilita",
            "infusione",
            "tessitura",
            "cerimoniale",
            "consumabile_tessitura",
        )
        .get(pk=voce_id, negozio=negozio, attivo=True)
    )
    richiede_montaggio = _voce_richiede_montaggio(voce)
    consegna_istanza = _voce_consegna_istanza(voce)
    destinatario = personaggio
    if richiede_montaggio:
        destinatario = _risolve_destinatario_montaggio(personaggio, destinatario_id)
        if not slot_corpo:
            raise ValidationError(
                "Per innesti e mutazioni indica lo slot corpo e, se diverso da te, "
                "il destinatario del montaggio."
            )
        inf_ref = voce.infusione
        if voce.tipo_voce == VOCE_OGGETTO and voce.oggetto_id:
            inf_ref = voce.oggetto.infusione_generatrice
        liberi = {
            s["code"]
            for s in slot_aumento_disponibili(
                destinatario, infusione=inf_ref, oggetto=voce.oggetto
            )
        }
        if slot_corpo not in liberi:
            raise ValidationError(
                "Montaggio non possibile: slot occupato o non consentito. Acquisto annullato."
            )

    prezzo = int(voce.prezzo_crediti)
    campagna = getattr(personaggio, "campagna", None)
    cfg = get_economia_config(campagna)
    da_pagare = prepara_addebito_bene(
        prezzo,
        conto=conto,
        categoria=CATEGORIA_NEGOZIO,
        campagna=campagna,
        personaggio=personaggio,
        cfg=cfg,
    )
    if conto == CONTO_DEPOSITO:
        if saldo_conto(personaggio, CONTO_DEPOSITO) < da_pagare:
            raise ValidationError(f"Deposito insufficiente. Servono {da_pagare} CR.")
    elif saldo_spendibile(personaggio) < da_pagare:
        raise ValidationError(f"Crediti insufficienti. Servono {da_pagare} CR.")

    if voce.quantita_residua is not None:
        if voce.quantita_residua <= 0:
            raise ValidationError("Articolo esaurito.")
        voce.quantita_residua -= 1
        voce.save(update_fields=["quantita_residua", "updated_at"])

    entita_creata = None

    if voce.tipo_voce == VOCE_OGGETTO_BASE:
        ob = voce.oggetto_base
        _assert_voce_globally_vendibile(ob)
        entita_creata = GestioneCraftingService.crea_istanza_da_oggetto_base(
            ob, personaggio, costo_acquisto=prezzo
        )
    elif voce.tipo_voce == VOCE_OGGETTO:
        og = voce.oggetto
        _assert_voce_globally_vendibile(og)
        if _inventario_corrente_pk(og) != negozio.inventario_id:
            raise ValidationError("Oggetto non più in vendita.")
        if richiede_montaggio:
            _monta_aumento_o_annulla(destinatario, og, slot_corpo)
        else:
            og.sposta_in_inventario(personaggio)
        voce.oggetto = None
        voce.attivo = False
        voce.save(update_fields=["oggetto", "attivo", "updated_at"])
        entita_creata = og
    elif voce.tipo_voce == VOCE_ABILITA:
        ab = voce.abilita
        _assert_voce_globally_vendibile(ab)
        if personaggio.abilita_possedute.filter(pk=ab.pk).exists():
            raise ValidationError("Abilità già posseduta.")
        PersonaggioAbilita.objects.create(
            personaggio=personaggio,
            abilita=ab,
            origine=PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO,
        )
    elif voce.tipo_voce == VOCE_INFUSIONE:
        t = voce.infusione
        _assert_voce_globally_vendibile(t)
        if consegna_istanza:
            entita_creata = GestioneOggettiService.crea_oggetto_da_infusione(
                t, destinatario if richiede_montaggio else personaggio
            )
            if richiede_montaggio:
                _monta_aumento_o_annulla(destinatario, entita_creata, slot_corpo)
        else:
            ok_u, msg_u = personaggio.valida_acquisto_tecnica(t)
            if not ok_u:
                raise ValidationError(msg_u)
            if personaggio.infusioni_possedute.filter(pk=t.pk).exists():
                raise ValidationError("Infusione già posseduta.")
            personaggio.infusioni_possedute.add(t)
    elif voce.tipo_voce == VOCE_TESSITURA:
        t = voce.tessitura
        _assert_voce_globally_vendibile(t)
        ok_u, msg_u = personaggio.valida_acquisto_tecnica(t)
        if not ok_u:
            raise ValidationError(msg_u)
        if personaggio.tessiture_possedute.filter(pk=t.pk).exists():
            raise ValidationError("Tessitura già posseduta.")
        personaggio.tessiture_possedute.add(t)
    elif voce.tipo_voce == VOCE_CERIMONIALE:
        t = voce.cerimoniale
        _assert_voce_globally_vendibile(t)
        ok_u, msg_u = personaggio.valida_acquisto_tecnica(t)
        if not ok_u:
            raise ValidationError(msg_u)
        if personaggio.cerimoniali_posseduti.filter(pk=t.pk).exists():
            raise ValidationError("Cerimoniale già posseduto.")
        personaggio.cerimoniali_posseduti.add(t)
    elif voce.tipo_voce == VOCE_CONSUMABILE:
        from datetime import timedelta

        tess = voce.consumabile_tessitura
        nome = voce.consumabile_nome or (tess.nome if tess else "Consumabile")
        livello = max(1, int(voce.consumabile_livello or 1))
        ConsumabilePersonaggio.objects.create(
            personaggio=personaggio,
            tessitura=tess,
            nome=nome,
            descrizione=(tess.testo if tess else "") or "",
            formula=(tess.formula if tess else "") or "",
            utilizzi_rimanenti=livello,
            data_scadenza=timezone.now().date() + timedelta(days=30),
        )
    else:
        raise ValidationError("Tipo voce non supportato.")

    pagato = addebita_bene(
        personaggio,
        prezzo,
        f"Acquisto presso {negozio.nome}",
        conto=conto,
        categoria=CATEGORIA_NEGOZIO,
        campagna=getattr(personaggio, "campagna", None),
        importo_gia_calcolato=da_pagare,
        cfg=cfg,
    )
    if negozio.incassa_acquisti_catalogo:
        _aggiorna_saldo(
            negozio,
            Decimal(prezzo),
            tipo="incasso_acquisto",
            personaggio=personaggio,
            voce=voce,
            nota=f"Acquisto: {voce}",
        )

    personaggio.aggiungi_log(
        f"Acquisto al negozio «{negozio.nome}» ({pagato} CR da {conto.lower()})."
    )
    result = {
        "status": "success",
        "prezzo": prezzo,
        "prezzo_pagato": str(pagato),
        "conto": conto,
    }
    if richiede_montaggio:
        result["montato_su"] = destinatario.id
        result["slot_corpo"] = slot_corpo
    if entita_creata and hasattr(entita_creata, "id"):
        result["oggetto_id"] = entita_creata.id
    return result


@transaction.atomic
def acquista_stock(
    negozio,
    personaggio,
    stock_id,
    *,
    slot_corpo=None,
    conto: str = "CORRENTE",
    destinatario_id=None,
) -> dict:
    from personaggi.economia_crediti import (
        CATEGORIA_NEGOZIO,
        CONTO_DEPOSITO,
        addebita_bene,
        get_economia_config,
        normalize_conto,
        prepara_addebito_bene,
        saldo_conto,
        saldo_spendibile,
    )

    ok, msg = negozio_e_aperto(negozio, personaggio)
    if not ok:
        raise ValidationError(msg or "Negozio chiuso.")

    stock = (
        NegozioMercanteStock.objects.select_for_update(of=("self",))
        .select_related("oggetto", "negozio")
        .get(pk=stock_id, negozio=negozio, stato=STOCK_DISPONIBILE)
    )
    og = stock.oggetto
    richiede_montaggio = _oggetto_e_aumento(og)
    destinatario = personaggio
    if richiede_montaggio:
        destinatario = _risolve_destinatario_montaggio(personaggio, destinatario_id)
        if not slot_corpo:
            raise ValidationError(
                "Per innesti e mutazioni indica lo slot corpo e, se diverso da te, "
                "il destinatario del montaggio."
            )
        inf_ref = og.infusione_generatrice
        liberi = {
            s["code"]
            for s in slot_aumento_disponibili(destinatario, infusione=inf_ref, oggetto=og)
        }
        if slot_corpo not in liberi:
            raise ValidationError(
                "Montaggio non possibile: slot occupato o non consentito. Acquisto annullato."
            )

    prezzo = int(stock.prezzo_rivendita)
    conto = normalize_conto(conto)
    campagna = getattr(personaggio, "campagna", None)
    cfg = get_economia_config(campagna)
    da_pagare = prepara_addebito_bene(
        prezzo,
        conto=conto,
        categoria=CATEGORIA_NEGOZIO,
        campagna=campagna,
        personaggio=personaggio,
        cfg=cfg,
    )
    if conto == CONTO_DEPOSITO:
        if saldo_conto(personaggio, CONTO_DEPOSITO) < da_pagare:
            raise ValidationError(f"Deposito insufficiente. Servono {da_pagare} CR.")
    elif saldo_spendibile(personaggio) < da_pagare:
        raise ValidationError(f"Crediti insufficienti. Servono {da_pagare} CR.")

    if richiede_montaggio:
        _monta_aumento_o_annulla(destinatario, og, slot_corpo)
    else:
        og.sposta_in_inventario(personaggio)

    stock.stato = STOCK_VENDUTO
    stock.save(update_fields=["stato", "updated_at"])

    pagato = addebita_bene(
        personaggio,
        prezzo,
        f"Riacquisto usato da {negozio.nome}",
        conto=conto,
        categoria=CATEGORIA_NEGOZIO,
        campagna=getattr(personaggio, "campagna", None),
        importo_gia_calcolato=da_pagare,
        cfg=cfg,
    )
    _aggiorna_saldo(
        negozio,
        Decimal(prezzo),
        tipo="incasso_rivendita",
        personaggio=personaggio,
        stock=stock,
    )
    personaggio.aggiungi_log(
        f"Riacquisto al negozio «{negozio.nome}» ({pagato} CR da {conto.lower()})."
    )
    return {
        "status": "success",
        "prezzo": prezzo,
        "prezzo_pagato": str(pagato),
        "conto": conto,
        "oggetto_id": og.id,
        **(
            {"montato_su": destinatario.id, "slot_corpo": slot_corpo}
            if richiede_montaggio
            else {}
        ),
    }


def preview_vendita_oggetto(negozio, personaggio, oggetto_id) -> dict:
    """Stima fascia offerta (percentuali config) senza effettuare la vendita."""
    ok, msg = negozio_e_aperto(negozio, personaggio)
    if not ok:
        raise ValidationError(msg or "Negozio chiuso.")

    try:
        og = Oggetto.objects.select_related("infusione_generatrice").get(pk=oggetto_id)
    except Oggetto.DoesNotExist:
        raise ValidationError("Oggetto non trovato.")

    if _inventario_corrente_pk(og) != personaggio.id:
        raise ValidationError("Oggetto non nel tuo inventario.")
    if og.ospitato_su_id:
        raise ValidationError("Smonta l'oggetto prima di venderlo.")

    config = _config(negozio)
    val_ref = valore_riferimento_oggetto(og, config)
    lo = float(config.get("pct_vendita_min") or 20) / 100.0
    hi = float(config.get("pct_vendita_max") or 80) / 100.0
    if hi < lo:
        lo, hi = hi, lo
    offerta_min = max(1, int(round(val_ref * lo)))
    offerta_max = max(1, int(round(val_ref * hi)))
    saldo = negozio.saldo_crediti or Decimal("0")

    return {
        "oggetto_id": str(og.id),
        "nome": og.nome,
        "valore_riferimento": val_ref,
        "offerta_min": offerta_min,
        "offerta_max": offerta_max,
        "cassa_sufficiente": saldo >= offerta_max,
        "saldo_negozio": int(saldo),
    }


@transaction.atomic
def vendi_oggetto_a_negozio(negozio, personaggio, oggetto_id) -> dict:
    ok, msg = negozio_e_aperto(negozio, personaggio)
    if not ok:
        raise ValidationError(msg or "Negozio chiuso.")

    og = Oggetto.objects.select_related("infusione_generatrice").get(pk=oggetto_id)
    if _inventario_corrente_pk(og) != personaggio.id:
        raise ValidationError("Oggetto non nel tuo inventario.")
    if og.ospitato_su_id:
        raise ValidationError("Smonta l'oggetto prima di venderlo.")

    config = _config(negozio)
    val_ref = valore_riferimento_oggetto(og, config)
    pct = _random_pct(config, "pct_vendita_min", "pct_vendita_max")
    offerta = max(1, int(round(val_ref * pct)))

    if negozio.saldo_crediti < offerta:
        raise ValidationError("Il mercante non ha fondi sufficienti per l'acquisto.")

    pct_r = _random_pct(config, "pct_rivendita_min", "pct_rivendita_max")
    prezzo_riv = max(1, int(round(val_ref * pct_r)))

    og.sposta_in_inventario(negozio.inventario)
    stock = NegozioMercanteStock.objects.create(
        negozio=negozio,
        oggetto=og,
        prezzo_rivendita=prezzo_riv,
        valore_riferimento=val_ref,
        venduto_da=personaggio,
        stato=STOCK_DISPONIBILE,
    )

    personaggio.modifica_crediti(offerta, f"Vendita a {negozio.nome}", conto="DEPOSITO")
    _aggiorna_saldo(
        negozio,
        Decimal(-offerta),
        tipo="pagamento_vendita_pg",
        personaggio=personaggio,
        stock=stock,
        nota=f"Acquisto usato {og.nome}",
    )
    personaggio.aggiungi_log(f"Venduto «{og.nome}» al negozio «{negozio.nome}» per {offerta} CR.")
    return {
        "status": "success",
        "offerta_crediti": offerta,
        "prezzo_rivendita": prezzo_riv,
        "stock_id": str(stock.id),
    }


def negozi_corporativi_per_personaggio(personaggio, campagna=None):
    qs = NegozioMercante.objects.filter(
        attivo=True,
        tipo_negozio=NEGOZIO_TIPO_CORPORATIVO,
    )
    if campagna:
        qs = qs.filter(campagna=campagna)
    elif personaggio.campagna_id:
        qs = qs.filter(campagna_id=personaggio.campagna_id)
    out = []
    for n in qs:
        ok, _ = personaggio_puo_vedere_negozio_corporativo(n, personaggio)
        if ok:
            out.append(n)
    return out


def personaggio_puo_vedere_negozio_corporativo(negozio, personaggio):
    from personaggi.negozio_mercante_apertura import personaggio_puo_vedere_negozio_corporativo as _vis

    return _vis(negozio, personaggio)
