"""
Ciclo di vita dei contratti, slot, erogazioni e preset.
"""
from __future__ import annotations

import base64
import io
import logging
from datetime import timedelta
from decimal import Decimal

import qrcode
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from personaggi.campagna_moduli import (
    MODULO_CONTRATTI,
    personaggio_puo_accedere_modulo,
)
from personaggi.contratti_effetti import (
    INNESCO_ATTIVAZIONE,
    INNESCO_FINE_EVENTO,
    INNESCO_INIZIO_EVENTO,
    INNESCO_SCADENZA,
    INNESCO_STIPULA,
    calcola_post_tetto,
    codice_noto,
    q2,
    render_testo_contratto,
    risolvi_config,
)
from personaggi.contratti_models import (
    ADEMP_APPLICATO,
    ADEMP_DEBITO,
    ADEMP_IN_ATTESA,
    CHI_PROPONENTE,
    CHI_STAFF,
    DURATA_FINE_EVENTO,
    DURATA_GIORNI,
    EffettoModello,
    ModelloContratto,
    ParametroModello,
    STATI_OCCUPANO_SLOT,
    STATO_ANNULLATO,
    STATO_IN_ATTESA,
    STATO_RIFIUTATO,
    STATO_RISOLTO,
    STATO_SCADUTO,
    STATO_STIPULATO,
    VOCE_CLAUSOLA,
    VOCE_COMPENSO,
    Contratto,
    ContrattoAdempimento,
    ContrattoPost,
    ContrattoServizio,
    VoceModello,
)
from personaggi.economia_crediti import (
    CONTO_CORRENTE,
    CONTO_DEPOSITO,
    campagna_ha_conto_deposito,
    modifica_crediti,
    saldo_conto,
)
from personaggi.models import (
    CAMPAGNA_ROLE_HEAD_MASTER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_STAFFER,
    CampagnaUtente,
    Personaggio,
    QrCode,
    get_active_korp_membership,
)

logger = logging.getLogger(__name__)

AMBITO_DA_TIPO_PROPOSTA = {
    "INF": "creazione_infusione",
    "TES": "creazione_tessitura",
    "CER": "creazione_cerimoniale",
}


def user_is_staff_campagna(user, campagna) -> bool:
    if not user or not getattr(user, "is_authenticated", False) or not campagna:
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    return CampagnaUtente.objects.filter(
        campagna=campagna,
        user=user,
        attivo=True,
        ruolo__in=(CAMPAGNA_ROLE_STAFFER, CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER),
    ).exists()


def modulo_attivo_per(personaggio, user=None) -> bool:
    return personaggio_puo_accedere_modulo(personaggio, MODULO_CONTRATTI, user=user)


def _conto_movimento(personaggio) -> str:
    """Bonus e trasferimenti sul deposito se il modulo esiste; altrimenti sul corrente."""
    if campagna_ha_conto_deposito(getattr(personaggio, "campagna", None)):
        return CONTO_DEPOSITO
    return CONTO_CORRENTE


def slot_totali(personaggio) -> int:
    membership = get_active_korp_membership(personaggio)
    if not membership or not getattr(membership.carriera, "sottoscrive_contratti", False):
        return 0
    base = int(membership.carriera.slot_contratto_base or 0)
    bonus = int(membership.carica.bonus_slot_contratto or 0) if membership.carica_id else 0
    sct = int(personaggio.get_valore_statistica("SCT") or 0)
    return max(0, base + bonus + sct)


def slot_usati(personaggio) -> int:
    """Solo i contratti aperti come proponente. Quelli stipulati come cliente non occupano slot."""
    return Contratto.objects.filter(proponente=personaggio, stato__in=STATI_OCCUPANO_SLOT).count()


def slot_liberi(personaggio) -> int:
    return max(0, slot_totali(personaggio) - slot_usati(personaggio))


def cliente_ha_modello_stipulato(cliente, modello_id, escluso_pk=None) -> bool:
    """Il cliente può avere un solo contratto STIPULATO per ciascun modello."""
    qs = Contratto.objects.filter(cliente=cliente, modello_id=modello_id, stato=STATO_STIPULATO)
    if escluso_pk is not None:
        qs = qs.exclude(pk=escluso_pk)
    return qs.exists()


def riepilogo_ruoli(personaggio) -> dict:
    """Contratti STIPULATO del personaggio, divisi per ruolo. Le proposte in attesa non contano."""
    return {
        "attivi_cliente": Contratto.objects.filter(cliente=personaggio, stato=STATO_STIPULATO).count(),
        "attivi_offerente": Contratto.objects.filter(proponente=personaggio, stato=STATO_STIPULATO).count(),
    }


def tab_visibile(personaggio, user=None) -> bool:
    if not modulo_attivo_per(personaggio, user):
        return False
    membership = get_active_korp_membership(personaggio)
    if membership and getattr(membership.carriera, "sottoscrive_contratti", False):
        return True
    return Contratto.objects.filter(Q(proponente=personaggio) | Q(cliente=personaggio)).exclude(
        stato=STATO_ANNULLATO
    ).exists()


def marca_scaduti(contratto: Contratto | None = None) -> None:
    now = timezone.now()
    qs = Contratto.objects.filter(stato__in=STATI_OCCUPANO_SLOT, scadenza__lt=now)
    if contratto is not None:
        qs = qs.filter(pk=contratto.pk)
    for row in qs:
        era = row.stato
        row.stato = STATO_SCADUTO
        row.save(update_fields=["stato", "updated_at"])
        if era == STATO_STIPULATO:
            eroga_inneschi(row, INNESCO_SCADENZA, fonte_prefix=f"scadenza:{row.pk}")


def _effetti_snapshot(contratto: Contratto) -> list[dict]:
    return list((contratto.snapshot or {}).get("effetti") or [])


def _parametri_snapshot(contratto: Contratto) -> dict:
    return dict((contratto.snapshot or {}).get("parametri") or {})


def _render_testo(modello_testo: str, *, proponente, cliente, korp, scadenza, parametri, clausole, compensi) -> str:
    nome_cliente = cliente.nome if cliente is not None else "il sottoscrittore"
    scadenza_txt = timezone.localtime(scadenza).strftime("%d/%m/%Y %H:%M") if scadenza else ""
    return render_testo_contratto(
        modello_testo,
        proponente=getattr(proponente, "nome", "") or "",
        cliente=nome_cliente,
        korp=getattr(korp, "nome", "") or "",
        scadenza=scadenza_txt,
        parametri=parametri,
        clausole=clausole,
        compensi=compensi,
    )


