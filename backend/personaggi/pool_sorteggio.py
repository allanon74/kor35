"""
Sorteggio pesato di personaggi da un pool staff.

Peso = fattore ** sorteggi_pregressi nel pool.
Esempio: fattore 0.8 e 2 estrazioni precedenti → 0.64.
"""

from __future__ import annotations

import random
import re
from decimal import Decimal
from typing import Any, Iterable, Sequence

from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import strip_tags

TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")

PLACEHOLDER_CAMPI = (
    {
        "token": "{{nome_personaggio}}",
        "descrizione": "Nome del personaggio estratto",
    },
    {
        "token": "{{nome_giocatore}}",
        "descrizione": "Nome e cognome del giocatore (fallback: username)",
    },
    {
        "token": "{{username_giocatore}}",
        "descrizione": "Username del giocatore proprietario",
    },
    {
        "token": "{{nome_evento}}",
        "descrizione": "Titolo dell'evento in corso (se presente)",
    },
    {
        "token": "{{nome_pool}}",
        "descrizione": "Nome del pool da cui è stato estratto",
    },
    {
        "token": "{{data_sorteggio}}",
        "descrizione": "Data e ora del sorteggio",
    },
)


def giocatore_display_name(user) -> str:
    if not user:
        return ""
    full = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return full or user.username or ""


def peso_sorteggio(fattore: float, sorteggi_pregressi: int) -> float:
    n = max(0, int(sorteggi_pregressi or 0))
    f = float(fattore)
    if n == 0:
        return 1.0
    return f ** n


def campiona_pesato(
    candidati: Sequence[tuple[Any, float]],
    k: int,
    *,
    rng: random.Random | None = None,
) -> list[Any]:
    """Estrazione senza reinserimento. Se tutti i pesi sono 0, uniforme sui restanti."""
    rng = rng or random.Random()
    pool = [(item, float(w)) for item, w in candidati]
    k = max(0, min(int(k), len(pool)))
    scelti: list[Any] = []
    for _ in range(k):
        if not pool:
            break
        totale = sum(w for _, w in pool)
        if totale <= 0:
            idx = rng.randrange(len(pool))
        else:
            r = rng.random() * totale
            acc = 0.0
            idx = len(pool) - 1
            for i, (_, w) in enumerate(pool):
                acc += max(w, 0.0)
                if r <= acc:
                    idx = i
                    break
        item, _w = pool.pop(idx)
        scelti.append(item)
    return scelti


def render_placeholders(testo: str, context: dict[str, str]) -> str:
    if not testo:
        return ""

    def _sub(match: re.Match) -> str:
        key = match.group(1)
        return context.get(key, match.group(0))

    return TOKEN_RE.sub(_sub, testo)


def placeholder_context(*, personaggio, pool, evento=None, when=None) -> dict[str, str]:
    user = getattr(personaggio, "proprietario", None)
    when = when or timezone.now()
    evento_nome = ""
    if evento is not None:
        evento_nome = getattr(evento, "titolo", "") or ""
    return {
        "nome_personaggio": getattr(personaggio, "nome", "") or "",
        "nome_giocatore": giocatore_display_name(user),
        "username_giocatore": getattr(user, "username", "") or "",
        "nome_evento": evento_nome,
        "nome_pool": getattr(pool, "nome", "") or "",
        "data_sorteggio": timezone.localtime(when).strftime("%d/%m/%Y %H:%M"),
    }


def conteggi_sorteggi_pool(pool) -> dict[int, int]:
    from personaggi.models import PersonaggioPoolSorteggioEsito

    rows = (
        PersonaggioPoolSorteggioEsito.objects.filter(pool=pool)
        .values("personaggio_id")
        .annotate(n=Count("id"))
    )
    return {row["personaggio_id"]: int(row["n"]) for row in rows}


def membri_attivi_qs(pool):
    from personaggi.models import Personaggio

    qs = Personaggio.objects.filter(
        pool_sorteggio_membri__pool=pool,
        pool_sorteggio_membri__attivo=True,
        campagna=pool.campagna,
        eliminato_at__isnull=True,
    ).select_related("proprietario", "tipologia")
    if pool.escludi_png:
        qs = qs.filter(tipologia__giocante=True)
    return qs.distinct()


