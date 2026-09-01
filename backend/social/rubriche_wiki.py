"""
Pubblicazione off-game delle rubriche: pagine Wiki generate dal DB.

Una pagina per rubrica (posizionabile nel menu dallo staff) e una sottopagina per
ogni articolo pubblicato. Le pagine sono di sola lettura: like e commenti restano
esclusiva della sezione Rubriche di InstaFame.

I `sync_id` delle pagine sono derivati in modo deterministico dai `sync_id` di
rubrica e articolo: nodi diversi generano la stessa pagina e il sync LWW non
produce collisioni sullo slug unique di PaginaRegolamento.
"""

from __future__ import annotations

import logging
import uuid

from django.db import transaction
from django.utils import timezone
from django.utils.html import escape
from django.utils.text import slugify

from gestione_plot.models import PaginaRegolamento

from .models_rubriche import RUBRICA_ARTICOLO_PUBBLICATO, RUBRICA_WIKI_AUTENTICATI, Rubrica

logger = logging.getLogger(__name__)

NAMESPACE_RUBRICHE_WIKI = uuid.UUID("6f4c1f2a-6a3e-5b7d-9c11-0f6b2a4d8e31")
SLUG_MAX_LEN = PaginaRegolamento._meta.get_field("slug").max_length or 50


def sync_id_pagina_rubrica(rubrica) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE_RUBRICHE_WIKI, f"rubrica:{rubrica.sync_id}")


def sync_id_pagina_articolo(articolo) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE_RUBRICHE_WIKI, f"articolo:{articolo.sync_id}")


def _slug_wiki(base: str, sync_id: uuid.UUID) -> str:
    """Slug leggibile ma sempre entro il limite del campo e stabile tra i nodi."""
    radice = slugify(base) or "rubrica"
    if len(radice) <= SLUG_MAX_LEN:
        candidato = radice
    else:
        suffisso = f"-{str(sync_id).replace('-', '')[:6]}"
        candidato = f"{radice[: SLUG_MAX_LEN - len(suffisso)]}{suffisso}"
    conflitto = (
        PaginaRegolamento.objects.filter(slug=candidato).exclude(sync_id=sync_id).exists()
    )
    if not conflitto:
        return candidato
    suffisso = f"-{str(sync_id).replace('-', '')[:6]}"
    return f"{candidato[: SLUG_MAX_LEN - len(suffisso)]}{suffisso}"


def slug_pagina_rubrica(rubrica) -> str:
    return _slug_wiki(f"rubrica-{rubrica.slug}", sync_id_pagina_rubrica(rubrica))


def slug_pagina_articolo(articolo) -> str:
    return _slug_wiki(
        f"rubrica-{articolo.rubrica.slug}-{articolo.slug}", sync_id_pagina_articolo(articolo)
    )


def _media_src(field_file) -> str | None:
    if not field_file or not getattr(field_file, "name", ""):
        return None
    try:
        return field_file.url
    except Exception:
        return None


def _data_leggibile(valore) -> str:
    if not valore:
        return ""
    return timezone.localtime(valore).strftime("%d/%m/%Y")