def _testo_visibile(contratto: Contratto) -> str:
    """Ricalcola il testo dallo snapshot, così i {{param:chiave}} non restano in pagina."""
    snap = contratto.snapshot or {}
    sorgente = snap.get("testo_modello") or ""
    if not sorgente:
        return snap.get("testo") or ""
    clausole = [v.get("nome") or "" for v in snap.get("voci") or [] if v.get("tipo") != VOCE_COMPENSO]
    compensi = [v.get("nome") or "" for v in snap.get("voci") or [] if v.get("tipo") == VOCE_COMPENSO]
    scadenza_txt = ""
    if contratto.scadenza:
        scadenza_txt = timezone.localtime(contratto.scadenza).strftime("%d/%m/%Y %H:%M")
    return render_testo_contratto(
        sorgente,
        proponente=getattr(contratto.proponente, "nome", "") or "",
        cliente=contratto.cliente.nome if contratto.cliente_id else "il sottoscrittore",
        korp=snap.get("korp_nome") or "",
        scadenza=scadenza_txt,
        parametri=snap.get("parametri") or {},
        clausole=clausole,
        compensi=compensi,
    )


def _nome_parte(contratto: Contratto, ruolo: str):
    if ruolo == "PROPONENTE":
        return contratto.proponente
    if ruolo == "CLIENTE":
        return contratto.cliente
    if ruolo == "EREDE":
        erede_id = _parametri_snapshot(contratto).get("erede")
        if not erede_id:
            return contratto.cliente
        return Personaggio.objects.filter(pk=erede_id).first() or contratto.cliente
    return None


def _accredita(personaggio, importo, descrizione, evento=None):
    """Bonus sul deposito se il modulo è attivo, altrimenti sul corrente (stesso conto dei trasferimenti)."""
    importo = q2(importo)
    if personaggio is None or importo == 0:
        return
    modifica_crediti(personaggio, importo, descrizione, conto=_conto_movimento(personaggio), evento=evento)


def _trasferisci(da, a, importo, descrizione, *, se_scoperto: str, evento=None) -> tuple[Decimal, Decimal]:
    """Ritorna (versato, residuo_debito)."""
    importo = q2(importo)
    if importo <= 0 or da is None or a is None:
        return q2(0), q2(0)
    conto = _conto_movimento(da)
    saldo = saldo_conto(da, conto)
    if saldo >= importo:
        modifica_crediti(da, -importo, descrizione, conto=conto, evento=evento)
        modifica_crediti(a, importo, descrizione, conto=_conto_movimento(a), evento=evento)
        return importo, q2(0)
    if se_scoperto == "BLOCCA":
        raise ValidationError("Saldo insufficiente per sottoscrivere il contratto.")
    versato = q2(saldo) if saldo > 0 else q2(0)
    if versato > 0:
        modifica_crediti(da, -versato, descrizione, conto=conto, evento=evento)
        modifica_crediti(a, versato, descrizione, conto=_conto_movimento(a), evento=evento)
    return versato, q2(importo - versato)


def _gia_erogato(contratto, fonte: str) -> bool:
    return ContrattoAdempimento.objects.filter(contratto=contratto, fonte=fonte).exists()


def eroga_inneschi(contratto: Contratto, innesco: str, *, fonte_prefix: str, evento=None) -> None:
    if contratto.stato not in (STATO_STIPULATO, STATO_SCADUTO) and innesco != INNESCO_STIPULA:
        return
    if innesco == INNESCO_STIPULA and contratto.stato != STATO_STIPULATO:
        return
    for index, effetto in enumerate(_effetti_snapshot(contratto)):
        codice = effetto.get("codice")
        config = effetto.get("config") or {}
        if codice in ("credito_creato", "trasferimento") and (config.get("innesco") or INNESCO_STIPULA) != innesco:
            continue
        if codice not in ("credito_creato", "trasferimento"):
            continue
        fonte = f"{fonte_prefix}:{codice}:{index}"
        if _gia_erogato(contratto, fonte):
            continue
        importo = q2(config.get("importo") or 0)
        descrizione = f"Contratto «{contratto.snapshot.get('nome', '')}»"
        if codice == "credito_creato":
            beneficiario = config.get("beneficiario") or "ENTRAMBI"
            if beneficiario in ("CLIENTE", "ENTRAMBI") and contratto.cliente_id:
                _accredita(contratto.cliente, importo, descrizione, evento=evento)
            if beneficiario in ("PROPONENTE", "ENTRAMBI"):
                _accredita(contratto.proponente, importo, descrizione, evento=evento)
            ContrattoAdempimento.objects.create(
                contratto=contratto,
                codice_effetto=codice,
                fonte=fonte,
                evento=evento,
                stato=ADEMP_APPLICATO,
                dovuto=importo,
                versato=importo,
                importo_cliente=importo if beneficiario in ("CLIENTE", "ENTRAMBI") else 0,
                importo_proponente=importo if beneficiario in ("PROPONENTE", "ENTRAMBI") else 0,
                note=descrizione[:240],
            )
        else:
            da = _nome_parte(contratto, config.get("da") or "CLIENTE")
            a = _nome_parte(contratto, config.get("a") or "PROPONENTE")
            se_scoperto = config.get("se_scoperto") or ("BLOCCA" if innesco == INNESCO_STIPULA else "DEBITO")
            versato, debito = _trasferisci(
                da, a, importo, descrizione, se_scoperto=se_scoperto, evento=evento
            )
            ContrattoAdempimento.objects.create(
                contratto=contratto,
                codice_effetto=codice,
                fonte=fonte,
                evento=evento,
                stato=ADEMP_DEBITO if debito > 0 else ADEMP_APPLICATO,
                dovuto=importo,
                versato=versato,
                note=descrizione[:240],
                dettaglio={"debito": str(debito)},
            )


def _contratti_cliente_vivi(personaggio):
    now = timezone.now()
    return Contratto.objects.filter(
        cliente=personaggio,
        stato=STATO_STIPULATO,
        scadenza__gte=now,
    ).select_related("proponente", "cliente")


def on_task_reclamata(risoluzione) -> None:
    personaggio = risoluzione.personaggio
    if not modulo_attivo_per(personaggio):
        return
    crediti = q2(risoluzione.reward_crediti)
    if crediti <= 0:
        return
    fonte_base = f"task:{risoluzione.pk}"
    for contratto in _contratti_cliente_vivi(personaggio):
        for index, effetto in enumerate(_effetti_snapshot(contratto)):
            if effetto.get("codice") != "percentuale_task":
                continue
            fonte = f"{fonte_base}:{contratto.pk}:{index}"
            if _gia_erogato(contratto, fonte):
                continue
            config = effetto.get("config") or {}
            pct_c = q2(config.get("pct_cliente") or 0)
            pct_p = q2(config.get("pct_proponente") or 0)
            bonus_c = q2(crediti * pct_c / Decimal("100"))
            bonus_p = q2(crediti * pct_p / Decimal("100"))
            titolo = f"Contratto «{contratto.snapshot.get('nome', '')}» — task"
            if bonus_c > 0:
                _accredita(contratto.cliente, bonus_c, titolo)
            if bonus_p > 0:
                _accredita(contratto.proponente, bonus_p, titolo)
            ContrattoAdempimento.objects.create(
                contratto=contratto,
                codice_effetto="percentuale_task",
                fonte=fonte,
                stato=ADEMP_APPLICATO,
                dovuto=q2(bonus_c + bonus_p),
                versato=q2(bonus_c + bonus_p),
                importo_cliente=bonus_c,
                importo_proponente=bonus_p,
                note=titolo[:240],
            )


