"""Importazione moduli e validazione risposte del sondaggio in-app."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from personaggi.economia_crediti import CONTO_CORRENTE, CONTO_DEPOSITO
from personaggi.sondaggi_google import (
    ErroreModuloGoogle,
    analizza_html_modulo,
    normalizza_url_modulo,
    scarica_html_modulo,
)
from personaggi.sondaggi_models import RispostaSondaggio, Sondaggio

_DATA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ORA_RE = re.compile(r"^(\d{2}):(\d{2})(?::\d{2})?$")
_LIMITI_TESTO = {"testo_breve": 500, "testo_lungo": 5000}


def importa_modulo(campagna, url: str, *, attivo: bool | None = None) -> tuple[Sondaggio, bool]:
    canonico, form_id = normalizza_url_modulo(url)
    html = scarica_html_modulo(canonico)
    return salva_analisi(campagna, canonico, form_id, analizza_html_modulo(html), attivo=attivo)


def salva_analisi(campagna, canonico: str, form_id: str, analisi: dict, *, attivo: bool | None = None):
    titolo = (analisi.get("titolo") or "Sondaggio")[:200]
    descrizione = (analisi.get("descrizione") or "")[:8000]
    domande = analisi.get("domande") or []
    avvisi = analisi.get("avvisi") or []
    with transaction.atomic():
        esistente = (
            Sondaggio.objects.select_for_update()
            .filter(campagna=campagna, google_form_id=form_id)
            .first()
        )
        if esistente:
            esistente.titolo = titolo
            esistente.descrizione = descrizione
            esistente.google_form_url = canonico
            esistente.domande = domande
            esistente.avvisi = avvisi
            if attivo is not None:
                esistente.attivo = attivo
            esistente.save()
            return esistente, False
        creato = Sondaggio.objects.create(
            campagna=campagna,
            google_form_id=form_id,
            titolo=titolo,
            descrizione=descrizione,
            google_form_url=canonico,
            domande=domande,
            avvisi=avvisi,
            attivo=True if attivo is None else attivo,
        )
        return creato, True


def _domande_compilabili(domande) -> list[dict]:
    scelte = []
    for domanda in domande or []:
        if not domanda.get("supportata") or domanda.get("tipo") == "sezione":
            continue
        ident = str(domanda.get("id") or "")
        if domanda.get("tipo") == "griglia" or ident.startswith("entry."):
            scelte.append(domanda)
    return scelte


def valida_risposte(domande, grezze) -> dict:
    if not isinstance(grezze, dict):
        raise ValidationError("Le risposte devono essere un oggetto.")
    pulite = {}
    for domanda in _domande_compilabili(domande):
        chiave = domanda["id"]
        tipo = domanda["tipo"]
        valore = grezze.get(chiave)
        obbligatorio = bool(domanda.get("obbligatoria"))
        if tipo == "griglia":
            for riga in domanda.get("righe") or []:
                chiave_riga = str(riga.get("id") or "")
                if not chiave_riga.startswith("entry."):
                    continue
                valore_riga = grezze.get(chiave_riga)
                obbligo_riga = bool(riga.get("obbligatoria"))
                titolo_riga = f"{domanda['titolo']} — {riga.get('titolo') or 'riga'}"
                if valore_riga is None or valore_riga == "" or valore_riga == []:
                    if obbligo_riga:
                        raise ValidationError(f"Rispondi a «{titolo_riga}».")
                    continue
                if isinstance(valore_riga, list):
                    raise ValidationError(f"«{titolo_riga}» accetta una sola risposta.")
                testo_riga = str(valore_riga).strip()
                ammesse = [str(voce) for voce in (riga.get("opzioni") or domanda.get("opzioni") or [])]
                if testo_riga not in ammesse:
                    raise ValidationError(f"Scelta non prevista in «{titolo_riga}».")
                pulite[chiave_riga] = testo_riga
            continue
        if tipo == "caselle":
            if valore in (None, "", []):
                if obbligatorio:
                    raise ValidationError(f"Rispondi a «{domanda['titolo']}».")
                continue
            if not isinstance(valore, list):
                raise ValidationError(f"«{domanda['titolo']}» accetta più scelte.")
            ammesse = set(domanda.get("opzioni") or [])
            scelte = []
            for voce in valore:
                testo = str(voce).strip()
                if testo not in ammesse:
                    raise ValidationError(f"Scelta non prevista in «{domanda['titolo']}».")
                if testo not in scelte:
                    scelte.append(testo)
            if obbligatorio and not scelte:
                raise ValidationError(f"Rispondi a «{domanda['titolo']}».")
            if scelte:
                pulite[chiave] = scelte
            continue
        if valore is None or (isinstance(valore, str) and not valore.strip()):
            if obbligatorio:
                raise ValidationError(f"Rispondi a «{domanda['titolo']}».")
            continue
        if isinstance(valore, list):
            raise ValidationError(f"«{domanda['titolo']}» accetta una sola risposta.")
        testo = str(valore).strip()
        if tipo in _LIMITI_TESTO:
            if len(testo) > _LIMITI_TESTO[tipo]:
                raise ValidationError(f"«{domanda['titolo']}» è troppo lunga.")
            pulite[chiave] = testo
            continue
        if tipo in {"scelta_singola", "menu"}:
            if testo not in set(domanda.get("opzioni") or []):
                raise ValidationError(f"Scelta non prevista in «{domanda['titolo']}».")
            pulite[chiave] = testo
            continue
        if tipo == "scala":
            try:
                numero = int(testo)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"«{domanda['titolo']}» richiede un numero.") from exc
            minimo = domanda.get("scala_min")
            massimo = domanda.get("scala_max")
            if minimo is not None and numero < int(minimo):
                raise ValidationError(f"«{domanda['titolo']}» è sotto il minimo.")
            if massimo is not None and numero > int(massimo):
                raise ValidationError(f"«{domanda['titolo']}» è sopra il massimo.")
            pulite[chiave] = str(numero)
            continue
        if tipo == "valutazione":
            ammesse = [str(voce) for voce in (domanda.get("opzioni") or [])]
            if ammesse and testo not in ammesse:
                raise ValidationError(f"«{domanda['titolo']}» richiede un livello previsto.")
            if not ammesse:
                try:
                    numero = int(testo)
                except (TypeError, ValueError) as exc:
                    raise ValidationError(f"«{domanda['titolo']}» richiede un numero.") from exc
                minimo = int(domanda.get("scala_min") if domanda.get("scala_min") is not None else 1)
                massimo = int(domanda.get("scala_max") if domanda.get("scala_max") is not None else 5)
                if numero < minimo or numero > massimo:
                    raise ValidationError(f"«{domanda['titolo']}» è fuori dai livelli.")
                testo = str(numero)
            pulite[chiave] = testo
            continue
        if tipo == "data":
            if not _DATA_RE.match(testo):
                raise ValidationError(f"«{domanda['titolo']}» richiede una data.")
            try:
                datetime.strptime(testo, "%Y-%m-%d")
            except ValueError as exc:
                raise ValidationError(f"«{domanda['titolo']}» ha una data non valida.") from exc
            pulite[chiave] = testo
            continue
        if tipo == "ora":
            trovato = _ORA_RE.match(testo)
            if not trovato:
                raise ValidationError(f"«{domanda['titolo']}» richiede un orario.")
            ore, minuti = int(trovato.group(1)), int(trovato.group(2))
            if ore > 23 or minuti > 59:
                raise ValidationError(f"«{domanda['titolo']}» ha un orario non valido.")
            pulite[chiave] = f"{ore:02d}:{minuti:02d}"
            continue
        raise ValidationError(f"«{domanda['titolo']}» non è compilabile nell'app.")
    if len(str(pulite)) > 20000:
        raise ValidationError("Risposte troppo lunghe.")
    return pulite


_MAX_PC = 10000
_MAX_CREDITI = Decimal("1000000.00")


def _importo_crediti(valore, nome: str) -> Decimal:
    if isinstance(valore, bool) or valore is None:
        raise ValidationError(f"{nome} deve essere un importo.")
    testo = str(valore).strip().replace(",", ".")
    if testo == "":
        return Decimal("0.00")
    try:
        numero = Decimal(testo)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{nome} deve essere un importo.") from exc
    numero = numero.quantize(Decimal("0.01"))
    if numero < 0 or numero > _MAX_CREDITI:
        raise ValidationError(f"{nome} deve essere tra 0 e {_MAX_CREDITI}.")
    return numero


def _importo_pc(valore) -> int:
    if isinstance(valore, bool) or valore is None:
        raise ValidationError("I PC del premio devono essere un numero intero.")
    testo = str(valore).strip().replace(",", ".")
    if testo == "":
        return 0
    try:
        numero = Decimal(testo)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError("I PC del premio devono essere un numero intero.") from exc
    if numero != numero.to_integral_value():
        raise ValidationError("I PC del premio devono essere un numero intero.")
    intero = int(numero)
    if intero < 0 or intero > _MAX_PC:
        raise ValidationError(f"I PC del premio devono essere tra 0 e {_MAX_PC}.")
    return intero


def applica_premi_da_richiesta(sondaggio: Sondaggio, dati) -> None:
    """Aggiorna gli importi del premio se presenti nella richiesta staff."""
    if not isinstance(dati, dict):
        return
    if "premio_pc" in dati:
        sondaggio.premio_pc = _importo_pc(dati.get("premio_pc"))
    if "premio_crediti_correnti" in dati:
        sondaggio.premio_crediti_correnti = _importo_crediti(
            dati.get("premio_crediti_correnti"),
            "I crediti correnti del premio",
        )
    if "premio_crediti_deposito" in dati:
        sondaggio.premio_crediti_deposito = _importo_crediti(
            dati.get("premio_crediti_deposito"),
            "I crediti di deposito del premio",
        )


def premio_configurato(sondaggio: Sondaggio) -> bool:
    return (
        int(sondaggio.premio_pc or 0) > 0
        or Decimal(sondaggio.premio_crediti_correnti or 0) > 0
        or Decimal(sondaggio.premio_crediti_deposito or 0) > 0
    )


def _descrizione_premio(sondaggio: Sondaggio) -> str:
    titolo = (sondaggio.titolo or "Sondaggio").strip() or "Sondaggio"
    return f"Sondaggio «{titolo}»"[:200]


def eroga_premio(risposta: RispostaSondaggio) -> bool:
    """
    Accredita PC e crediti del sondaggio, una sola volta per risposta.
    Se il premio configurato è zero, non segna la risposta come pagata:
    lo staff può accreditarla dopo aver impostato gli importi.
    """
    if risposta.premio_erogato_at or not risposta.personaggio_id:
        return False
    sondaggio = risposta.sondaggio
    pc = int(sondaggio.premio_pc or 0)
    corrente = Decimal(sondaggio.premio_crediti_correnti or 0).quantize(Decimal("0.01"))
    deposito = Decimal(sondaggio.premio_crediti_deposito or 0).quantize(Decimal("0.01"))
    if pc <= 0 and corrente <= 0 and deposito <= 0:
        return False
    personaggio = risposta.personaggio
    descrizione = _descrizione_premio(sondaggio)
    if pc > 0:
        personaggio.modifica_pc(pc, descrizione)
    if corrente > 0:
        personaggio.modifica_crediti(corrente, descrizione, conto=CONTO_CORRENTE)
    if deposito > 0:
        personaggio.modifica_crediti(deposito, descrizione, conto=CONTO_DEPOSITO)
    parti = []
    if pc > 0:
        parti.append(f"{pc} PC")
    if corrente > 0:
        parti.append(f"{corrente} CR correnti")
    if deposito > 0:
        parti.append(f"{deposito} CR deposito")
    personaggio.aggiungi_log(f"Premio sondaggio «{sondaggio.titolo}»: {', '.join(parti)}")
    risposta.premio_pc = pc
    risposta.premio_crediti_correnti = corrente
    risposta.premio_crediti_deposito = deposito
    risposta.premio_erogato_at = timezone.now()
    risposta.save(update_fields=[
        "premio_pc",
        "premio_crediti_correnti",
        "premio_crediti_deposito",
        "premio_erogato_at",
        "updated_at",
    ])
    return True


def eroga_premi_mancanti(sondaggio: Sondaggio) -> int:
    """Accredita il premio attuale a chi ha già risposto e non l'ha ancora ricevuto."""
    if not premio_configurato(sondaggio):
        return 0
    erogati = 0
    with transaction.atomic():
        qs = (
            sondaggio.risposte.select_for_update()
            .filter(premio_erogato_at__isnull=True, personaggio__isnull=False)
            .order_by("created_at")
        )
        for risposta in qs:
            if eroga_premio(risposta):
                erogati += 1
    return erogati


