"""
Programmazione automatica giornate torneo a cadenza fissa (es. ogni 14 giorni) tra un evento LARP e il successivo.
Le giornate in evento restano manuali (genera-per-evento / calendario staff).
"""
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from gestione_plot.models import Evento
from personaggi.scommesse_config import get_config_scommesse
from personaggi.scommesse_models import CalendarioScommesse, ProgrammazioneTorneoScommesse


def eventi_programmabili(sport) -> list[Evento]:
    """Eventi futuri senza calendario già creato per questo sport (solo uso manuale staff)."""
    now = timezone.now()
    ids_con_calendario = CalendarioScommesse.objects.filter(
        sport=sport,
        evento_id__isnull=False,
    ).values_list("evento_id", flat=True)
    return list(
        Evento.objects.filter(data_inizio__gt=now)
        .exclude(pk__in=ids_con_calendario)
        .order_by("data_inizio")
    )


def calcola_date_calendario(evento: Evento, programmazione: ProgrammazioneTorneoScommesse):
    """Finestra scommesse manuale legata a evento: apertura prima, chiusura poco prima dell'inizio."""
    data_risoluzione = evento.data_inizio - timezone.timedelta(
        hours=int(programmazione.ore_chiusura_prima_evento)
    )
    data_apertura = evento.data_inizio - timezone.timedelta(
        hours=int(programmazione.ore_apertura_prima_evento)
    )
    if data_risoluzione <= data_apertura:
        data_apertura = data_risoluzione - timezone.timedelta(hours=24)
    return data_apertura, data_risoluzione


def _ancora_cadenza(programmazione: ProgrammazioneTorneoScommesse) -> datetime:
    if programmazione.data_ancora_cadenza:
        ancora = programmazione.data_ancora_cadenza
    else:
        ancora = programmazione.created_at
    if timezone.is_naive(ancora):
        ancora = timezone.make_aware(ancora, timezone.get_current_timezone())
    return ancora


def _combine_data_ora(data, ora) -> datetime:
    tz = timezone.get_current_timezone()
    combined = datetime.combine(data, ora)
    if timezone.is_naive(combined):
        return timezone.make_aware(combined, tz)
    return combined


def _ultima_giornata_automatica(programmazione: ProgrammazioneTorneoScommesse):
    return (
        CalendarioScommesse.objects.filter(
            programmazione=programmazione,
            evento__isnull=True,
        )
        .order_by("-data_risoluzione")
        .first()
    )