def piano_sconto(personaggio, ambito: str, costo_pieno, costo_corrente):
    """Calcola il pagamento dopo lo sconto contratto, senza scrivere movimenti."""
    pieno = q2(costo_pieno)
    corrente = q2(costo_corrente)
    if not modulo_attivo_per(personaggio) or pieno <= 0:
        return corrente, []
    sconto = q2(0)
    righe = []
    for contratto in _contratti_cliente_vivi(personaggio):
        for index, effetto in enumerate(_effetti_snapshot(contratto)):
            if effetto.get("codice") != "sconto_costo":
                continue
            config = effetto.get("config") or {}
            ambiti = config.get("ambiti") or []
            if ambito not in ambiti:
                continue
            pct_s = q2(config.get("pct_sconto_cliente") or 0)
            pct_b = q2(config.get("pct_bonus_proponente") or 0)
            quota = q2(pieno * pct_s / Decimal("100"))
            bonus = q2(pieno * pct_b / Decimal("100"))
            sconto = q2(sconto + quota)
            righe.append(
                {
                    "contratto": contratto,
                    "index": index,
                    "bonus": bonus,
                    "sconto": quota,
                }
            )
    pagamento = q2(max(Decimal("0"), corrente - sconto))
    return pagamento, righe


def eroga_bonus_sconto(personaggio, ambito: str, fonte: str, righe) -> None:
    for riga in righe:
        contratto = riga["contratto"]
        chiave = f"costo:{fonte}:{contratto.pk}:{riga['index']}"
        if _gia_erogato(contratto, chiave):
            continue
        bonus = q2(riga["bonus"])
        titolo = f"Contratto «{contratto.snapshot.get('nome', '')}» — {ambito}"
        if bonus > 0:
            _accredita(contratto.proponente, bonus, titolo)
        ContrattoAdempimento.objects.create(
            contratto=contratto,
            codice_effetto="sconto_costo",
            fonte=chiave,
            stato=ADEMP_APPLICATO,
            dovuto=bonus,
            versato=bonus,
            importo_proponente=bonus,
            note=titolo[:240],
            dettaglio={"sconto_cliente": str(riga["sconto"]), "ambito": ambito},
        )


def costo_con_sconto_contratto(personaggio, ambito, costo_pieno, costo_corrente, fonte, *, eroga=False):
    pagamento, righe = piano_sconto(personaggio, ambito, costo_pieno, costo_corrente)
    if eroga:
        eroga_bonus_sconto(personaggio, ambito, fonte, righe)
    return pagamento


def _vivo_durante(contratto: Contratto, evento) -> bool:
    if contratto.stato != STATO_STIPULATO or not contratto.stipulata_at:
        return False
    inizio = evento.data_inizio
    fine = evento.data_fine
    return contratto.stipulata_at <= fine and contratto.scadenza >= inizio


def _partecipa(contratto: Contratto, evento) -> bool:
    ids = {contratto.proponente_id}
    if contratto.cliente_id:
        ids.add(contratto.cliente_id)
    return evento.partecipanti.filter(pk__in=ids).exists()


def on_evento_iniziato(evento) -> None:
    for contratto in Contratto.objects.filter(stato=STATO_STIPULATO).select_related("proponente", "cliente"):
        if not _vivo_durante(contratto, evento) or not _partecipa(contratto, evento):
            continue
        if not modulo_attivo_per(contratto.proponente):
            continue
        eroga_inneschi(
            contratto,
            INNESCO_INIZIO_EVENTO,
            fonte_prefix=f"inizio:{evento.pk}",
            evento=evento,
        )


def on_evento_terminato(evento) -> None:
    qs = Contratto.objects.filter(stato=STATO_STIPULATO).select_related("proponente", "cliente")
    for contratto in qs:
        if not _vivo_durante(contratto, evento) or not _partecipa(contratto, evento):
            continue
        if not modulo_attivo_per(contratto.cliente or contratto.proponente):
            continue
        eroga_inneschi(
            contratto,
            INNESCO_FINE_EVENTO,
            fonte_prefix=f"fine:{evento.pk}",
            evento=evento,
        )
        _chiudi_post_evento(contratto, evento)


def _chiudi_post_evento(contratto: Contratto, evento) -> None:
    effetti = [e for e in _effetti_snapshot(contratto) if e.get("codice") == "post_tetto_evento"]
    if not effetti:
        return
    fonte = f"post:{evento.pk}:{contratto.pk}"
    if _gia_erogato(contratto, fonte):
        return
    config = effetti[0].get("config") or {}
    n_post = ContrattoPost.objects.filter(contratto=contratto, evento=evento).count()
    piano = calcola_post_tetto(n_post, int(config.get("massimo_post") or 0), config.get("crediti_per_post") or 0)
    titolo = f"Contratto «{contratto.snapshot.get('nome', '')}» — post evento"
    if piano["creato_ciascuno"] > 0:
        _accredita(contratto.cliente, piano["creato_ciascuno"], titolo, evento=evento)
        _accredita(contratto.proponente, piano["creato_ciascuno"], titolo, evento=evento)
    debito = q2(0)
    versato_ind = q2(0)
    if piano["indennizzo"] > 0 and contratto.cliente_id:
        versato_ind, debito = _trasferisci(
            contratto.proponente,
            contratto.cliente,
            piano["indennizzo"],
            f"{titolo} — indennizzo",
            se_scoperto="DEBITO",
            evento=evento,
        )
    ContrattoAdempimento.objects.create(
        contratto=contratto,
        codice_effetto="post_tetto_evento",
        fonte=fonte,
        evento=evento,
        stato=ADEMP_DEBITO if debito > 0 else ADEMP_APPLICATO,
        dovuto=piano["indennizzo"],
        versato=versato_ind,
        importo_cliente=piano["netto_cliente"],
        importo_proponente=piano["netto_proponente"],
        note=titolo[:240],
        dettaglio={k: str(v) for k, v in piano.items()},
    )


def on_personaggio_morto(personaggio) -> None:
    if not modulo_attivo_per(personaggio):
        return
    for contratto in _contratti_cliente_vivi(personaggio):
        for index, effetto in enumerate(_effetti_snapshot(contratto)):
            if effetto.get("codice") != "penale_confermata":
                continue
            if (effetto.get("config") or {}).get("evento") != "MORTE":
                continue
            fonte = f"morte:{personaggio.pk}:{contratto.pk}:{index}"
            if _gia_erogato(contratto, fonte):
                continue
            _apri_penale(contratto, effetto, index, fonte, motivo="MORTE")


