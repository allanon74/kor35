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
    NegozioMercanteBundle,
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


def _registra_movimento(
    negozio, *, tipo, importo, personaggio=None, voce=None, stock=None, bundle=None, nota=""
):
    NegozioMercanteMovimento.objects.create(
        negozio=negozio,
        personaggio=personaggio,
        tipo=tipo,
        importo=Decimal(importo),
        saldo_dopo=negozio.saldo_crediti,
        nota=nota[:255],
        riferimento_voce=voce,
        riferimento_stock=stock,
        riferimento_bundle=bundle,
    )


def _aggiorna_saldo(
    negozio, delta: Decimal, *, tipo, personaggio=None, voce=None, stock=None, bundle=None, nota=""
):
    negozio.saldo_crediti = (negozio.saldo_crediti or Decimal("0")) + delta
    negozio.save(update_fields=["saldo_crediti", "updated_at"])
    _registra_movimento(
        negozio,
        tipo=tipo,
        importo=delta,
        personaggio=personaggio,
        voce=voce,
        stock=stock,
        bundle=bundle,
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


def _e_innesto_corporeo(*, infusione=None, oggetto=None) -> bool:
    """Innesto (ATE) vs mutazione: tipo oggetto vince sulla classificazione infusione."""
    if oggetto is not None and oggetto.tipo_oggetto == TIPO_OGGETTO_INNESTO:
        return True
    if infusione is None:
        return False
    from personaggi.services import GestioneCraftingService

    return GestioneCraftingService._classifica_risultato_infusione(infusione) == "INNESTO"


def _voce_richiede_montaggio(voce: NegozioMercanteVoce) -> bool:
    if voce.tipo_voce == VOCE_OGGETTO:
        return _oggetto_e_aumento(voce.oggetto)
    if voce.tipo_voce == VOCE_INFUSIONE and voce.infusione_id:
        return voce.infusione.tipo_risultato == SCELTA_RISULTATO_AUMENTO
    return False


def _voce_permette_quantita_multipla(voce: NegozioMercanteVoce) -> bool:
    if voce.tipo_voce in (VOCE_OGGETTO_BASE, VOCE_CONSUMABILE):
        return True
    if voce.tipo_voce == VOCE_INFUSIONE and _voce_consegna_istanza(voce):
        # Aumenti corporei: una sola unità (montaggio unico).
        return voce.infusione.tipo_risultato != SCELTA_RISULTATO_AUMENTO
    return False


def _nome_voce_catalogo(voce: NegozioMercanteVoce) -> str:
    ent = _voce_entita(voce)
    return getattr(ent, "nome", None) or voce.consumabile_nome or "Articolo"


def _assert_stock_voce(voce: NegozioMercanteVoce, qty: int) -> None:
    if qty < 1:
        raise ValidationError("Quantità non valida.")
    if voce.quantita_residua is not None and voce.quantita_residua < qty:
        raise ValidationError(MSG_ESAURITO_LISTINO)


def _decrementa_stock_voce(voce: NegozioMercanteVoce, qty: int) -> None:
    _assert_stock_voce(voce, qty)
    if voce.quantita_residua is None:
        return
    voce.quantita_residua -= qty
    voce.save(update_fields=["quantita_residua", "updated_at"])


def _motivo_voce_non_acquistabile(voce: NegozioMercanteVoce, personaggio, *, qty: int = 1) -> str | None:
    """Messaggio se la voce non può essere consegnata (qty unità); None se ok."""
    if not voce.attivo:
        return MSG_NON_DISPONIBILE_LISTINO
    if voce.quantita_residua is not None and voce.quantita_residua < qty:
        return MSG_ESAURITO_LISTINO
    if qty > 1 and not _voce_permette_quantita_multipla(voce):
        return "Questa voce non supporta quantità multiple."

    if voce.tipo_voce == VOCE_OGGETTO:
        if not voce.oggetto_id:
            return MSG_NON_DISPONIBILE_LISTINO
        if _inventario_corrente_pk(voce.oggetto) != voce.negozio.inventario_id:
            return MSG_NON_DISPONIBILE_LISTINO
        if qty != 1:
            return "Gli oggetti unici si acquistano uno alla volta."
        return None

    if voce.tipo_voce == VOCE_ABILITA:
        if personaggio.abilita_possedute.filter(pk=voce.abilita_id).exists():
            return "Abilità già posseduta."
        return None

    if voce.tipo_voce in (VOCE_INFUSIONE, VOCE_TESSITURA, VOCE_CERIMONIALE):
        if voce.tipo_voce == VOCE_INFUSIONE and _voce_consegna_istanza(voce):
            return None
        ent = _voce_entita(voce)
        ok_u, msg_u = personaggio.valida_acquisto_tecnica(ent)
        if not ok_u:
            return msg_u or "Tecnica non acquistabile."
        if voce.tipo_voce == VOCE_INFUSIONE:
            if personaggio.infusioni_possedute.filter(pk=ent.pk).exists():
                return "Infusione già posseduta."
        elif voce.tipo_voce == VOCE_TESSITURA:
            if personaggio.tessiture_possedute.filter(pk=ent.pk).exists():
                return "Tessitura già posseduta."
        else:
            if personaggio.cerimoniali_posseduti.filter(pk=ent.pk).exists():
                return "Cerimoniale già posseduto."
        return None

    if voce.tipo_voce != VOCE_CONSUMABILE:
        ent = _voce_entita(voce)
        if ent is None and voce.tipo_voce != VOCE_CONSUMABILE:
            return "Voce catalogo incompleta."
        if voce.tipo_voce != VOCE_CONSUMABILE and getattr(ent, "non_vendibile", False):
            return "Questo contenuto non è vendibile."
    return None


def _consegna_unita_voce(
    negozio: NegozioMercante,
    voce: NegozioMercanteVoce,
    personaggio,
    *,
    slot_corpo: str | None = None,
    destinatario=None,
):
    """Consegna una singola unità della voce. Ritorna eventuale entità creata."""
    from datetime import timedelta

    from personaggi.services import GestioneCraftingService, GestioneOggettiService

    destinatario = destinatario or personaggio
    richiede_montaggio = _voce_richiede_montaggio(voce)
    consegna_istanza = _voce_consegna_istanza(voce)
    entita_creata = None

    if voce.tipo_voce == VOCE_OGGETTO_BASE:
        ob = voce.oggetto_base
        _assert_voce_globally_vendibile(ob)
        entita_creata = GestioneCraftingService.crea_istanza_da_oggetto_base(
            ob, personaggio, costo_acquisto=int(voce.prezzo_crediti)
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
    return entita_creata


def _prepara_montaggio_voce(voce, personaggio, *, slot_corpo, destinatario_id):
    """Valida e ritorna (destinatario, slot) se la voce richiede montaggio."""
    if not _voce_richiede_montaggio(voce):
        return personaggio, None
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
    return destinatario, slot_corpo


def _righe_bundle_qs(bundle: NegozioMercanteBundle):
    return bundle.righe.select_related(
        "voce",
        "voce__negozio",
        "voce__oggetto_base",
        "voce__oggetto",
        "voce__oggetto__infusione_generatrice",
        "voce__abilita",
        "voce__infusione",
        "voce__tessitura",
        "voce__cerimoniale",
        "voce__consumabile_tessitura",
    ).order_by("ordine", "created_at")


def _bundle_disponibilita(bundle: NegozioMercanteBundle, personaggio) -> tuple[bool, str, int | None]:
    """
    Ritorna (acquistabile, messaggio, quantita_effettiva).
    quantita_effettiva = minimo stock componenti limitati (None = illimitato).
    """
    righe = list(_righe_bundle_qs(bundle))
    if not righe:
        return False, "Bundle vuoto.", 0
    qty_eff = None
    for riga in righe:
        voce = riga.voce
        if voce.negozio_id != bundle.negozio_id:
            return False, "Bundle non valido.", 0
        if not voce.attivo:
            return False, MSG_NON_DISPONIBILE_LISTINO, 0
        motivo = _motivo_voce_non_acquistabile(voce, personaggio, qty=riga.quantita)
        if motivo:
            return False, motivo, 0
        if voce.quantita_residua is not None:
            disponibili = voce.quantita_residua // max(1, riga.quantita)
            qty_eff = disponibili if qty_eff is None else min(qty_eff, disponibili)
    if qty_eff is not None and qty_eff <= 0:
        return False, MSG_ESAURITO_LISTINO, 0
    return True, "", qty_eff


def serializza_bundle_listino(bundle: NegozioMercanteBundle, personaggio, *, prezzi_ctx=None) -> dict:
    from personaggi.economia_crediti import CATEGORIA_NEGOZIO, prezzi_duali

    campagna = getattr(personaggio, "campagna", None)
    if prezzi_ctx:
        duali = prezzi_duali(
            bundle.prezzo_crediti,
            campagna,
            categoria=CATEGORIA_NEGOZIO,
            cfg=prezzi_ctx.get("cfg"),
            deposito_ammesso=prezzi_ctx.get("deposito_ammesso"),
        )
    else:
        duali = prezzi_duali(
            bundle.prezzo_crediti,
            campagna,
            categoria=CATEGORIA_NEGOZIO,
        )
    acquistabile, msg, qty_eff = _bundle_disponibilita(bundle, personaggio)
    componenti = []
    montaggio_count = 0
    montaggio_meta = None
    for riga in _righe_bundle_qs(bundle):
        voce = riga.voce
        componenti.append(
            {
                "voce_id": str(voce.id),
                "nome": _nome_voce_catalogo(voce),
                "tipo_voce": voce.tipo_voce,
                "quantita": riga.quantita,
            }
        )
        if _voce_richiede_montaggio(voce):
            montaggio_count += riga.quantita
            if montaggio_meta is None:
                montaggio_meta = {}
                if voce.tipo_voce == VOCE_OGGETTO:
                    _applica_avvisi_montaggio_listino(
                        montaggio_meta, personaggio, oggetto=voce.oggetto
                    )
                else:
                    _applica_avvisi_montaggio_listino(
                        montaggio_meta, personaggio, infusione=voce.infusione
                    )
    richiede_montaggio = montaggio_count == 1
    payload = {
        "id": str(bundle.id),
        "tipo": "bundle",
        "tipo_voce": "BND",
        "nome": bundle.nome,
        "descrizione": bundle.descrizione or "",
        "prezzo_crediti": bundle.prezzo_crediti,
        "prezzo_corrente": duali["prezzo_corrente"],
        "prezzo_deposito": duali["prezzo_deposito"],
        "deposito_ammesso": duali["deposito_ammesso"],
        "quantita_residua": qty_eff,
        "acquistabile": acquistabile and (montaggio_count <= 1),
        "messaggio_usabilita": msg
        if montaggio_count <= 1
        else "Il pacchetto contiene più innesti/mutazioni: non acquistabile insieme.",
        "componenti": componenti,
        "richiede_montaggio": richiede_montaggio,
        "consegna_istanza": False,
    }
    if richiede_montaggio and montaggio_meta:
        for key in (
            "infusione_id",
            "tipo_risultato",
            "slot_corpo_permessi",
            "slot_disponibili",
            "richiede_ate",
        ):
            if key in montaggio_meta:
                payload[key] = montaggio_meta[key]
        payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
            payload.get("messaggio_usabilita"),
            montaggio_meta.get("messaggio_usabilita"),
        )
        if richiede_montaggio and not payload.get("slot_disponibili"):
            payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
                payload.get("messaggio_usabilita"), MSG_SLOT_PIENO_LISTINO
            )
    return payload


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


