"""
Servizi per piazzamento scommesse e liquidazione calendari.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from personaggi.scommesse_config import get_config_scommesse
from personaggi.scommesse_evento import personaggio_in_evento_attivo
from personaggi.scommesse_logic import (
    ALLIBRATORE_SIGLA,
    ESITI_VALIDI,
    ESITO_PAREGGIO,
    applica_variazione_potenza_dopo_incontro,
    calcola_probabilita_esito,
    calendario_ancora_visibile,
    margine_allibratore,
    risultati_pubblicati,
)
from personaggi.scommesse_risultati import formatta_risultato, pareggio_consentito
from personaggi.scommesse_models import (
    CalendarioScommesse,
    CodiceScommessa,
    IncontroScommesse,
    PuntataScommessa,
    SelezionePuntata,
)


def _decimal2(value):
    from personaggi.scommesse_logic import _decimal2 as fn
    return fn(value)


def calcola_ritiro_contanti_da_riserva(personaggio, puntata: PuntataScommessa, cfg=None) -> tuple[Decimal, Decimal]:
    """
    Quanto della vincita già in riserva può passare ai crediti liberi (ritiro, residuo_riserva).
    Applica soglia per puntata e tetto per calendario.
    """
    if not puntata.vincita_riscossa:
        return Decimal("0.00"), Decimal("0.00")

    vincita = _decimal2(puntata.vincita or Decimal("0.00"))
    if vincita <= 0:
        return Decimal("0.00"), Decimal("0.00")

    gia_ritirato_puntata = _decimal2(puntata.vincita_ritirata or Decimal("0.00"))
    residuo_puntata = vincita - gia_ritirato_puntata
    if residuo_puntata <= 0:
        return Decimal("0.00"), Decimal("0.00")

    cfg = cfg or get_config_scommesse(puntata.calendario.sport.campagna_id)
    soglia = _decimal2(cfg.soglia_vincita_rilevante)
    max_calendario = _decimal2(cfg.max_ritiro_vincita_calendario)

    gia_ritirato_cal = PuntataScommessa.objects.filter(
        personaggio=personaggio,
        calendario_id=puntata.calendario_id,
        vincita_riscossa=True,
    ).exclude(pk=puntata.pk).aggregate(tot=Sum("vincita_ritirata"))["tot"]
    gia_ritirato_cal = _decimal2(gia_ritirato_cal or Decimal("0.00"))
    cap_residuo_cal = max(Decimal("0.00"), max_calendario - gia_ritirato_cal)

    if vincita > soglia:
        limite_puntata = min(vincita, soglia)
    else:
        limite_puntata = vincita
    max_ancora_puntata = limite_puntata - gia_ritirato_puntata
    if max_ancora_puntata <= 0:
        ritiro = Decimal("0.00")
    else:
        ritiro = min(residuo_puntata, max_ancora_puntata, cap_residuo_cal)

    residuo_riserva = residuo_puntata - ritiro
    return _decimal2(ritiro), _decimal2(residuo_riserva)


def liquidare_calendari_scaduti():
    """Liquida puntate per calendari la cui data_risoluzione è passata."""
    now = timezone.now()
    calendari = CalendarioScommesse.objects.filter(
        liquidato=False,
        data_risoluzione__lte=now,
        attivo=True,
    ).prefetch_related("incontri", "incontri__squadra_casa", "incontri__squadra_trasferta", "puntate__selezioni__incontro", "sport")

    for calendario in calendari:
        with transaction.atomic():
            _liquida_calendario(calendario)


def _liquida_calendario(calendario: CalendarioScommesse):
    cfg = get_config_scommesse(calendario.sport.campagna_id)
    puntate = calendario.puntate.filter(stato=PuntataScommessa.STATO_PENDING).select_related(
        "personaggio", "codice__allibratore"
    ).prefetch_related("selezioni__incontro")

    for puntata in puntate:
        vinta = all(
            sel.esito_scelto == sel.incontro.esito
            for sel in puntata.selezioni.all()
        )
        if vinta:
            vincita = _decimal2(puntata.importo * puntata.quota_totale)
            puntata.stato = PuntataScommessa.STATO_WON
            puntata.vincita = vincita
        else:
            puntata.stato = PuntataScommessa.STATO_LOST
            puntata.vincita = Decimal("0.00")
        puntata.liquidata_at = timezone.now()
        puntata.save(update_fields=["stato", "vincita", "liquidata_at", "updated_at"])

    for incontro in calendario.incontri.select_related("squadra_casa", "squadra_trasferta").all():
        applica_variazione_potenza_dopo_incontro(incontro, cfg)

    calendario.liquidato = True
    calendario.save(update_fields=["liquidato", "updated_at"])


def _quota_selezione(incontro: IncontroScommesse, esito: str, margine_bonus=None, allow_draw: bool = True) -> Decimal:
    base = incontro.quota_per_esito(esito)
    if margine_bonus is None:
        return base
    p_casa, p_pareggio, p_trasf = calcola_probabilita_esito(
        incontro.potenza_casa_effettiva,
        incontro.potenza_trasferta_effettiva,
        allow_draw=allow_draw,
    )
    prob_map = {"1": p_casa, "X": p_pareggio, "2": p_trasf}
    prob = prob_map.get(esito, p_casa)
    return _decimal2(margine_bonus / Decimal(str(prob)))


@transaction.atomic
def piazza_puntata(personaggio, calendario_id, selezioni: list, importo, codice_str=None, usa_riserva=False):
    """
    selezioni: lista di dict {"incontro_id": uuid, "esito": "1"|"X"|"2"}
    usa_riserva: se True, l'importo è scalato dalla riserva (non dai crediti liberi).
    """
    liquidare_calendari_scaduti()

    try:
        calendario = CalendarioScommesse.objects.select_related("sport").get(pk=calendario_id)
    except CalendarioScommesse.DoesNotExist:
        raise ValidationError("Calendario non trovato.")

    cfg = get_config_scommesse(calendario.sport.campagna_id)

    if not calendario.attivo or not calendario_ancora_visibile(calendario):
        raise ValidationError("Calendario non disponibile per scommesse.")
    if risultati_pubblicati(calendario.data_risoluzione):
        raise ValidationError("Il periodo scommesse è chiuso: i risultati sono già pubblicati.")
    if timezone.now() < calendario.data_apertura:
        raise ValidationError("Il calendario non è ancora aperto alle scommesse.")

    if not selezioni:
        raise ValidationError("Seleziona almeno un evento.")
    if len(selezioni) > cfg.max_selezioni_combinata:
        raise ValidationError(f"Massimo {cfg.max_selezioni_combinata} eventi per scommessa combinata.")

    importo = _decimal2(importo)
    if importo <= 0:
        raise ValidationError("Importo non valido.")

    codice_obj = None
    margine_bonus = None
    if codice_str:
        if usa_riserva:
            raise ValidationError("Il codice allibratore non è utilizzabile con la riserva.")
        codice_str = codice_str.strip().upper()
        codice_obj = CodiceScommessa.objects.select_related("allibratore").filter(
            codice=codice_str, usato=False
        ).first()
        if not codice_obj:
            raise ValidationError("Codice scommessa non valido o già utilizzato.")
        valore_all = codice_obj.allibratore.get_valore_statistica(ALLIBRATORE_SIGLA)
        margine_bonus = margine_allibratore(valore_all, cfg)
    else:
        if not usa_riserva and importo > calendario.importo_max_senza_codice:
            raise ValidationError(
                f"Senza codice allibratore il massimo è {calendario.importo_max_senza_codice} CR."
            )

    importo_riserva = Decimal("0.00")
    if usa_riserva:
        riserva_disp = _decimal2(personaggio.riserva)
        if riserva_disp < importo:
            raise ValidationError(
                f"Riserva insufficiente. Disponibile: {riserva_disp} CR, richiesti: {importo} CR."
            )
        importo_riserva = importo
    else:
        if personaggio.crediti < float(importo):
            raise ValidationError(
                f"Crediti insufficienti. Posseduti: {personaggio.crediti}, richiesti: {importo}."
            )

    incontro_ids = [s["incontro_id"] for s in selezioni]
    incontri = {
        str(i.id): i
        for i in IncontroScommesse.objects.filter(
            calendario=calendario,
            id__in=incontro_ids,
        ).select_related("calendario__sport")
    }
    if len(incontri) != len(incontro_ids):
        raise ValidationError("Uno o più incontri non appartengono a questo calendario.")

    quota_totale = Decimal("1.00")
    tipo = PuntataScommessa.TIPO_SINGOLA if len(selezioni) == 1 else PuntataScommessa.TIPO_COMBINATA

    for sel in selezioni:
        esito = sel.get("esito", "").upper()
        if esito not in ESITI_VALIDI:
            raise ValidationError(f"Esito non valido: {esito}")
        incontro = incontri.get(str(sel["incontro_id"]))
        if not incontro:
            raise ValidationError("Incontro non valido.")
        tipo_sport = calendario.sport.tipo_risultato
        if esito == ESITO_PAREGGIO and not pareggio_consentito(tipo_sport):
            raise ValidationError("Il pareggio non è disponibile per questo sport.")
        q = _quota_selezione(incontro, esito, margine_bonus, allow_draw=pareggio_consentito(tipo_sport))
        quota_totale *= q

    quota_totale = _decimal2(quota_totale)

    if usa_riserva:
        personaggio.riserva = _decimal2(personaggio.riserva - importo_riserva)
        personaggio.save(update_fields=["riserva", "updated_at"])
    else:
        personaggio.modifica_crediti(
            float(-importo),
            f"Scommessa {tipo.lower()} ({calendario.titolo or calendario.sport.nome})",
        )

    if codice_obj:
        codice_obj.usato = True
        codice_obj.usato_at = timezone.now()
        codice_obj.save(update_fields=["usato", "usato_at", "updated_at"])
        commissione = _decimal2(importo * cfg.commissione_allibratore_pct)
        if commissione > 0:
            codice_obj.allibratore.modifica_crediti(
                float(commissione),
                f"Commissione allibratore codice {codice_obj.codice}",
            )

    puntata = PuntataScommessa.objects.create(
        personaggio=personaggio,
        calendario=calendario,
        codice=codice_obj,
        importo=importo,
        importo_riserva=importo_riserva,
        tipo=tipo,
        quota_totale=quota_totale,
    )

    for sel in selezioni:
        SelezionePuntata.objects.create(
            puntata=puntata,
            incontro=incontri[str(sel["incontro_id"])],
            esito_scelto=sel["esito"].upper(),
        )

    return puntata


@transaction.atomic
def riscuoti_vincita(personaggio, puntata_id):
    """Versa l'intera vincita nella riserva del giocatore."""
    try:
        puntata = (
            PuntataScommessa.objects.select_for_update()
            .select_related("calendario__sport", "personaggio")
            .get(pk=puntata_id, personaggio=personaggio)
        )
    except PuntataScommessa.DoesNotExist:
        raise ValidationError("Puntata non trovata.")

    if not risultati_pubblicati(puntata.calendario.data_risoluzione):
        raise ValidationError("I risultati non sono ancora stati pubblicati.")

    if puntata.stato != PuntataScommessa.STATO_WON:
        raise ValidationError("Questa puntata non ha una vincita da riscuotere.")
    if puntata.vincita_riscossa:
        raise ValidationError("Vincita già versata in riserva.")
    vincita = puntata.vincita or Decimal("0.00")
    if vincita <= 0:
        raise ValidationError("Importo vincita non valido.")

    versato = _decimal2(vincita)
    personaggio.riserva = _decimal2(personaggio.riserva + versato)
    personaggio.save(update_fields=["riserva", "updated_at"])

    puntata.vincita_riscossa = True
    puntata.vincita_versata_riserva = versato
    puntata.vincita_ritirata = Decimal("0.00")
    puntata.riscossa_at = timezone.now()
    puntata.save(update_fields=[
        "vincita_riscossa", "vincita_versata_riserva", "vincita_ritirata", "riscossa_at", "updated_at",
    ])
    return puntata