def _apri_penale(contratto, effetto, index, fonte, motivo: str) -> ContrattoAdempimento:
    config = effetto.get("config") or {}
    importo = q2(config.get("importo") or 0)
    return ContrattoAdempimento.objects.create(
        contratto=contratto,
        codice_effetto="penale_confermata",
        fonte=fonte,
        stato=ADEMP_IN_ATTESA,
        dovuto=importo,
        versato=0,
        note=f"{motivo} in attesa di conferma"[:240],
        dettaglio={"motivo": motivo, "config": config, "index": index},
    )


@transaction.atomic
def conferma_adempimento(adempimento: ContrattoAdempimento, *, attore: Personaggio | None, staff: bool) -> ContrattoAdempimento:
    if adempimento.stato != ADEMP_IN_ATTESA:
        return adempimento
    contratto = adempimento.contratto
    config = (adempimento.dettaglio or {}).get("config") or {}
    conferma = config.get("conferma") or "STAFF"
    if conferma == "STAFF" and not staff:
        raise ValidationError("Questa conferma è riservata allo staff.")
    if conferma == "CONTROPARTE" and not staff:
        if attore is None or attore.pk not in (contratto.proponente_id, contratto.cliente_id):
            raise ValidationError("Solo un contraente può confermare.")
    da_ruolo = config.get("da") or "PROPONENTE"
    a_ruolo = config.get("a") or "CLIENTE"
    if (adempimento.dettaglio or {}).get("motivo") == "MORTE":
        a_ruolo = config.get("a_morte_paga") or a_ruolo
    da = _nome_parte(contratto, da_ruolo)
    a = _nome_parte(contratto, a_ruolo)
    versato, debito = _trasferisci(
        da,
        a,
        adempimento.dovuto,
        f"Contratto «{contratto.snapshot.get('nome', '')}» — {adempimento.note}",
        se_scoperto="DEBITO",
    )
    adempimento.versato = versato
    adempimento.stato = ADEMP_DEBITO if debito > 0 else ADEMP_APPLICATO
    adempimento.dettaglio = {**(adempimento.dettaglio or {}), "debito": str(debito)}
    adempimento.save(update_fields=["versato", "stato", "dettaglio", "updated_at"])
    return adempimento


@transaction.atomic
def salda_debito(adempimento: ContrattoAdempimento) -> ContrattoAdempimento:
    if adempimento.stato != ADEMP_DEBITO:
        return adempimento
    residuo = q2(adempimento.dovuto) - q2(adempimento.versato)
    if residuo <= 0:
        adempimento.stato = ADEMP_APPLICATO
        adempimento.save(update_fields=["stato", "updated_at"])
        return adempimento
    contratto = adempimento.contratto
    config = (adempimento.dettaglio or {}).get("config") or {}
    if adempimento.codice_effetto == "post_tetto_evento":
        da, a = contratto.proponente, contratto.cliente
    else:
        da = _nome_parte(contratto, config.get("da") or "PROPONENTE")
        a = _nome_parte(contratto, config.get("a") or "CLIENTE")
    versato, debito = _trasferisci(da, a, residuo, "Saldo debito contratto", se_scoperto="DEBITO")
    adempimento.versato = q2(adempimento.versato) + versato
    adempimento.stato = ADEMP_DEBITO if debito > 0 else ADEMP_APPLICATO
    adempimento.save(update_fields=["versato", "stato", "updated_at"])
    return adempimento


def _valida_parametri(modello: ModelloContratto, inviati: dict) -> dict:
    risolti = {}
    for parametro in modello.parametri.all():
        vincoli = parametro.vincoli or {}
        if parametro.chi_compila == CHI_STAFF:
            risolti[parametro.chiave] = parametro.valore
            continue
        valore = inviati.get(parametro.chiave, vincoli.get("default"))
        if valore in (None, "") and vincoli.get("obbligatorio", True):
            raise ValidationError(f"Manca il parametro «{parametro.etichetta}».")
        if parametro.tipo in ("INTERO", "DECIMALE", "PERCENTUALE") and valore not in (None, ""):
            numero = q2(valore) if parametro.tipo != "INTERO" else int(valore)
            if vincoli.get("min") not in (None, "") and q2(numero) < q2(vincoli["min"]):
                raise ValidationError(f"«{parametro.etichetta}» è sotto il minimo.")
            if vincoli.get("max") not in (None, "") and q2(numero) > q2(vincoli["max"]):
                raise ValidationError(f"«{parametro.etichetta}» è sopra il massimo.")
            risolti[parametro.chiave] = int(numero) if parametro.tipo == "INTERO" else float(numero)
        else:
            risolti[parametro.chiave] = valore
    return risolti


def _effetti_risolti(modello: ModelloContratto, voci_ids: set, parametri: dict) -> list[dict]:
    righe = []
    for effetto in modello.effetti.all():
        if not codice_noto(effetto.codice):
            raise ValidationError(f"Effetto sconosciuto: {effetto.codice}")
        righe.append(
            {
                "codice": effetto.codice,
                "config": risolvi_config(effetto.config or {}, parametri),
                "origine": "modello",
            }
        )
    for voce in modello.voci.all():
        if not voce.obbligatoria and str(voce.pk) not in voci_ids and voce.pk not in voci_ids:
            continue
        for effetto in voce.effetti.all():
            if not codice_noto(effetto.codice):
                raise ValidationError(f"Effetto sconosciuto: {effetto.codice}")
            righe.append(
                {
                    "codice": effetto.codice,
                    "config": risolvi_config(effetto.config or {}, parametri),
                    "origine": str(voce.pk),
                }
            )
    return righe