def evento_in_corso():
    from gestione_plot.models import Evento

    now = timezone.now()
    return (
        Evento.objects.filter(
            Q(started_at__isnull=False, ended_at__isnull=True)
            | Q(started_at__isnull=True, data_inizio__lte=now, data_fine__gte=now)
        )
        .order_by("-data_inizio")
        .first()
    )


def preview_testo_html(html: str) -> str:
    plain = strip_tags(html or "")
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain[:180]


def client_ip(request) -> str | None:
    if not request:
        return None
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    raw = forwarded or request.META.get("REMOTE_ADDR") or ""
    return raw[:45] or None


ULTIMI_ESITI_GIOCATORE = 15


def inizio_giorno_locale(when=None):
    """Inizio del giorno civile nel fuso TIME_ZONE (non UTC)."""
    when = timezone.localtime(when or timezone.now())
    return when.replace(hour=0, minute=0, second=0, microsecond=0)


def conteggio_attivazioni_giocatore_oggi(pool, personaggio, when=None) -> int:
    from personaggi.models import PersonaggioPoolSorteggio

    if not pool or not personaggio or not getattr(pool, "pk", None):
        return 0
    start = inizio_giorno_locale(when)
    return PersonaggioPoolSorteggio.objects.filter(
        pool=pool,
        origine=PersonaggioPoolSorteggio.ORIGINE_GIOCATORE,
        avviato_da_personaggio=personaggio,
        created_at__gte=start,
    ).count()


def rimanenti_attivazioni_giocatore(pool, personaggio, when=None) -> int:
    massimo = int(getattr(pool, "max_sorteggi_giorno", 0) or 0)
    if massimo <= 0:
        return 0
    usati = conteggio_attivazioni_giocatore_oggi(pool, personaggio, when=when)
    return max(0, massimo - usati)


def pool_visibile_per_personaggio(pool, personaggio) -> bool:
    """Tab giocatore: statistica impostata e valore effettivo PG > 0."""
    if not pool or not personaggio:
        return False
    stat = getattr(pool, "statistica", None)
    if not stat:
        return False
    sigla = (getattr(stat, "sigla", None) or "").strip()
    if not sigla:
        return False
    try:
        return int(personaggio.get_valore_statistica(sigla) or 0) > 0
    except Exception:
        return False


def payload_pool_giocatore(pool, personaggio, *, include_esiti=False) -> dict:
    massimo = int(getattr(pool, "max_sorteggi_giorno", 0) or 0)
    usati = conteggio_attivazioni_giocatore_oggi(pool, personaggio)
    rimanenti = max(0, massimo - usati) if massimo > 0 else 0
    stat = getattr(pool, "statistica", None)
    data = {
        "id": str(pool.id),
        "nome": pool.nome,
        "statistica_id": stat.id if stat else None,
        "statistica_sigla": (stat.sigla if stat else "") or "",
        "statistica_nome": (stat.nome if stat else "") or "",
        "max_sorteggi_giorno": massimo,
        "usati_oggi": usati,
        "rimanenti": rimanenti,
        "puo_attivare": rimanenti > 0,
        "sorteggio_min": pool.sorteggio_min,
        "sorteggio_max": pool.sorteggio_max,
    }
    if include_esiti:
        data["ultimi_esiti"] = ultimi_esiti_giocatore(pool)
    return data


def ultimi_esiti_giocatore(pool, *, limit: int = ULTIMI_ESITI_GIOCATORE) -> list[dict]:
    from personaggi.models import PersonaggioPoolSorteggioEsito

    qs = (
        PersonaggioPoolSorteggioEsito.objects.filter(pool=pool)
        .select_related("personaggio")
        .order_by("-created_at")[: max(1, int(limit))]
    )
    rows = []
    for e in qs:
        pg = e.personaggio
        rows.append(
            {
                "id": str(e.id),
                "personaggio_nome": pg.nome if pg else "",
                "created_at": e.created_at,
            }
        )
    return rows