@transaction.atomic
def ritira_da_riserva(personaggio, puntata_id):
    """Preleva dalla riserva e accredita ai crediti liberi (solo durante evento attivo)."""
    if not personaggio_in_evento_attivo(personaggio):
        raise ValidationError(
            "Il ritiro in contanti dalla riserva è consentito solo durante un evento attivo a cui partecipi."
        )

    try:
        puntata = (
            PuntataScommessa.objects.select_for_update()
            .select_related("calendario__sport", "personaggio")
            .get(pk=puntata_id, personaggio=personaggio)
        )
    except PuntataScommessa.DoesNotExist:
        raise ValidationError("Puntata non trovata.")

    if not puntata.vincita_riscossa:
        raise ValidationError("Versa prima la vincita in riserva.")

    cfg = get_config_scommesse(puntata.calendario.sport.campagna_id)
    ritiro, _ = calcola_ritiro_contanti_da_riserva(personaggio, puntata, cfg)
    if ritiro <= 0:
        raise ValidationError("Nessun importo ritirabile in contanti per questa puntata.")

    riserva_disp = _decimal2(personaggio.riserva)
    if riserva_disp < ritiro:
        raise ValidationError("Saldo riserva insufficiente.")

    personaggio.riserva = _decimal2(riserva_disp - ritiro)
    personaggio.save(update_fields=["riserva", "updated_at"])
    personaggio.modifica_crediti(
        float(ritiro),
        f"Ritiro riserva scommesse ({puntata.calendario.titolo or puntata.calendario.sport.nome})",
    )

    puntata.vincita_ritirata = _decimal2((puntata.vincita_ritirata or Decimal("0.00")) + ritiro)
    puntata.save(update_fields=["vincita_ritirata", "updated_at"])
    return puntata


