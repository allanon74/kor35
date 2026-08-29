"""Generazione feed iCal: eventi per tutti; compiti per helper/staff/master."""
from __future__ import annotations

import re
from datetime import timedelta, timezone as dt_timezone

from django.utils import timezone
from django.utils.html import strip_tags


def _ics_escape(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _ics_dt(value) -> str:
    if value is None:
        return ""
    dt = timezone.localtime(value) if timezone.is_aware(value) else value
    utc = dt.astimezone(dt_timezone.utc)
    return utc.strftime("%Y%m%dT%H%M%SZ")


def _plain(text: str) -> str:
    raw = strip_tags(text or "")
    raw = re.sub(r"\s+", " ", raw.replace("\xa0", " ")).strip()
    return raw


def user_ics_includes_compiti(user) -> bool:
    from personaggi.models import CAMPAGNA_ROLES_COMPITO, CampagnaUtente

    if not user:
        return False
    return CampagnaUtente.objects.filter(
        user=user,
        attivo=True,
        ruolo__in=CAMPAGNA_ROLES_COMPITO,
    ).exists()


def calendario_ics_path(token) -> str:
    return f"/api/plot/api/calendario.ics?token={token}"


def calendario_feed_payload(user) -> dict:
    from gestione_plot.models import CalendarioFeedToken

    token_row, _ = CalendarioFeedToken.objects.get_or_create(user=user)
    return {
        "token": str(token_row.token),
        "path": calendario_ics_path(token_row.token),
        "include_compiti": user_ics_includes_compiti(user),
    }


def eventi_queryset_for_ics():
    from gestione_plot.models import Evento

    cutoff = timezone.now() - timedelta(days=30)
    return (
        Evento.objects.filter(data_fine__gte=cutoff, iscrizione_test_attiva=False)
        .order_by("data_inizio")
    )


def assegnazioni_queryset_for_ics(user):
    from gestione_plot.models import StaffCompitoAssegnazione

    cutoff = timezone.now() - timedelta(days=14)
    assegnazioni = (
        StaffCompitoAssegnazione.objects.filter(user=user, compito__attivo=True)
        .select_related("compito")
        .order_by("compito__scadenza")
    )
    return [
        row
        for row in assegnazioni
        if row.completato_at is None or (row.completato_at and row.completato_at >= cutoff)
    ]


def build_calendario_ics(
    *,
    eventi=None,
    assegnazioni=None,
    calendar_name="KOR35",
    include_compiti=False,
) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//KOR35//Calendario//IT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_ics_escape(calendar_name)}",
    ]
    now = timezone.now()
    for ev in eventi or []:
        if not ev or not ev.data_inizio:
            continue
        uid = f"evento-{ev.pk}@kor35"
        dtstart = _ics_dt(ev.data_inizio)
        dtend = _ics_dt(ev.data_fine or (ev.data_inizio + timedelta(hours=2)))
        stamp = _ics_dt(getattr(ev, "updated_at", None) or now)
        desc = _plain(ev.sinossi or "")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:{_ics_escape(ev.titolo)}",
            ]
        )
        if desc:
            lines.append(f"DESCRIPTION:{_ics_escape(desc)}")
        if ev.luogo:
            lines.append(f"LOCATION:{_ics_escape(ev.luogo)}")
        lines.append("END:VEVENT")

    if include_compiti:
        _append_compiti(lines, assegnazioni or [], now)

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def _append_compiti(lines: list[str], assegnazioni, now) -> None:
    for row in assegnazioni:
        compito = row.compito
        if not compito or not compito.attivo or not compito.scadenza:
            continue
        uid = f"staff-compito-{row.id}@kor35"
        dtstart = _ics_dt(compito.scadenza)
        dtend = _ics_dt(compito.scadenza + timedelta(minutes=30))
        stamp = _ics_dt(compito.updated_at or now)
        desc_parts = [compito.descrizione or ""]
        if row.completato_at:
            desc_parts.append("Completato.")
        description = _ics_escape("\n".join(p for p in desc_parts if p).strip())
        summary = _ics_escape(compito.titolo)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:{summary}",
            ]
        )
        if description:
            lines.append(f"DESCRIPTION:{description}")
        if compito.preavviso_minuti:
            lines.extend(
                [
                    "BEGIN:VALARM",
                    f"TRIGGER:-PT{int(compito.preavviso_minuti)}M",
                    "ACTION:DISPLAY",
                    f"DESCRIPTION:{summary}",
                    "END:VALARM",
                ]
            )
        lines.append("END:VEVENT")


def build_compiti_ics(assegnazioni, *, calendar_name="KOR35 compiti") -> str:
    """Compat: solo VEVENT dei compiti (test / usi interni)."""
    return build_calendario_ics(
        assegnazioni=assegnazioni,
        calendar_name=calendar_name,
        include_compiti=True,
    )