@transaction.atomic
def crea_proposta(proponente, modello: ModelloContratto, parametri_inviati: dict, voci_ids: list, evento=None) -> Contratto:
    if not modulo_attivo_per(proponente):
        raise ValidationError("Contratti non attivi per questo personaggio.")
    membership = get_active_korp_membership(proponente)
    if not membership or membership.carriera_id != modello.korp_id or not modello.korp.sottoscrive_contratti:
        raise ValidationError("Questo modello non è offerto dalla tua Korp.")
    if not modello.attivo:
        raise ValidationError("Modello non attivo.")
    marca_scaduti()
    if slot_usati(proponente) >= slot_totali(proponente):
        raise ValidationError("Non hai slot di contratto liberi.")
    parametri = _valida_parametri(modello, parametri_inviati or {})
    ids = {str(x) for x in (voci_ids or [])}
    if modello.durata_modo == DURATA_FINE_EVENTO:
        if evento is None:
            raise ValidationError("Scegli l'evento di scadenza.")
        scadenza = evento.data_fine
    else:
        giorni = int(modello.durata_giorni or 0)
        if giorni <= 0:
            raise ValidationError("Durata in giorni non valida.")
        scadenza = timezone.now() + timedelta(days=giorni)
    effetti = _effetti_risolti(modello, ids, parametri)
    voci_scelte = []
    nomi_clausole = []
    nomi_compensi = []
    for voce in modello.voci.all():
        if voce.obbligatoria or str(voce.pk) in ids:
            voci_scelte.append({"id": str(voce.pk), "tipo": voce.tipo, "nome": voce.nome, "testo": voce.testo})
            etichetta = voce.nome + (f" — {voce.testo}" if voce.testo else "")
            if voce.tipo == VOCE_COMPENSO:
                nomi_compensi.append(etichetta)
            else:
                nomi_clausole.append(etichetta)
    testo = _render_testo(
        modello.testo,
        proponente=proponente,
        cliente=None,
        korp=modello.korp,
        scadenza=scadenza,
        parametri=parametri,
        clausole=nomi_clausole,
        compensi=nomi_compensi,
    )
    qr = QrCode.objects.create(testo=f"Contratto {modello.nome}")
    contratto = Contratto.objects.create(
        modello=modello,
        campagna=modello.campagna,
        proponente=proponente,
        stato=STATO_IN_ATTESA,
        scadenza=scadenza,
        qr_code=qr,
        snapshot={
            "nome": modello.nome,
            "chiave_esclusivita": modello.chiave_esclusivita or "",
            "testo_modello": modello.testo,
            "testo": testo,
            "parametri": parametri,
            "effetti": effetti,
            "voci": voci_scelte,
            "korp_nome": modello.korp.nome,
        },
    )
    return contratto


def _rigenera_testo(contratto: Contratto) -> None:
    snap = dict(contratto.snapshot or {})
    clausole = [v["nome"] for v in snap.get("voci") or [] if v.get("tipo") != VOCE_COMPENSO]
    compensi = [v["nome"] for v in snap.get("voci") or [] if v.get("tipo") == VOCE_COMPENSO]
    snap["testo"] = _render_testo(
        snap.get("testo_modello") or "",
        proponente=contratto.proponente,
        cliente=contratto.cliente,
        korp=contratto.modello.korp,
        scadenza=contratto.scadenza,
        parametri=snap.get("parametri") or {},
        clausole=clausole,
        compensi=compensi,
    )
    contratto.snapshot = snap


@transaction.atomic
def firma_contratto(contratto: Contratto, cliente) -> Contratto:
    marca_scaduti(contratto)
    contratto.refresh_from_db()
    if not modulo_attivo_per(cliente):
        raise ValidationError("Contratti non attivi per questo personaggio.")
    if contratto.stato != STATO_IN_ATTESA:
        raise ValidationError("La proposta non è più firmabile.")
    if contratto.scadenza < timezone.now():
        contratto.stato = STATO_SCADUTO
        contratto.save(update_fields=["stato", "updated_at"])
        raise ValidationError("La proposta è scaduta.")
    if cliente.pk == contratto.proponente_id:
        raise ValidationError("Non puoi sottoscrivere un tuo contratto.")
    if cliente_ha_modello_stipulato(cliente, contratto.modello_id, escluso_pk=contratto.pk):
        raise ValidationError("Hai già un contratto stipulato di questo modello.")
    contratto.cliente = cliente
    contratto.stato = STATO_STIPULATO
    contratto.stipulata_at = timezone.now()
    _rigenera_testo(contratto)
    contratto.save(update_fields=["cliente", "stato", "stipulata_at", "snapshot", "updated_at"])
    eroga_inneschi(contratto, INNESCO_STIPULA, fonte_prefix=f"stipula:{contratto.pk}")
    return contratto


@transaction.atomic
def rifiuta_contratto(contratto: Contratto, cliente) -> Contratto:
    if contratto.stato != STATO_IN_ATTESA:
        raise ValidationError("La proposta non è in attesa.")
    if cliente.pk == contratto.proponente_id:
        raise ValidationError("Il proponente annulla la proposta, non la rifiuta.")
    contratto.cliente = cliente
    contratto.stato = STATO_RIFIUTATO
    contratto.save(update_fields=["cliente", "stato", "updated_at"])
    return contratto


@transaction.atomic
def annulla_proposta(contratto: Contratto, proponente) -> Contratto:
    if contratto.proponente_id != proponente.pk:
        raise ValidationError("Solo il proponente può annullare la proposta.")
    if contratto.stato != STATO_IN_ATTESA:
        raise ValidationError("Si può annullare solo una proposta in attesa.")
    contratto.stato = STATO_ANNULLATO
    contratto.save(update_fields=["stato", "updated_at"])
    return contratto


@transaction.atomic
def elimina_contratto(contratto: Contratto) -> None:
    """Cancellazione staff: il record esce dal gioco e lo slot del proponente si libera."""
    qr_id = contratto.qr_code_id
    contratto.delete()
    if qr_id:
        from personaggi.models import QrCode

        QrCode.objects.filter(pk=qr_id).delete()


@transaction.atomic
def attiva_contratto(contratto: Contratto, proponente, *, staff=False) -> Contratto:
    if contratto.stato != STATO_STIPULATO:
        raise ValidationError("Il contratto non è in corso.")
    if contratto.proponente_id != proponente.pk and not staff:
        raise ValidationError("Solo il proponente può attivare.")
    effetti_att = [e for e in _effetti_snapshot(contratto) if e.get("codice") == "attivazione"]
    if not effetti_att:
        raise ValidationError("Questo contratto non prevede un'attivazione.")
    if (contratto.meta or {}).get("attivato"):
        raise ValidationError("Già attivato.")
    config = effetti_att[0].get("config") or {}
    if config.get("richiede_staff") and not staff:
        meta = dict(contratto.meta or {})
        meta["attivazione_in_attesa"] = True
        contratto.meta = meta
        contratto.save(update_fields=["meta", "updated_at"])
        ContrattoAdempimento.objects.get_or_create(
            contratto=contratto,
            fonte=f"attivazione-attesa:{contratto.pk}",
            defaults={
                "codice_effetto": "attivazione",
                "stato": ADEMP_IN_ATTESA,
                "note": "Attivazione in attesa dello staff",
            },
        )
        return contratto
    meta = dict(contratto.meta or {})
    meta["attivato"] = True
    meta["attivazione_in_attesa"] = False
    contratto.meta = meta
    contratto.save(update_fields=["meta", "updated_at"])
    ContrattoAdempimento.objects.filter(
        contratto=contratto,
        fonte=f"attivazione-attesa:{contratto.pk}",
        stato=ADEMP_IN_ATTESA,
    ).update(stato=ADEMP_APPLICATO, updated_at=timezone.now())
    eroga_inneschi(contratto, INNESCO_ATTIVAZIONE, fonte_prefix=f"attivazione:{contratto.pk}")
    if config.get("risolvi_contratto"):
        contratto.stato = STATO_RISOLTO
        contratto.save(update_fields=["stato", "updated_at"])
    return contratto