def registra_risposta(sondaggio: Sondaggio, personaggio, utente, grezze) -> tuple[RispostaSondaggio, bool]:
    if not sondaggio.attivo:
        raise ValidationError("Questo sondaggio non è aperto.")
    if personaggio.campagna_id != sondaggio.campagna_id:
        raise ValidationError("Il sondaggio appartiene a un'altra campagna.")
    pulite = valida_risposte(sondaggio.domande, grezze)
    with transaction.atomic():
        esistente = (
            RispostaSondaggio.objects.select_for_update()
            .filter(sondaggio=sondaggio, personaggio=personaggio)
            .first()
        )
        if esistente and not sondaggio.consenti_modifica:
            raise ValidationError("Hai già inviato questo sondaggio.")
        if esistente:
            return _aggiorna_risposta(esistente, pulite, utente), False
        try:
            creata = RispostaSondaggio.objects.create(
                sondaggio=sondaggio,
                personaggio=personaggio,
                utente=utente,
                risposte=pulite,
            )
        except IntegrityError:
            esistente = (
                RispostaSondaggio.objects.select_for_update()
                .filter(sondaggio=sondaggio, personaggio=personaggio)
                .first()
            )
            if not esistente or not sondaggio.consenti_modifica:
                raise ValidationError("Hai già inviato questo sondaggio.")
            return _aggiorna_risposta(esistente, pulite, utente), False
        eroga_premio(creata)
        return creata, True