def _motivo_impedimento_montaggio_negozio(destinatario, *, infusione=None, oggetto=None):
    """
    Requisiti per montare un aumento già prodotto dal negozio.

    Mutazione: nessuno (basta lo slot libero).
    Innesto: Aura Tecnologica del destinatario > 0.
    Aura/mattoni della scheda tecnica restano requisiti di *acquisto ricetta*,
    non di montaggio istanza.
    """
    if not _e_innesto_corporeo(infusione=infusione, oggetto=oggetto):
        return None
    if destinatario.get_valore_aura_per_sigla("ATE") < 1:
        return (
            f"{destinatario.nome} non può sostenere innesti: "
            "serve almeno 1 punto di Aura Tecnologica."
        )
    return None


def _avviso_ate_listino(personaggio, *, infusione=None, oggetto=None) -> str:
    if not _e_innesto_corporeo(infusione=infusione, oggetto=oggetto):
        return ""
    if personaggio.get_valore_aura_per_sigla("ATE") >= 1:
        return ""
    return (
        "Tu non hai Aura Tecnologica (serve almeno 1 per gli innesti). "
        "Puoi montarlo su un altro personaggio."
    )


MSG_SLOT_PIENO_LISTINO = (
    "Nessuno slot libero sul tuo corpo: scegli un altro destinatario "
    "oppure libera una locazione."
)
MSG_NON_DISPONIBILE_LISTINO = "Non più disponibile."
MSG_ESAURITO_LISTINO = "Esaurito."
MSG_USATO_LISTINO = "Usato — rivendita"