@transaction.atomic
def segnala_ferita(contratto: Contratto, attore: Personaggio) -> ContrattoAdempimento:
    if contratto.stato != STATO_STIPULATO:
        raise ValidationError("Il contratto non è in corso.")
    if attore.pk not in (contratto.proponente_id, contratto.cliente_id):
        raise ValidationError("Solo un contraente può segnalare la ferita.")
    trovati = [
        (index, effetto)
        for index, effetto in enumerate(_effetti_snapshot(contratto))
        if effetto.get("codice") == "penale_confermata" and (effetto.get("config") or {}).get("evento") == "FERITA"
    ]
    if not trovati:
        raise ValidationError("Questo contratto non prevede la ferita grave.")
    index, effetto = trovati[0]
    fonte = f"ferita:{contratto.pk}:{index}"
    esistente = ContrattoAdempimento.objects.filter(contratto=contratto, fonte=fonte).first()
    if esistente:
        return esistente
    return _apri_penale(contratto, effetto, index, fonte, motivo="FERITA")


@transaction.atomic
def registra_servizio(contratto: Contratto, attore: Personaggio, quantita, evento=None, note="") -> ContrattoServizio:
    if contratto.stato != STATO_STIPULATO:
        raise ValidationError("Il contratto non è in corso.")
    if attore.pk != contratto.proponente_id:
        raise ValidationError("Registra il servizio il proponente.")
    effetti = [e for e in _effetti_snapshot(contratto) if e.get("codice") == "contatore_servizi"]
    if not effetti:
        raise ValidationError("Nessun tetto di servizi su questo contratto.")
    config = effetti[0].get("config") or {}
    unita = config.get("unita") or "ORE"
    massimo = q2(config.get("massimo_per_evento") or 0)
    qty = q2(quantita)
    if qty <= 0:
        raise ValidationError("Quantità non valida.")
    gia = ContrattoServizio.objects.filter(contratto=contratto, evento=evento, unita=unita).aggregate(s=Sum("quantita"))["s"]
    if massimo > 0 and q2(gia or 0) + qty > massimo:
        raise ValidationError("Tetto servizi dell'evento superato.")
    return ContrattoServizio.objects.create(
        contratto=contratto,
        evento=evento,
        unita=unita,
        quantita=qty,
        note=(note or "")[:200],
    )


@transaction.atomic
def associa_post(contratto: Contratto, proponente, post) -> ContrattoPost:
    if contratto.proponente_id != proponente.pk:
        raise ValidationError("Solo il proponente associa i post.")
    if contratto.stato != STATO_STIPULATO:
        raise ValidationError("Il contratto non è in corso.")
    if not any(e.get("codice") == "post_tetto_evento" for e in _effetti_snapshot(contratto)):
        raise ValidationError("Questo contratto non conta i post.")
    if post.autore_id != proponente.pk:
        raise ValidationError("Il post non è tuo.")
    if not post.evento_id:
        raise ValidationError("Il post non è legato a un evento.")
    if ContrattoPost.objects.filter(post=post).exclude(contratto=contratto).exists():
        raise ValidationError("Questo post è già contato su un altro contratto.")
    riga, _ = ContrattoPost.objects.get_or_create(
        contratto=contratto,
        post=post,
        defaults={"evento_id": post.evento_id},
    )
    return riga


def qr_png_base64(qr_id: str) -> str:
    immagine = qrcode.make(str(qr_id))
    buffer = io.BytesIO()
    immagine.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def serializza_contratto(contratto: Contratto, personaggio_id=None) -> dict:
    marca_scaduti(contratto)
    contratto.refresh_from_db()
    snap = contratto.snapshot or {}
    ruolo = None
    if personaggio_id and contratto.proponente_id == personaggio_id:
        ruolo = "PROPONENTE"
    elif personaggio_id and contratto.cliente_id == personaggio_id:
        ruolo = "CLIENTE"
    codici = {e.get("codice") for e in snap.get("effetti") or []}
    return {
        "id": str(contratto.pk),
        "nome": snap.get("nome") or "",
        "stato": contratto.stato,
        "ruolo": ruolo,
        "scadenza": contratto.scadenza.isoformat() if contratto.scadenza else None,
        "stipulata_at": contratto.stipulata_at.isoformat() if contratto.stipulata_at else None,
        "proponente": {"id": contratto.proponente_id, "nome": contratto.proponente.nome},
        "cliente": (
            {"id": contratto.cliente_id, "nome": contratto.cliente.nome} if contratto.cliente_id else None
        ),
        "testo": _testo_visibile(contratto),
        "parametri": snap.get("parametri") or {},
        "chiave_esclusivita": snap.get("chiave_esclusivita") or "",
        "qr_code_id": contratto.qr_code_id,
        "azioni": {
            "associa_post": "post_tetto_evento" in codici and contratto.stato == STATO_STIPULATO,
            "servizio": "contatore_servizi" in codici and contratto.stato == STATO_STIPULATO,
            "ferita": any(
                e.get("codice") == "penale_confermata" and (e.get("config") or {}).get("evento") == "FERITA"
                for e in snap.get("effetti") or []
            ),
            "attiva": "attivazione" in codici and contratto.stato == STATO_STIPULATO and not (contratto.meta or {}).get("attivato"),
        },
        "meta": contratto.meta or {},
        "adempimenti": [
            {
                "id": str(a.pk),
                "codice": a.codice_effetto,
                "stato": a.stato,
                "dovuto": str(a.dovuto),
                "versato": str(a.versato),
                "note": a.note,
            }
            for a in contratto.adempimenti.all()[:30]
        ],
    }