def _aggiorna_risposta(esistente, pulite, utente):
    esistente.risposte = pulite
    esistente.utente = utente
    esistente.google_inviato_at = None
    esistente.google_claim_at = None
    esistente.google_errore = ""
    esistente.save()
    return esistente


def ha_domande_esterne(domande) -> bool:
    return any(not d.get("supportata") for d in (domande or []))


def _premio_dict(pc, corrente, deposito) -> dict:
    return {
        "pc": int(pc or 0),
        "crediti_correnti": f"{Decimal(corrente or 0):.2f}",
        "crediti_deposito": f"{Decimal(deposito or 0):.2f}",
    }


def serializza_per_giocatore(sondaggio: Sondaggio, risposta: RispostaSondaggio | None) -> dict:
    gia = risposta is not None
    premio_ricevuto = None
    if risposta and risposta.premio_erogato_at:
        premio_ricevuto = _premio_dict(
            risposta.premio_pc,
            risposta.premio_crediti_correnti,
            risposta.premio_crediti_deposito,
        )
    return {
        "id": str(sondaggio.id),
        "titolo": sondaggio.titolo,
        "descrizione": sondaggio.descrizione,
        "domande": sondaggio.domande,
        "consenti_modifica": sondaggio.consenti_modifica,
        "gia_risposto": gia,
        "mia_risposta": risposta.risposte if risposta else None,
        "inviata_il": risposta.created_at.isoformat() if risposta else None,
        "link_esterno": sondaggio.google_form_url if ha_domande_esterne(sondaggio.domande) else "",
        "premio": _premio_dict(
            sondaggio.premio_pc,
            sondaggio.premio_crediti_correnti,
            sondaggio.premio_crediti_deposito,
        ),
        "premio_ricevuto": premio_ricevuto,
    }