def storico_risultati_squadra(squadra_id, limit=12):
    """Ultimi incontri con risultato pubblicato per una squadra."""
    from django.db.models import Q

    from personaggi.scommesse_models import IncontroScommesse, SquadraScommesse

    squadra = SquadraScommesse.objects.filter(pk=squadra_id, attiva=True).select_related("sport").first()
    if not squadra:
        return None

    now = timezone.now()
    incontri = (
        IncontroScommesse.objects.filter(
            Q(squadra_casa_id=squadra_id) | Q(squadra_trasferta_id=squadra_id),
            calendario__data_risoluzione__lte=now,
            calendario__attivo=True,
        )
        .select_related(
            "calendario__sport",
            "squadra_casa",
            "squadra_trasferta",
        )
        .order_by("-calendario__data_risoluzione", "-ordine")[:limit]
    )

    righe = []
    for inc in incontri:
        is_casa = str(inc.squadra_casa_id) == str(squadra_id)
        avversario = inc.squadra_trasferta if is_casa else inc.squadra_casa
        if inc.esito == "X":
            esito = "P"
        elif (is_casa and inc.esito == "1") or (not is_casa and inc.esito == "2"):
            esito = "V"
        else:
            esito = "S"
        tipo_risultato = inc.calendario.sport.tipo_risultato
        punti_fatti = inc.gol_casa if is_casa else inc.gol_trasferta
        punti_subiti = inc.gol_trasferta if is_casa else inc.gol_casa
        righe.append({
            "data_risoluzione": inc.calendario.data_risoluzione,
            "calendario_titolo": inc.calendario.titolo or inc.calendario.sport.nome,
            "sport_nome": inc.calendario.sport.nome,
            "tipo_risultato": tipo_risultato,
            "avversario_id": avversario.id,
            "avversario_nome": avversario.nome,
            "in_casa": is_casa,
            "esito": esito,
            "gol_fatti": punti_fatti,
            "gol_subiti": punti_subiti,
            "risultato_formattato": formatta_risultato(tipo_risultato, inc.gol_casa, inc.gol_trasferta),
        })

    return {
        "squadra": {
            "id": squadra.id,
            "nome": squadra.nome,
            "sport_nome": squadra.sport.nome,
        },
        "risultati": righe,
    }
