"""
Servizi per piazzamento scommesse e liquidazione calendari.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from personaggi.scommesse_config import get_config_scommesse
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
            puntata.personaggio.modifica_crediti(
                float(vincita),
                f"Scommessa vinta ({calendario.titolo or calendario.sport.nome})",
            )
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
def piazza_puntata(personaggio, calendario_id, selezioni: list, importo, codice_str=None):
    """
    selezioni: lista di dict {"incontro_id": uuid, "esito": "1"|"X"|"2"}
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
        codice_str = codice_str.strip().upper()
        codice_obj = CodiceScommessa.objects.select_related("allibratore").filter(
            codice=codice_str, usato=False
        ).first()
        if not codice_obj:
            raise ValidationError("Codice scommessa non valido o già utilizzato.")
        valore_all = codice_obj.allibratore.get_valore_statistica(ALLIBRATORE_SIGLA)
        margine_bonus = margine_allibratore(valore_all, cfg)
    else:
        if importo > calendario.importo_max_senza_codice:
            raise ValidationError(
                f"Senza codice allibratore il massimo è {calendario.importo_max_senza_codice} CR."
            )

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
            "potenza_squadra_al_match": inc.potenza_casa_effettiva if is_casa else inc.potenza_trasferta_effettiva,
            "potenza_avversario_al_match": inc.potenza_trasferta_effettiva if is_casa else inc.potenza_casa_effettiva,
        })

    return {
        "squadra": {
            "id": squadra.id,
            "nome": squadra.nome,
            "potenza": squadra.potenza,
            "sport_nome": squadra.sport.nome,
        },
        "risultati": righe,
    }