def serializza_staff(sondaggio: Sondaggio, *, con_risposte: bool = False) -> dict:
    qs = sondaggio.risposte.all()
    totale = qs.count()
    inoltrate = qs.filter(google_inviato_at__isnull=False).count()
    payload = {
        "id": str(sondaggio.id),
        "titolo": sondaggio.titolo,
        "descrizione": sondaggio.descrizione,
        "google_form_url": sondaggio.google_form_url,
        "google_form_id": sondaggio.google_form_id,
        "domande": sondaggio.domande,
        "avvisi": sondaggio.avvisi,
        "attivo": sondaggio.attivo,
        "consenti_modifica": sondaggio.consenti_modifica,
        "inoltra_email": sondaggio.inoltra_email,
        "premio_pc": int(sondaggio.premio_pc or 0),
        "premio_crediti_correnti": f"{Decimal(sondaggio.premio_crediti_correnti or 0):.2f}",
        "premio_crediti_deposito": f"{Decimal(sondaggio.premio_crediti_deposito or 0):.2f}",
        "premi_mancanti": (
            qs.filter(premio_erogato_at__isnull=True, personaggio__isnull=False).count()
            if premio_configurato(sondaggio)
            else 0
        ),
        "creato_il": sondaggio.created_at.isoformat(),
        "risposte_totali": totale,
        "risposte_inoltrate": inoltrate,
        "risposte_in_sospeso": totale - inoltrate,
    }
    if con_risposte:
        righe = []
        for riga in qs.select_related("personaggio", "utente").order_by("-created_at")[:200]:
            righe.append({
                "id": str(riga.id),
                "personaggio": getattr(riga.personaggio, "nome", "") or "",
                "utente": getattr(riga.utente, "username", "") or "",
                "risposte": riga.risposte,
                "creata_il": riga.created_at.isoformat(),
                "aggiornata_il": riga.updated_at.isoformat() if riga.updated_at else "",
                "google_inviato_il": riga.google_inviato_at.isoformat() if riga.google_inviato_at else "",
                "google_errore": riga.google_errore,
                "premio_erogato": bool(riga.premio_erogato_at),
                "premio": _premio_dict(
                    riga.premio_pc,
                    riga.premio_crediti_correnti,
                    riga.premio_crediti_deposito,
                ) if riga.premio_erogato_at else None,
            })
        payload["risposte"] = righe
    return payload


def inoltra_sospese(sondaggio: Sondaggio) -> dict:
    from personaggi.sondaggi_google import inoltra_risposta_a_google

    esito = {"inviate": 0, "errori": 0, "saltate": 0}
    ids = list(
        sondaggio.risposte.filter(google_inviato_at__isnull=True).values_list("pk", flat=True)
    )
    for pk in ids:
        stato = inoltra_risposta_a_google(pk)
        if stato == "inviata":
            esito["inviate"] += 1
        elif stato == "errore":
            esito["errori"] += 1
        else:
            esito["saltate"] += 1
    return esito