def html_articolo(articolo) -> str:
    """Corpo HTML della pagina wiki di un articolo (nessuna interazione social)."""
    from .rubriche_markers import (
        expand_corpo_markers,
        figure_html_for_meta,
        immagini_non_posizionate,
    )

    colore = escape(articolo.rubrica.colore_accento or "#b91c1c")
    parti: list[str] = ['<div class="rubrica-articolo">']

    if articolo.occhiello:
        parti.append(
            f'<p style="color:{colore};font-weight:700;letter-spacing:.08em;'
            f'text-transform:uppercase;margin-bottom:.25rem">{escape(articolo.occhiello)}</p>'
        )
    if articolo.sottotitolo:
        parti.append(f"<h3><em>{escape(articolo.sottotitolo)}</em></h3>")

    riga_firma = [f"di {escape(articolo.firma)}"]
    data = _data_leggibile(articolo.data_pubblicazione or articolo.created_at)
    if data:
        riga_firma.append(data)
    riga_firma.append(f"{articolo.tempo_lettura_min} min di lettura")
    parti.append(f'<p><small>{escape(" · ".join(riga_firma))}</small></p>')

    hero = _media_src(articolo.hero_immagine)
    if hero:
        didascalia = (
            f"<figcaption>{escape(articolo.hero_didascalia)}</figcaption>"
            if articolo.hero_didascalia
            else ""
        )
        parti.append(
            f'<figure><img src="{escape(hero)}" alt="{escape(articolo.titolo)}">{didascalia}</figure>'
        )

    if articolo.sommario:
        parti.append(
            f'<blockquote style="border-left:4px solid {colore}">'
            f"{escape(articolo.sommario)}</blockquote>"
        )

    immagini = list(articolo.immagini.all())
    immagini_by_id = {}
    for riga in immagini:
        src = _media_src(riga.immagine)
        if not src:
            continue
        immagini_by_id[str(riga.id).lower()] = {
            "url": src,
            "didascalia": riga.didascalia or "",
            "layout": riga.layout or "full",
        }

    if articolo.corpo:
        parti.append(
            expand_corpo_markers(
                articolo.corpo, immagini_by_id, titolo_fallback=articolo.titolo or ""
            )
        )

    appendice = immagini_non_posizionate(articolo.corpo or "", immagini)
    if appendice:
        parti.append('<div class="rubrica-galleria" style="clear:both;margin-top:1rem;">')
        for riga in appendice:
            src = _media_src(riga.immagine)
            if not src:
                continue
            parti.append(
                figure_html_for_meta(
                    {
                        "url": src,
                        "didascalia": riga.didascalia or "",
                        "layout": riga.layout or "full",
                    },
                    titolo_fallback=articolo.titolo or "",
                )
            )
        parti.append("</div>")

    video = _media_src(articolo.video)
    if video:
        parti.append(f'<p><video src="{escape(video)}" controls style="max-width:100%"></video></p>')

    parti.append("</div>")
    parti.append(
        "<hr><p><small>Articolo della rubrica "
        f"<strong>{escape(articolo.rubrica.nome)}</strong>. Pagina generata automaticamente: "
        "le modifiche vanno fatte dalla sezione Rubriche (InstaFame o Dashboard staff).</small></p>"
    )
    return "\n".join(parti)


def html_indice_rubrica(rubrica, articoli_e_slug) -> str:
    colore = escape(rubrica.colore_accento or "#b91c1c")
    parti: list[str] = []
    if rubrica.sottotitolo:
        parti.append(f"<p><em>{escape(rubrica.sottotitolo)}</em></p>")
    if rubrica.descrizione:
        parti.append(f"<p>{escape(rubrica.descrizione)}</p>")

    if not articoli_e_slug:
        parti.append("<p>Nessun articolo pubblicato al momento.</p>")
    else:
        parti.append("<h3>Articoli</h3><ul>")
        for articolo, slug in articoli_e_slug:
            occhiello = (
                f'<span style="color:{colore};text-transform:uppercase">'
                f"{escape(articolo.occhiello)}</span> — "
                if articolo.occhiello
                else ""
            )
            data = _data_leggibile(articolo.data_pubblicazione or articolo.created_at)
            meta = f" <small>({escape(articolo.firma)}{', ' + data if data else ''})</small>"
            parti.append(
                f'<li>{occhiello}<a href="/regolamento/{escape(slug)}">'
                f"{escape(articolo.titolo)}</a>{meta}</li>"
            )
        parti.append("</ul>")

    parti.append(
        "<hr><p><small>Sezione generata dalle Rubriche di InstaFame. "
        "Like e commenti sono disponibili solo in gioco.</small></p>"
    )
    return "\n".join(parti)