def _unisci_messaggi_usabilita(*parti) -> str:
    """Concatena vincoli di usabilità senza duplicati e senza sovrascriverli."""
    visti = []
    for parte in parti:
        testo = (parte or "").strip()
        if not testo or testo in visti:
            continue
        visti.append(testo)
    return " ".join(visti)


def _applica_avvisi_montaggio_listino(
    payload, personaggio, *, infusione=None, oggetto=None
):
    precedente = payload.get("messaggio_usabilita") or ""
    meta = _meta_montaggio_listino(
        personaggio, infusione=infusione, oggetto=oggetto
    )
    meta_msg = meta.pop("messaggio_usabilita", "") or ""
    payload.update(meta)
    slot_msg = ""
    if payload.get("richiede_montaggio") and not payload.get("slot_disponibili"):
        slot_msg = MSG_SLOT_PIENO_LISTINO
    payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
        precedente, meta_msg, slot_msg
    )


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
    motivo = _motivo_impedimento_montaggio_negozio(
        destinatario, infusione=inf, oggetto=oggetto
    )
    if motivo:
        raise ValidationError(motivo)
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
    ate_msg = _avviso_ate_listino(personaggio, infusione=inf, oggetto=oggetto)
    meta = {
        "richiede_montaggio": True,
        "infusione_id": str(inf.id) if inf else None,
        "tipo_risultato": getattr(inf, "tipo_risultato", None),
        "slot_corpo_permessi": sorted(permessi) if permessi else [
            code for code, _label in SLOT_CORPO_CHOICES
        ],
        "slot_disponibili": slot_aumento_disponibili(
            personaggio, infusione=inf, oggetto=oggetto
        ),
        "richiede_ate": _e_innesto_corporeo(infusione=inf, oggetto=oggetto),
    }
    if ate_msg:
        meta["messaggio_usabilita"] = ate_msg
    return meta


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
            _applica_avvisi_montaggio_listino(
                payload, personaggio, infusione=voce.infusione
            )
        else:
            payload.update(_tecnica_listino_extra(personaggio, ent))
    elif voce.tipo_voce == VOCE_ABILITA:
        if personaggio.abilita_possedute.filter(pk=ent.pk).exists():
            payload["acquistabile"] = False
            payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
                payload.get("messaggio_usabilita"), "Abilità già posseduta."
            )
            payload["gia_posseduta"] = True
        else:
            payload["gia_posseduta"] = False
    elif voce.tipo_voce == VOCE_OGGETTO:
        _applica_avvisi_montaggio_listino(
            payload, personaggio, oggetto=voce.oggetto
        )
        if voce.oggetto_id and _inventario_corrente_pk(voce.oggetto) != voce.negozio.inventario_id:
            payload["acquistabile"] = False
            payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
                payload.get("messaggio_usabilita"), MSG_NON_DISPONIBILE_LISTINO
            )
    if voce.quantita_residua is not None and voce.quantita_residua <= 0:
        payload["acquistabile"] = False
        payload["messaggio_usabilita"] = _unisci_messaggi_usabilita(
            payload.get("messaggio_usabilita"), MSG_ESAURITO_LISTINO
        )
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
        "messaggio_usabilita": (
            MSG_USATO_LISTINO if stock.stato == STOCK_DISPONIBILE else ""
        ),
        "usato": True,
        "consegna_istanza": True,
        "richiede_montaggio": False,
    }
    if personaggio is not None:
        _applica_avvisi_montaggio_listino(
            payload, personaggio, oggetto=stock.oggetto
        )
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
        for voce in negozio.voci.filter(attivo=True, non_vendibile=False).select_related(
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
        for bundle in (
            NegozioMercanteBundle.objects.filter(negozio=negozio, attivo=True)
            .prefetch_related("righe__voce")
            .order_by("ordine", "created_at")
        ):
            if not bundle.righe.exists():
                continue
            voci.append(serializza_bundle_listino(bundle, personaggio, prezzi_ctx=prezzi_ctx))
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
            "oggetto__infusione_generatrice",
            "abilita",
            "infusione",
            "tessitura",
            "cerimoniale",
            "consumabile_tessitura",
        )
        .get(pk=voce_id, negozio=negozio, attivo=True)
    )
    if voce.non_vendibile:
        raise ValidationError(
            "Questo articolo è vendibile solo all'interno di un pacchetto (bundle)."
        )

    destinatario, slot_eff = _prepara_montaggio_voce(
        voce, personaggio, slot_corpo=slot_corpo, destinatario_id=destinatario_id
    )
    richiede_montaggio = _voce_richiede_montaggio(voce)

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

    motivo = _motivo_voce_non_acquistabile(voce, personaggio, qty=1)
    if motivo:
        raise ValidationError(motivo)

    _decrementa_stock_voce(voce, 1)
    entita_creata = _consegna_unita_voce(
        negozio,
        voce,
        personaggio,
        slot_corpo=slot_eff,
        destinatario=destinatario,
    )

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
        result["slot_corpo"] = slot_eff
    if entita_creata and hasattr(entita_creata, "id"):
        result["oggetto_id"] = entita_creata.id
    return result