def risposta_qr_contratto(qr_code, request):
    from rest_framework import status
    from rest_framework.response import Response

    contratto = (
        Contratto.objects.filter(qr_code=qr_code)
        .select_related("proponente", "cliente", "modello")
        .first()
    )
    if not contratto:
        return None
    if not request.user.is_authenticated:
        return Response({"error": "Autenticazione richiesta."}, status=status.HTTP_401_UNAUTHORIZED)
    raw_pid = request.query_params.get("personaggio_id")
    try:
        pid = int(raw_pid)
    except (TypeError, ValueError):
        return Response({"error": "personaggio_id richiesto."}, status=status.HTTP_400_BAD_REQUEST)
    scanner = Personaggio.objects.filter(pk=pid, proprietario=request.user).first()
    if not scanner:
        return Response({"error": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)
    marca_scaduti(contratto)
    contratto.refresh_from_db()
    dati = serializza_contratto(contratto, scanner.pk)
    puo_firmare = contratto.stato == STATO_IN_ATTESA and scanner.pk != contratto.proponente_id
    motivo = ""
    if puo_firmare and cliente_ha_modello_stipulato(scanner, contratto.modello_id, escluso_pk=contratto.pk):
        puo_firmare = False
        motivo = "Hai già un contratto stipulato di questo modello."
    dati["puo_firmare"] = puo_firmare
    dati["motivo_blocco"] = motivo
    dati["puo_rifiutare"] = contratto.stato == STATO_IN_ATTESA and scanner.pk != contratto.proponente_id
    return Response(
        {
            "tipo_modello": "contratto",
            "messaggio": dati["nome"] or "Contratto",
            "dati": dati,
            "qrcode_id": qr_code.id,
        },
        status=status.HTTP_200_OK,
    )


def salva_modello(modello: ModelloContratto, payload: dict) -> ModelloContratto:
    modello.nome = (payload.get("nome") or modello.nome or "").strip()
    modello.attivo = bool(payload.get("attivo", True))
    modello.chiave_esclusivita = (payload.get("chiave_esclusivita") or "").strip()[:64]
    modello.durata_modo = payload.get("durata_modo") or DURATA_GIORNI
    modello.durata_giorni = int(payload.get("durata_giorni") or 90)
    modello.testo = payload.get("testo") or ""
    if payload.get("korp"):
        modello.korp_id = payload["korp"]
    if payload.get("campagna"):
        modello.campagna_id = payload["campagna"]
    if not modello.nome:
        raise ValidationError("Il nome è obbligatorio.")
    modello.save()
    _sostituisci_figli(modello, payload)
    return modello


def _sostituisci_figli(modello: ModelloContratto, payload: dict) -> None:
    if "parametri" in payload:
        tenuti = []
        for ordine, row in enumerate(payload.get("parametri") or []):
            chiave = (row.get("chiave") or "").strip()
            if not chiave:
                continue
            obj, _ = ParametroModello.objects.update_or_create(
                modello=modello,
                chiave=chiave,
                defaults={
                    "etichetta": row.get("etichetta") or chiave,
                    "tipo": row.get("tipo") or "DECIMALE",
                    "chi_compila": row.get("chi_compila") or CHI_STAFF,
                    "valore": row.get("valore"),
                    "vincoli": row.get("vincoli") or {},
                    "ordine": ordine,
                },
            )
            tenuti.append(obj.pk)
        ParametroModello.objects.filter(modello=modello).exclude(pk__in=tenuti).delete()
    if "voci" in payload or "effetti" in payload:
        EffettoModello.objects.filter(modello=modello).delete()
        if "voci" in payload:
            VoceModello.objects.filter(modello=modello).delete()
            for ordine, row in enumerate(payload.get("voci") or []):
                voce = VoceModello.objects.create(
                    modello=modello,
                    tipo=row.get("tipo") or VOCE_CLAUSOLA,
                    nome=row.get("nome") or "Voce",
                    testo=row.get("testo") or "",
                    obbligatoria=bool(row.get("obbligatoria")),
                    ordine=ordine,
                )
                for i, effetto in enumerate(row.get("effetti") or []):
                    if not codice_noto(effetto.get("codice") or ""):
                        raise ValidationError(f"Effetto sconosciuto: {effetto.get('codice')}")
                    EffettoModello.objects.create(
                        voce=voce,
                        codice=effetto["codice"],
                        config=effetto.get("config") or {},
                        ordine=i,
                    )
        for i, effetto in enumerate(payload.get("effetti") or []):
            if not codice_noto(effetto.get("codice") or ""):
                raise ValidationError(f"Effetto sconosciuto: {effetto.get('codice')}")
            EffettoModello.objects.create(
                modello=modello,
                codice=effetto["codice"],
                config=effetto.get("config") or {},
                ordine=i,
            )


def serializza_modello(modello: ModelloContratto) -> dict:
    return {
        "id": str(modello.pk),
        "nome": modello.nome,
        "attivo": modello.attivo,
        "korp": modello.korp_id,
        "korp_nome": modello.korp.nome,
        "campagna": str(modello.campagna_id),
        "chiave_esclusivita": modello.chiave_esclusivita,
        "durata_modo": modello.durata_modo,
        "durata_giorni": modello.durata_giorni,
        "testo": modello.testo,
        "parametri": [
            {
                "id": str(p.pk),
                "chiave": p.chiave,
                "etichetta": p.etichetta,
                "tipo": p.tipo,
                "chi_compila": p.chi_compila,
                "valore": p.valore,
                "vincoli": p.vincoli or {},
            }
            for p in modello.parametri.all()
        ],
        "effetti": [
            {"id": str(e.pk), "codice": e.codice, "config": e.config or {}}
            for e in modello.effetti.all()
        ],
        "voci": [
            {
                "id": str(v.pk),
                "tipo": v.tipo,
                "nome": v.nome,
                "testo": v.testo,
                "obbligatoria": v.obbligatoria,
                "effetti": [
                    {"codice": e.codice, "config": e.config or {}}
                    for e in v.effetti.all()
                ],
            }
            for v in modello.voci.all()
        ],
    }


PRESET = {
    "talento": {
        "nome": "Contratto di Talento",
        "chiave_esclusivita": "talento",
        "durata_giorni": 90,
        "testo": (
            "{{proponente}} ({{korp}}) propone a {{cliente}} un contratto di Talento fino al {{scadenza}}.\n"
            "Su ogni task completata dal cliente, bonus {{param:pct_cliente}}% al cliente "
            "e {{param:pct_proponente}}% al proponente, calcolati sui crediti della task."
        ),
        "parametri": [
            {"chiave": "pct_cliente", "etichetta": "Percentuale cliente", "tipo": "PERCENTUALE", "chi_compila": "STAFF", "valore": 10},
            {"chiave": "pct_proponente", "etichetta": "Percentuale proponente", "tipo": "PERCENTUALE", "chi_compila": "STAFF", "valore": 20},
        ],
        "effetti": [
            {"codice": "percentuale_task", "config": {"pct_cliente": "{{param:pct_cliente}}", "pct_proponente": "{{param:pct_proponente}}"}},
        ],
    },
    "creatore": {
        "nome": "Contratto di Creatore",
        "chiave_esclusivita": "creatore",
        "durata_giorni": 90,
        "testo": (
            "Sconto del {{param:pct_sconto}}% al cliente e bonus del {{param:pct_bonus}}% al proponente "
            "sul costo pieno di creazioni e forgiatura. Fino al {{scadenza}}."
        ),
        "parametri": [
            {"chiave": "pct_sconto", "etichetta": "Sconto cliente %", "tipo": "PERCENTUALE", "chi_compila": "STAFF", "valore": 10},
            {"chiave": "pct_bonus", "etichetta": "Bonus proponente %", "tipo": "PERCENTUALE", "chi_compila": "STAFF", "valore": 10},
        ],
        "effetti": [
            {
                "codice": "sconto_costo",
                "config": {
                    "ambiti": ["creazione_infusione", "creazione_cerimoniale", "creazione_tessitura", "forgiatura", "consumabile"],
                    "pct_sconto_cliente": "{{param:pct_sconto}}",
                    "pct_bonus_proponente": "{{param:pct_bonus}}",
                },
            }
        ],
    },
    "pubblicitario": {
        "nome": "Contratto pubblicitario",
        "chiave_esclusivita": "pubblicitario",
        "durata_giorni": 180,
        "testo": (
            "{{proponente}} pubblica fino a {{param:massimo_post}} post per evento su: {{param:tema}}.\n"
            "Ogni post vale {{param:crediti_per_post}} crediti a testa, fino al tetto. "
            "I post mancanti li indennizza il proponente. Fino al {{scadenza}}."
        ),
        "parametri": [
            {"chiave": "tema", "etichetta": "Tema dei post", "tipo": "TESTO", "chi_compila": "PROPONENTE", "vincoli": {"obbligatorio": True}},
            {"chiave": "massimo_post", "etichetta": "Massimo post per evento", "tipo": "INTERO", "chi_compila": "STAFF", "valore": 3},
            {"chiave": "crediti_per_post", "etichetta": "Crediti a post", "tipo": "DECIMALE", "chi_compila": "STAFF", "valore": 30},
        ],
        "effetti": [
            {"codice": "post_tetto_evento", "config": {"massimo_post": "{{param:massimo_post}}", "crediti_per_post": "{{param:crediti_per_post}}"}},
        ],
    },
    "protettore": {
        "nome": "Contratto di Protettore",
        "chiave_esclusivita": "protettore",
        "durata_giorni": 90,
        "testo": (
            "{{cliente}} versa {{param:somma}} crediti a {{proponente}} per la protezione fino al {{scadenza}}.\n"
            "Servizi massimi per evento e penali sono nelle clausole."
        ),
        "parametri": [
            {"chiave": "somma", "etichetta": "Somma versata dal cliente", "tipo": "DECIMALE", "chi_compila": "STAFF", "valore": 200},
            {"chiave": "penale", "etichetta": "Penale morte", "tipo": "DECIMALE", "chi_compila": "STAFF", "valore": 1000},
        ],
        "effetti": [
            {"codice": "trasferimento", "config": {"innesco": "ALLA_STIPULA", "da": "CLIENTE", "a": "PROPONENTE", "importo": "{{param:somma}}", "se_scoperto": "BLOCCA"}},
            {"codice": "contatore_servizi", "config": {"unita": "ORE", "massimo_per_evento": 4}},
            {"codice": "penale_confermata", "config": {"evento": "FERITA", "da": "PROPONENTE", "a": "CLIENTE", "importo": "{{param:somma}}", "conferma": "CONTROPARTE"}},
            {"codice": "penale_confermata", "config": {"evento": "MORTE", "da": "PROPONENTE", "a": "CLIENTE", "importo": "{{param:penale}}", "conferma": "STAFF", "a_morte_paga": "CLIENTE"}},
        ],
    },
    "mercenario": {
        "nome": "Contratto di Mercenario",
        "chiave_esclusivita": "mercenario",
        "durata_giorni": 90,
        "testo": (
            "{{cliente}} offre i propri servigi a {{proponente}}. "
            "Paga di {{param:paga}} crediti a inizio di ogni evento coperto, fino al {{scadenza}}."
        ),
        "parametri": [
            {"chiave": "paga", "etichetta": "Paga per evento", "tipo": "DECIMALE", "chi_compila": "STAFF", "valore": 150},
            {"chiave": "erede", "etichetta": "Erede", "tipo": "PERSONAGGIO", "chi_compila": "PROPONENTE", "vincoli": {"obbligatorio": False}},
        ],
        "effetti": [
            {"codice": "trasferimento", "config": {"innesco": "A_INIZIO_EVENTO", "da": "PROPONENTE", "a": "CLIENTE", "importo": "{{param:paga}}", "se_scoperto": "DEBITO"}},
            {"codice": "contatore_servizi", "config": {"unita": "ORE", "massimo_per_evento": 6}},
            {"codice": "penale_confermata", "config": {"evento": "FERITA", "da": "PROPONENTE", "a": "CLIENTE", "importo": "{{param:paga}}", "conferma": "CONTROPARTE"}},
            {"codice": "penale_confermata", "config": {"evento": "MORTE", "da": "PROPONENTE", "a": "EREDE", "importo": "{{param:paga}}", "conferma": "STAFF", "a_morte_paga": "EREDE"}},
        ],
    },
    "agente": {
        "nome": "Contratto di Agente",
        "chiave_esclusivita": "agente",
        "durata_giorni": 365,
        "testo": (
            "{{cliente}} accetta di poter agire come agente dormiente di {{proponente}} fino al {{scadenza}}.\n"
            "Compenso iniziale per entrambi. Le clausole descrivono l'attivazione."
        ),
        "parametri": [
            {"chiave": "compenso", "etichetta": "Compenso iniziale (ciascuno)", "tipo": "DECIMALE", "chi_compila": "STAFF", "valore": 40},
        ],
        "effetti": [
            {"codice": "credito_creato", "config": {"innesco": "ALLA_STIPULA", "beneficiario": "ENTRAMBI", "importo": "{{param:compenso}}"}},
            {"codice": "attivazione", "config": {"richiede_staff": False, "risolvi_contratto": False}},
        ],
        "voci": [
            {
                "tipo": "CLAUSOLA",
                "nome": "Attivazione sul campo",
                "testo": "All'attivazione entrambi ricevono un ulteriore compenso.",
                "obbligatoria": False,
                "effetti": [
                    {"codice": "credito_creato", "config": {"innesco": "AD_ATTIVAZIONE", "beneficiario": "ENTRAMBI", "importo": "{{param:compenso}}"}},
                ],
            }
        ],
    },
}


@transaction.atomic
def crea_preset(campagna, korp, codice: str) -> ModelloContratto:
    ricetta = PRESET.get(codice)
    if not ricetta:
        raise ValidationError("Preset sconosciuto.")
    modello = ModelloContratto.objects.create(
        campagna=campagna,
        korp=korp,
        nome=ricetta["nome"],
        chiave_esclusivita=ricetta["chiave_esclusivita"],
        durata_modo=DURATA_GIORNI,
        durata_giorni=ricetta["durata_giorni"],
        testo=ricetta["testo"],
        attivo=True,
    )
    salva_modello(modello, {**ricetta, "korp": korp.pk, "campagna": campagna.pk})
    return modello