def _upsert_pagina(*, sync_id, slug, titolo, contenuto, parent, ordine, solo_autenticati):
    pagina = PaginaRegolamento.objects.filter(sync_id=sync_id).first()
    valori = {
        "slug": slug,
        "titolo": titolo[:200],
        "contenuto": contenuto,
        "parent": parent,
        "ordine": ordine,
        "public": True,
        "visibile_solo_staff": False,
        "visibile_solo_autenticati": solo_autenticati,
    }
    if pagina is None:
        pagina = PaginaRegolamento(sync_id=sync_id, **valori)
        pagina.save()
        return pagina
    cambiato = False
    for campo, valore in valori.items():
        if getattr(pagina, campo) != valore:
            setattr(pagina, campo, valore)
            cambiato = True
    if cambiato:
        pagina.save()
    return pagina


def rimuovi_pagine_wiki_rubrica(rubrica: Rubrica) -> int:
    """Cancella pagina indice e sottopagine articolo. Ritorna quante pagine sono sparite."""
    pagina_rubrica = PaginaRegolamento.objects.filter(
        sync_id=sync_id_pagina_rubrica(rubrica)
    ).first()
    if not pagina_rubrica:
        return 0
    rimosse = pagina_rubrica.sottopagine.count() + 1
    PaginaRegolamento.objects.filter(parent=pagina_rubrica).delete()
    pagina_rubrica.delete()
    return rimosse


@transaction.atomic
def sync_rubrica_to_wiki(rubrica: Rubrica) -> dict:
    """Allinea le pagine wiki di una rubrica. Ritorna un riepilogo delle azioni."""
    sync_id_rubrica = sync_id_pagina_rubrica(rubrica)

    if not rubrica.pubblica_in_wiki or not rubrica.attiva:
        rimosse = rimuovi_pagine_wiki_rubrica(rubrica)
        if rubrica.wiki_pagina_id:
            Rubrica.objects.filter(pk=rubrica.pk).update(
                wiki_pagina=None, updated_at=timezone.now()
            )
            rubrica.wiki_pagina = None
        return {"pubblicata": False, "pagine_rimosse": rimosse, "articoli": 0}

    solo_autenticati = rubrica.wiki_visibilita == RUBRICA_WIKI_AUTENTICATI
    articoli = list(
        rubrica.articoli.filter(stato=RUBRICA_ARTICOLO_PUBBLICATO)
        .select_related("rubrica", "autore_personaggio")
        .prefetch_related("immagini")
        .order_by("-data_pubblicazione", "-created_at")
    )
    articoli_e_slug = [(articolo, slug_pagina_articolo(articolo)) for articolo in articoli]

    pagina_rubrica = _upsert_pagina(
        sync_id=sync_id_rubrica,
        slug=slug_pagina_rubrica(rubrica),
        titolo=rubrica.titolo_wiki_effettivo,
        contenuto=html_indice_rubrica(rubrica, articoli_e_slug),
        parent=rubrica.wiki_parent,
        ordine=rubrica.wiki_ordine,
        solo_autenticati=solo_autenticati,
    )

    attese = set()
    for indice, (articolo, slug) in enumerate(articoli_e_slug):
        pagina = _upsert_pagina(
            sync_id=sync_id_pagina_articolo(articolo),
            slug=slug,
            titolo=articolo.titolo,
            contenuto=html_articolo(articolo),
            parent=pagina_rubrica,
            ordine=indice,
            solo_autenticati=solo_autenticati,
        )
        attese.add(pagina.pk)

    obsolete = PaginaRegolamento.objects.filter(parent=pagina_rubrica).exclude(pk__in=attese)
    rimosse = obsolete.count()
    obsolete.delete()

    if rubrica.wiki_pagina_id != pagina_rubrica.pk:
        Rubrica.objects.filter(pk=rubrica.pk).update(
            wiki_pagina=pagina_rubrica, updated_at=timezone.now()
        )
        rubrica.wiki_pagina = pagina_rubrica

    return {
        "pubblicata": True,
        "slug": pagina_rubrica.slug,
        "articoli": len(articoli_e_slug),
        "pagine_rimosse": rimosse,
    }


def sync_rubrica_to_wiki_safe(rubrica: Rubrica) -> None:
    """Variante per i signal: non deve mai far fallire il salvataggio."""
    try:
        sync_rubrica_to_wiki(rubrica)
    except Exception:
        logger.exception("Sync wiki rubrica fallito (rubrica_id=%s)", getattr(rubrica, "pk", None))