def prossima_finestra_cadenza(programmazione: ProgrammazioneTorneoScommesse) -> tuple[datetime, datetime]:
    """
    Calcola apertura/risoluzione della prossima giornata automatica da creare.
    Se l'ultima giornata auto esiste, avanza di intervallo_giorni; altrimenti usa ancoraggio + sfasamento.
    """
    interval = max(1, int(programmazione.intervallo_giorni))
    offset = int(programmazione.sfasamento_giorni)
    giorni_apertura = max(1, int(programmazione.giorni_apertura))
    ora_res = programmazione.ora_risoluzione

    ultima = _ultima_giornata_automatica(programmazione)
    if ultima:
        data_risoluzione = ultima.data_risoluzione + timedelta(days=interval)
    else:
        ancora = _ancora_cadenza(programmazione)
        prima_risoluzione = _combine_data_ora(ancora.date() + timedelta(days=offset), ora_res)
        if prima_risoluzione <= ancora:
            giorni_passati = (timezone.now().date() - (ancora.date() + timedelta(days=offset))).days
            periodi = max(0, giorni_passati // interval)
            data_risoluzione = prima_risoluzione + timedelta(days=periodi * interval)
            while data_risoluzione <= timezone.now():
                data_risoluzione += timedelta(days=interval)
        else:
            data_risoluzione = prima_risoluzione

    data_apertura = data_risoluzione - timedelta(days=giorni_apertura)
    if data_apertura >= data_risoluzione:
        data_apertura = data_risoluzione - timedelta(hours=24)
    return data_apertura, data_risoluzione


def _giornata_cadenza_gia_creata(programmazione: ProgrammazioneTorneoScommesse, giornata_numero: int) -> bool:
    return CalendarioScommesse.objects.filter(
        programmazione=programmazione,
        evento__isnull=True,
        giornata_numero=giornata_numero,
    ).exists()


@transaction.atomic
def genera_calendario_cadenza(
    programmazione: ProgrammazioneTorneoScommesse,
    data_apertura: datetime,
    data_risoluzione: datetime,
):
    """Crea calendario + incontri sulla cadenza temporale (senza evento LARP)."""
    sport = programmazione.sport
    squadre_attive = sport.squadre.filter(attiva=True).count()
    if squadre_attive < 2:
        raise ValidationError(f"Servono almeno 2 squadre attive per {sport.nome}.")

    giornata_numero = programmazione.giornata_corrente + 1
    if _giornata_cadenza_gia_creata(programmazione, giornata_numero):
        raise ValidationError(f"Giornata {giornata_numero} già generata per {sport.nome}.")

    cfg = get_config_scommesse(sport.campagna_id)
    calendario = CalendarioScommesse.objects.create(
        sport=sport,
        titolo=f"Giornata {giornata_numero}",
        data_apertura=data_apertura,
        data_risoluzione=data_risoluzione,
        importo_max_senza_codice=cfg.importo_max_senza_codice_default,
        evento=None,
        giornata_numero=giornata_numero,
        programmazione=programmazione,
    )
    calendario.genera_incontri(
        strategia=programmazione.strategia_accoppiamento,
        giornata_index=programmazione.giornata_corrente,
    )

    programmazione.giornata_corrente = giornata_numero
    programmazione.save(update_fields=["giornata_corrente", "updated_at"])
    return calendario


@transaction.atomic
def genera_calendario_per_evento(
    programmazione: ProgrammazioneTorneoScommesse,
    evento: Evento,
):
    """Crea calendario + incontri per un evento LARP (azione manuale staff)."""
    sport = programmazione.sport
    if CalendarioScommesse.objects.filter(sport=sport, evento=evento).exists():
        raise ValidationError(f"Esiste già un calendario per {sport.nome} legato a «{evento.titolo}».")

    squadre_attive = sport.squadre.filter(attiva=True).count()
    if squadre_attive < 2:
        raise ValidationError(f"Servono almeno 2 squadre attive per {sport.nome}.")

    data_apertura, data_risoluzione = calcola_date_calendario(evento, programmazione)
    giornata_numero = programmazione.giornata_corrente + 1
    cfg = get_config_scommesse(sport.campagna_id)

    calendario = CalendarioScommesse.objects.create(
        sport=sport,
        titolo=f"Giornata {giornata_numero} — {evento.titolo}",
        data_apertura=data_apertura,
        data_risoluzione=data_risoluzione,
        importo_max_senza_codice=cfg.importo_max_senza_codice_default,
        evento=evento,
        giornata_numero=giornata_numero,
        programmazione=programmazione,
    )
    calendario.genera_incontri(
        strategia=programmazione.strategia_accoppiamento,
        giornata_index=programmazione.giornata_corrente,
    )

    programmazione.giornata_corrente = giornata_numero
    programmazione.ultimo_evento = evento
    programmazione.save(update_fields=["giornata_corrente", "ultimo_evento", "updated_at"])
    return calendario


def sincronizza_programmazione(
    programmazione: ProgrammazioneTorneoScommesse,
    *,
    max_crea: int = 3,
) -> list[CalendarioScommesse]:
    """Genera fino a max_crea giornate automatiche se la cadenza è scaduta."""
    if not programmazione.attiva or not programmazione.auto_genera:
        return []

    creati = []
    now = timezone.now()
    for _ in range(max_crea):
        data_apertura, data_risoluzione = prossima_finestra_cadenza(programmazione)
        if now < data_apertura:
            break
        giornata_numero = programmazione.giornata_corrente + 1
        if _giornata_cadenza_gia_creata(programmazione, giornata_numero):
            break
        try:
            cal = genera_calendario_cadenza(programmazione, data_apertura, data_risoluzione)
            creati.append(cal)
            programmazione.refresh_from_db()
        except ValidationError:
            break
    return creati


def sincronizza_tutte_programmazioni(*, max_crea_per_sport: int = 1) -> dict:
    """Entry point per cron/timer: sincronizza tutte le programmazioni attive."""
    report = {"creati": [], "errori": []}
    qs = ProgrammazioneTorneoScommesse.objects.filter(attiva=True).select_related("sport")
    for prog in qs:
        try:
            creati = sincronizza_programmazione(prog, max_crea=max_crea_per_sport)
            for cal in creati:
                report["creati"].append({
                    "sport": prog.sport.nome,
                    "calendario_id": str(cal.id),
                    "titolo": cal.titolo,
                    "evento": cal.evento.titolo if cal.evento_id else None,
                })
        except Exception as exc:
            report["errori"].append({"sport": prog.sport.nome, "errore": str(exc)})
    return report


def stato_programmazione(programmazione: ProgrammazioneTorneoScommesse) -> dict:
    """Anteprima prossima giornata a cadenza e eventi disponibili per generazione manuale."""
    data_apertura, data_risoluzione = prossima_finestra_cadenza(programmazione)
    now = timezone.now()
    prossima_giornata_numero = programmazione.giornata_corrente + 1
    gia_creata = _giornata_cadenza_gia_creata(programmazione, prossima_giornata_numero)

    prossimi = eventi_programmabili(programmazione.sport)[:5]
    anteprima_eventi = []
    for ev in prossimi:
        apertura, risoluzione = calcola_date_calendario(ev, programmazione)
        anteprima_eventi.append({
            "evento_id": ev.id,
            "evento_titolo": ev.titolo,
            "data_inizio_evento": ev.data_inizio.isoformat(),
            "data_apertura_prevista": apertura.isoformat(),
            "data_risoluzione_prevista": risoluzione.isoformat(),
            "giornata_numero": programmazione.giornata_corrente + 1 + len(anteprima_eventi),
        })

    ultima_auto = _ultima_giornata_automatica(programmazione)
    return {
        "prossima_giornata_cadenza": {
            "giornata_numero": prossima_giornata_numero,
            "data_apertura_prevista": data_apertura.isoformat(),
            "data_risoluzione_prevista": data_risoluzione.isoformat(),
            "pronta": now >= data_apertura and not gia_creata,
            "gia_creata": gia_creata,
        },
        "prossimi_eventi": anteprima_eventi,
        "ultima_giornata_auto": (
            {
                "titolo": ultima_auto.titolo,
                "data_risoluzione": ultima_auto.data_risoluzione.isoformat(),
                "giornata_numero": ultima_auto.giornata_numero,
            }
            if ultima_auto
            else None
        ),
        "calendari_generati": CalendarioScommesse.objects.filter(
            sport=programmazione.sport,
            programmazione=programmazione,
        ).count(),
    }