@transaction.atomic
def acquista_bundle(
    negozio: NegozioMercante,
    personaggio,
    bundle_id,
    *,
    slot_corpo: str | None = None,
    conto: str = "CORRENTE",
    destinatario_id=None,
) -> dict:
    """Acquista un bundle: scala stock delle componenti e consegna tutto atomicamente."""
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

    conto = normalize_conto(conto)
    bundle = (
        NegozioMercanteBundle.objects.select_for_update(of=("self",))
        .select_related("negozio")
        .get(pk=bundle_id, negozio=negozio, attivo=True)
    )
    righe = list(_righe_bundle_qs(bundle))
    if not righe:
        raise ValidationError("Bundle vuoto.")

    voce_ids = [r.voce_id for r in righe]
    locked = {
        v.id: v
        for v in NegozioMercanteVoce.objects.select_for_update(of=("self",))
        .select_related(
            "negozio",
            "oggetto_base",
            "oggetto",
            "oggetto__infusione_generatrice",
            "abilita",
            "infusione",
            "tessitura",
            "cerimoniale",
            "consumabile_tessitura",
        )
        .filter(pk__in=voce_ids, negozio=negozio)
    }
    if len(locked) != len(voce_ids):
        raise ValidationError("Una o più componenti del bundle non sono più disponibili.")

    montaggio_righe = []
    for riga in righe:
        voce = locked[riga.voce_id]
        if voce.negozio_id != negozio.id:
            raise ValidationError("Bundle non valido.")
        if not voce.attivo:
            raise ValidationError(MSG_NON_DISPONIBILE_LISTINO)
        if riga.quantita > 1 and not _voce_permette_quantita_multipla(voce):
            raise ValidationError(
                f"La voce «{_nome_voce_catalogo(voce)}» non supporta quantità multiple."
            )
        motivo = _motivo_voce_non_acquistabile(voce, personaggio, qty=riga.quantita)
        if motivo:
            raise ValidationError(motivo)
        if _voce_richiede_montaggio(voce):
            montaggio_righe.append((riga, voce))

    if len(montaggio_righe) > 1 or (
        len(montaggio_righe) == 1 and montaggio_righe[0][0].quantita != 1
    ):
        raise ValidationError(
            "Il pacchetto contiene più innesti/mutazioni: non acquistabile insieme."
        )

    destinatario = personaggio
    slot_eff = None
    if montaggio_righe:
        _riga_m, voce_m = montaggio_righe[0]
        destinatario, slot_eff = _prepara_montaggio_voce(
            voce_m, personaggio, slot_corpo=slot_corpo, destinatario_id=destinatario_id
        )

    prezzo = int(bundle.prezzo_crediti)
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

    for riga in righe:
        _decrementa_stock_voce(locked[riga.voce_id], riga.quantita)

    ultima_entita = None
    for riga in righe:
        voce = locked[riga.voce_id]
        for _ in range(riga.quantita):
            # Ricarica OGG dopo eventuale disattivazione (qty sempre 1).
            if voce.tipo_voce == VOCE_OGGETTO:
                voce.refresh_from_db()
            ultima_entita = _consegna_unita_voce(
                negozio,
                voce,
                personaggio,
                slot_corpo=slot_eff if _voce_richiede_montaggio(voce) else None,
                destinatario=destinatario if _voce_richiede_montaggio(voce) else personaggio,
            )

    pagato = addebita_bene(
        personaggio,
        prezzo,
        f"Acquisto bundle «{bundle.nome}» presso {negozio.nome}",
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
            tipo="incasso_bundle",
            personaggio=personaggio,
            bundle=bundle,
            nota=f"Bundle: {bundle.nome}",
        )

    personaggio.aggiungi_log(
        f"Acquisto bundle «{bundle.nome}» al negozio «{negozio.nome}» "
        f"({pagato} CR da {conto.lower()})."
    )
    result = {
        "status": "success",
        "prezzo": prezzo,
        "prezzo_pagato": str(pagato),
        "conto": conto,
        "bundle_id": str(bundle.id),
    }
    if montaggio_righe:
        result["montato_su"] = destinatario.id
        result["slot_corpo"] = slot_eff
    if ultima_entita and hasattr(ultima_entita, "id"):
        result["oggetto_id"] = ultima_entita.id
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
