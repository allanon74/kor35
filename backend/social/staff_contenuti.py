"""Gestione staff dei post InstaFame e degli articoli di rubrica.

Filtri, modifica di autore/data/evento/testo e spostamento di un post nel corpo
di una rubrica. Le citazioni @ e gli hashtag restano quelli del testo: al save
i signal riallineano i tag.
"""

from __future__ import annotations

import html
import os
from datetime import datetime

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from gestione_plot.models import Evento
from gestione_plot.permissions import _get_active_campaign_for_request
from personaggi.campagna_moduli import staff_tool_abilitato
from personaggi.models import Korp, Personaggio, PersonaggioCarrieraMembership

from .mention_tags import suppress_mention_notify
from .models import (
    SOCIAL_VISIBILITY_CHOICES,
    SOCIAL_VISIBILITY_KORP,
    SOCIAL_VISIBILITY_PUBLIC,
    SocialPost,
    SocialPostImage,
    extract_hashtags,
)
from .models_rubriche import (
    RUBRICA_ARTICOLO_PUBBLICATO,
    RUBRICA_ARTICOLO_STATO_CHOICES,
    Rubrica,
    RubricaArticolo,
    RubricaArticoloComment,
    RubricaArticoloCommentLike,
    RubricaArticoloImmagine,
    testo_indicizzabile_articolo,
)
from .permissions_rubriche import is_staff_rubriche
from .serializers_rubriche import _righe_tag

STATI_ARTICOLO = {codice for codice, _etichetta in RUBRICA_ARTICOLO_STATO_CHOICES}
VISIBILITA_POST = {codice for codice, _etichetta in SOCIAL_VISIBILITY_CHOICES}
MAX_RIGHE_LISTA = 400


def richiedi_staff_contenuti(request):
    if not is_staff_rubriche(request):
        raise PermissionDenied("Solo lo staff può gestire i contenuti InstaFame.")
    campagna = _get_active_campaign_for_request(request)
    if campagna and not staff_tool_abilitato(campagna, "instafame-post"):
        raise PermissionDenied("Il modulo social è disattivo per questa campagna.")


def _parse_dt(value, *, allow_empty=True):
    if value in (None, ""):
        if allow_empty:
            return None
        raise ValidationError("Data obbligatoria.")
    if isinstance(value, datetime):
        dt = value
    else:
        dt = parse_datetime(str(value).strip())
        if dt is None:
            raise ValidationError("Data non valida. Usa un valore ISO, es. 2026-05-01T18:30:00.")
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _int_or_none(value, messaggio):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(messaggio) from exc


def _testo_post_come_html(testo: str) -> str:
    righe = (testo or "").replace("\r\n", "\n").split("\n")
    parti = [f"<p>{html.escape(riga)}</p>" for riga in righe if riga.strip()]
    return "\n".join(parti) or "<p></p>"


def _copia_file(field_file):
    if not field_file or not getattr(field_file, "name", ""):
        return None
    try:
        with field_file.storage.open(field_file.name, "rb") as handle:
            contenuto = handle.read()
    except Exception:
        return None
    nome = os.path.basename(str(field_file.name).replace("\\", "/")) or "media"
    return ContentFile(contenuto, name=nome)


def _nome_personaggio(personaggio):
    if not personaggio:
        return ""
    from .display_names import social_display_name

    return social_display_name(personaggio)


def _utente_di(personaggio):
    user = getattr(personaggio, "proprietario", None) if personaggio else None
    if not user:
        return ""
    return user.username or user.email or ""


def _anteprima(testo, limite=180):
    pulito = " ".join((testo or "").split())
    if len(pulito) <= limite:
        return pulito
    return pulito[: limite - 1] + "…"


def _riga_post(post) -> dict:
    articolo = post.articolo_collegato
    rubrica = articolo.rubrica if articolo and articolo.rubrica_id else None
    if not rubrica:
        annunci = list(post.articolo_annunciato.all()[:1])
        if annunci and annunci[0].rubrica_id:
            rubrica = annunci[0].rubrica
            articolo = articolo or annunci[0]
    return {
        "tipo": "post",
        "id": post.id,
        "titolo": post.titolo or "",
        "anteprima": _anteprima(post.testo),
        "autore_id": post.autore_id,
        "autore_nome": _nome_personaggio(post.autore),
        "utente": _utente_di(post.autore),
        "evento_id": post.evento_id,
        "evento_titolo": post.evento.titolo if post.evento_id and post.evento else "",
        "korp_id": post.korp_visibilita_id,
        "korp_nome": post.korp_visibilita.nome if post.korp_visibilita_id and post.korp_visibilita else "",
        "visibilita": post.visibilita,
        "rubrica_id": str(rubrica.id) if rubrica else None,
        "rubrica_nome": rubrica.nome if rubrica else "",
        "articolo_id": str(articolo.id) if articolo else None,
        "data": post.created_at.isoformat() if post.created_at else None,
        "hashtags": extract_hashtags(f"{post.titolo or ''} {post.testo or ''}"),
    }


def _riga_articolo(articolo) -> dict:
    return {
        "tipo": "articolo",
        "id": str(articolo.id),
        "titolo": articolo.titolo or "",
        "anteprima": _anteprima(articolo.sommario or articolo.corpo or ""),
        "autore_id": articolo.autore_personaggio_id,
        "autore_nome": articolo.firma,
        "utente": _utente_di(articolo.autore_personaggio),
        "evento_id": articolo.evento_id,
        "evento_titolo": articolo.evento.titolo if articolo.evento_id and articolo.evento else "",
        "korp_id": None,
        "korp_nome": "",
        "visibilita": articolo.stato,
        "rubrica_id": str(articolo.rubrica_id),
        "rubrica_nome": articolo.rubrica.nome if articolo.rubrica_id else "",
        "articolo_id": str(articolo.id),
        "data": (
            articolo.data_pubblicazione or articolo.created_at
        ).isoformat()
        if (articolo.data_pubblicazione or articolo.created_at)
        else None,
        "hashtags": extract_hashtags(testo_indicizzabile_articolo(articolo)),
    }


def _filtro_comune_qs_post(qs, params, membri_korp):
    personaggio_id = _int_or_none(params.get("personaggio_id"), "personaggio_id non valido.")
    if personaggio_id:
        qs = qs.filter(autore_id=personaggio_id)
    utente = (params.get("utente") or "").strip()
    if utente:
        qs = qs.filter(
            Q(autore__proprietario__username__icontains=utente)
            | Q(autore__proprietario__email__icontains=utente)
            | Q(autore__nome__icontains=utente)
        )
    evento_id = _int_or_none(params.get("evento_id"), "evento_id non valido.")
    if evento_id:
        qs = qs.filter(evento_id=evento_id)
    korp_id = _int_or_none(params.get("korp_id"), "korp_id non valido.")
    if korp_id:
        qs = qs.filter(Q(korp_visibilita_id=korp_id) | Q(autore_id__in=membri_korp))
    rubrica_id = (params.get("rubrica_id") or "").strip()
    if rubrica_id:
        qs = qs.filter(
            Q(articolo_collegato__rubrica_id=rubrica_id) | Q(articolo_annunciato__rubrica_id=rubrica_id)
        )
    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(titolo__icontains=q) | Q(testo__icontains=q) | Q(autore__nome__icontains=q))
    hashtag = (params.get("hashtag") or "").strip().lstrip("#")
    if hashtag:
        riconosciuti = extract_hashtags(f"#{hashtag}")
        if not riconosciuti:
            return qs.none()
        token = f"#{riconosciuti[0]}"
        qs = qs.filter(Q(titolo__icontains=token) | Q(testo__icontains=token))
    data_da = _parse_dt(params.get("data_da")) if params.get("data_da") else None
    data_a = _parse_dt(params.get("data_a")) if params.get("data_a") else None
    if data_da:
        qs = qs.filter(created_at__gte=data_da)
    if data_a:
        qs = qs.filter(created_at__lte=data_a)
    return qs


def _filtro_comune_qs_articolo(qs, params, membri_korp):
    personaggio_id = _int_or_none(params.get("personaggio_id"), "personaggio_id non valido.")
    if personaggio_id:
        qs = qs.filter(autore_personaggio_id=personaggio_id)
    utente = (params.get("utente") or "").strip()
    if utente:
        qs = qs.filter(
            Q(autore_personaggio__proprietario__username__icontains=utente)
            | Q(autore_personaggio__proprietario__email__icontains=utente)
            | Q(autore_personaggio__nome__icontains=utente)
            | Q(firma_libera__icontains=utente)
        )
    evento_id = _int_or_none(params.get("evento_id"), "evento_id non valido.")
    if evento_id:
        qs = qs.filter(evento_id=evento_id)
    korp_id = _int_or_none(params.get("korp_id"), "korp_id non valido.")
    if korp_id:
        qs = qs.filter(autore_personaggio_id__in=membri_korp)
    rubrica_id = (params.get("rubrica_id") or "").strip()
    if rubrica_id:
        qs = qs.filter(rubrica_id=rubrica_id)
    q = (params.get("q") or "").strip()
    if q:
        qs = qs.filter(
            Q(titolo__icontains=q)
            | Q(sommario__icontains=q)
            | Q(corpo__icontains=q)
            | Q(autore_personaggio__nome__icontains=q)
            | Q(firma_libera__icontains=q)
        )
    hashtag = (params.get("hashtag") or "").strip().lstrip("#")
    if hashtag:
        riconosciuti = extract_hashtags(f"#{hashtag}")
        if not riconosciuti:
            return qs.none()
        token = f"#{riconosciuti[0]}"
        qs = qs.filter(
            Q(occhiello__icontains=token)
            | Q(titolo__icontains=token)
            | Q(sottotitolo__icontains=token)
            | Q(sommario__icontains=token)
            | Q(corpo__icontains=token)
            | Q(comments__testo__icontains=token)
        ).distinct()
    data_da = _parse_dt(params.get("data_da")) if params.get("data_da") else None
    data_a = _parse_dt(params.get("data_a")) if params.get("data_a") else None
    if data_da:
        qs = qs.filter(
            Q(data_pubblicazione__gte=data_da)
            | Q(data_pubblicazione__isnull=True, created_at__gte=data_da)
        )
    if data_a:
        qs = qs.filter(
            Q(data_pubblicazione__lte=data_a)
            | Q(data_pubblicazione__isnull=True, created_at__lte=data_a)
        )
    return qs


def elenca_contenuti(params) -> dict:
    tipo = (params.get("tipo") or "tutti").strip().lower()
    if tipo not in {"tutti", "post", "articolo"}:
        raise ValidationError("tipo deve essere tutti, post o articolo.")
    korp_id = _int_or_none(params.get("korp_id"), "korp_id non valido.")
    membri_korp = []
    if korp_id:
        membri_korp = list(
            PersonaggioCarrieraMembership.objects.filter(
                carriera_id=korp_id, data_a__isnull=True
            ).values_list("personaggio_id", flat=True)
        )

    righe = []
    troncato = False
    if tipo in {"tutti", "post"}:
        qs = SocialPost.objects.select_related(
            "autore",
            "autore__proprietario",
            "autore__social_profile",
            "evento",
            "korp_visibilita",
            "articolo_collegato",
            "articolo_collegato__rubrica",
        ).prefetch_related("articolo_annunciato", "articolo_annunciato__rubrica")
        qs = _filtro_comune_qs_post(qs, params, membri_korp).order_by("-created_at", "-id")
        blocco = list(qs[: MAX_RIGHE_LISTA + 1])
        if len(blocco) > MAX_RIGHE_LISTA:
            troncato = True
            blocco = blocco[:MAX_RIGHE_LISTA]
        righe.extend(_riga_post(post) for post in blocco)
    if tipo in {"tutti", "articolo"}:
        qs = RubricaArticolo.objects.select_related(
            "rubrica",
            "autore_personaggio",
            "autore_personaggio__proprietario",
            "autore_personaggio__social_profile",
            "evento",
        )
        qs = _filtro_comune_qs_articolo(qs, params, membri_korp).order_by(
            "-data_pubblicazione", "-created_at", "-id"
        )
        blocco = list(qs[: MAX_RIGHE_LISTA + 1])
        if len(blocco) > MAX_RIGHE_LISTA:
            troncato = True
            blocco = blocco[:MAX_RIGHE_LISTA]
        righe.extend(_riga_articolo(articolo) for articolo in blocco)

    righe.sort(key=lambda riga: riga.get("data") or "", reverse=True)
    try:
        page = max(1, int(params.get("page") or 1))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(50, max(1, int(params.get("page_size") or 20)))
    except (TypeError, ValueError):
        page_size = 20
    inizio = (page - 1) * page_size
    return {
        "count": len(righe),
        "page": page,
        "page_size": page_size,
        "troncato": troncato,
        "results": righe[inizio : inizio + page_size],
    }


def dettaglio_post(post: SocialPost) -> dict:
    riga = _riga_post(post)
    riga.update(
        {
            "testo": post.testo or "",
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "tags": _righe_tag(post.tags),
        }
    )
    return riga


def dettaglio_articolo(articolo: RubricaArticolo) -> dict:
    riga = _riga_articolo(articolo)
    riga.update(
        {
            "stato": articolo.stato,
            "occhiello": articolo.occhiello or "",
            "sottotitolo": articolo.sottotitolo or "",
            "sommario": articolo.sommario or "",
            "corpo": articolo.corpo or "",
            "firma_libera": articolo.firma_libera or "",
            "data_pubblicazione": articolo.data_pubblicazione.isoformat()
            if articolo.data_pubblicazione
            else None,
            "created_at": articolo.created_at.isoformat() if articolo.created_at else None,
            "tags": _righe_tag(articolo.tags),
        }
    )
    return riga


def _personaggio_obbligatorio(raw_id):
    pid = _int_or_none(raw_id, "Autore non valido.")
    if not pid:
        raise ValidationError("Indica il personaggio autore.")
    personaggio = Personaggio.objects.filter(id=pid).first()
    if not personaggio:
        raise ValidationError("Personaggio autore non trovato.")
    return personaggio


def _evento_opzionale(raw_id):
    if raw_id in (None, "", 0, "0"):
        return None
    eid = _int_or_none(raw_id, "Evento non valido.")
    evento = Evento.objects.filter(id=eid).first()
    if not evento:
        raise ValidationError("Evento non trovato.")
    return evento


def _korp_opzionale(raw_id):
    if raw_id in (None, "", 0, "0"):
        return None
    kid = _int_or_none(raw_id, "KORP non valida.")
    korp = Korp.objects.filter(id=kid).first()
    if not korp:
        raise ValidationError("KORP non trovata.")
    return korp


@transaction.atomic
def aggiorna_post(post: SocialPost, dati: dict) -> SocialPost:
    if "autore" in dati or "autore_id" in dati:
        post.autore = _personaggio_obbligatorio(dati.get("autore", dati.get("autore_id")))
    if "titolo" in dati:
        titolo = str(dati.get("titolo") or "").strip()
        if not titolo:
            raise ValidationError("Il titolo è obbligatorio.")
        post.titolo = titolo[:180]
    if "testo" in dati:
        post.testo = dati.get("testo") or ""
    if "evento" in dati or "evento_id" in dati:
        post.evento = _evento_opzionale(dati.get("evento", dati.get("evento_id")))
    if "created_at" in dati:
        quando = _parse_dt(dati.get("created_at"), allow_empty=False)
        post.created_at = quando
    if "visibilita" in dati or "korp_visibilita" in dati or "korp_id" in dati:
        vis = str(dati.get("visibilita", post.visibilita) or SOCIAL_VISIBILITY_PUBLIC).upper()
        if vis not in VISIBILITA_POST:
            raise ValidationError("Visibilità non valida.")
        post.visibilita = vis
        if vis == SOCIAL_VISIBILITY_KORP:
            if "korp_visibilita" in dati or "korp_id" in dati:
                post.korp_visibilita = _korp_opzionale(dati.get("korp_visibilita", dati.get("korp_id")))
            if not post.korp_visibilita_id:
                raise ValidationError("Per la visibilità KORP indica una KORP.")
        else:
            post.korp_visibilita = None
    post.save()
    return post


@transaction.atomic
def aggiorna_articolo(articolo: RubricaArticolo, dati: dict) -> RubricaArticolo:
    if "rubrica" in dati or "rubrica_id" in dati:
        raw = dati.get("rubrica", dati.get("rubrica_id"))
        rubrica = Rubrica.objects.filter(id=raw).first() if raw else None
        if not rubrica:
            raise ValidationError("Rubrica non trovata.")
        if rubrica.id != articolo.rubrica_id and RubricaArticolo.objects.filter(
            rubrica=rubrica, slug=articolo.slug
        ).exclude(pk=articolo.pk).exists():
            articolo.slug = ""
        articolo.rubrica = rubrica
    if "stato" in dati:
        stato = str(dati.get("stato") or "").upper()
        if stato not in STATI_ARTICOLO:
            raise ValidationError("Stato articolo non valido.")
        articolo.stato = stato
    for campo, limite in (
        ("occhiello", 120),
        ("titolo", 200),
        ("sottotitolo", 300),
        ("firma_libera", 160),
    ):
        if campo in dati:
            valore = str(dati.get(campo) or "").strip()
            if campo == "titolo" and not valore:
                raise ValidationError("Il titolo è obbligatorio.")
            setattr(articolo, campo, valore[:limite])
    if "sommario" in dati:
        articolo.sommario = dati.get("sommario") or ""
    if "corpo" in dati:
        articolo.corpo = dati.get("corpo") or ""
    if "autore_personaggio" in dati or "autore_id" in dati:
        raw = dati.get("autore_personaggio", dati.get("autore_id"))
        if raw in (None, ""):
            articolo.autore_personaggio = None
        else:
            articolo.autore_personaggio = _personaggio_obbligatorio(raw)
    if "evento" in dati or "evento_id" in dati:
        articolo.evento = _evento_opzionale(dati.get("evento", dati.get("evento_id")))
    if "data_pubblicazione" in dati:
        articolo.data_pubblicazione = _parse_dt(dati.get("data_pubblicazione"))
    if "created_at" in dati:
        articolo.created_at = _parse_dt(dati.get("created_at"), allow_empty=False)
    if not articolo.autore_personaggio_id and not (articolo.firma_libera or "").strip():
        raise ValidationError("Serve un personaggio autore oppure una firma libera.")
    articolo.save()
    return articolo


def _copia_media_post(post: SocialPost, articolo: RubricaArticolo) -> None:
    immagini = []
    for riga in post.post_images.all().order_by("ordine", "id"):
        contenuto = _copia_file(riga.immagine)
        if contenuto:
            immagini.append(contenuto)
    if not immagini:
        contenuto = _copia_file(post.immagine)
        if contenuto:
            immagini.append(contenuto)
    if immagini:
        articolo.hero_immagine = immagini[0]
        articolo.save(update_fields=["hero_immagine", "updated_at"])
        for ordine, contenuto in enumerate(immagini[1:], start=0):
            RubricaArticoloImmagine.objects.create(articolo=articolo, immagine=contenuto, ordine=ordine)
        return
    video = _copia_file(post.video)
    if video:
        articolo.video = video
        articolo.save(update_fields=["video", "updated_at"])


@transaction.atomic
def sposta_post_in_rubrica(post: SocialPost, dati: dict, *, user) -> dict:
    """Crea l'articolo, sposta i commenti e collega (o rimuove) il post di feed."""
    if post.articolo_collegato_id or RubricaArticolo.objects.filter(post_annuncio=post).exists():
        raise ValidationError("Questo post è già collegato a un articolo di rubrica.")
    rubrica_id = dati.get("rubrica") or dati.get("rubrica_id")
    rubrica = Rubrica.objects.filter(id=rubrica_id).first() if rubrica_id else None
    if not rubrica:
        raise ValidationError("Indica la rubrica di destinazione.")
    stato = str(dati.get("stato") or RUBRICA_ARTICOLO_PUBBLICATO).upper()
    if stato not in STATI_ARTICOLO:
        raise ValidationError("Stato articolo non valido.")
    mantieni = dati.get("mantieni_post_lancio", True)
    if isinstance(mantieni, str):
        mantieni = mantieni.strip().lower() not in {"0", "false", "no"}

    with suppress_mention_notify():
        articolo = RubricaArticolo(
            rubrica=rubrica,
            stato=stato,
            titolo=(post.titolo or "Senza titolo")[:200],
            corpo=_testo_post_come_html(post.testo or ""),
            sommario=_anteprima(post.testo or "", 300),
            autore_personaggio=post.autore,
            creato_da_user=user if getattr(user, "is_authenticated", False) else None,
            evento=post.evento,
            data_pubblicazione=post.created_at,
            created_at=post.created_at or timezone.now(),
            likes_base=post.likes_base or 1,
        )
        articolo.save()
        _copia_media_post(post, articolo)
        for commento in post.comments.prefetch_related("likes").select_related("autore").order_by("created_at", "id"):
            nuovo = RubricaArticoloComment(
                articolo=articolo,
                autore=commento.autore,
                testo=commento.testo,
                evento=commento.evento,
                likes_base=commento.likes_base,
                created_at=commento.created_at,
            )
            nuovo.save()
            for like in commento.likes.all():
                RubricaArticoloCommentLike.objects.create(
                    comment=nuovo,
                    autore=like.autore,
                    peso_like=like.peso_like,
                    created_at=like.created_at,
                )
        post.comments.all().delete()
        if mantieni:
            post.articolo_collegato = articolo
            post.save(update_fields=["articolo_collegato", "updated_at"])
            articolo.post_annuncio = post
            articolo.save(update_fields=["post_annuncio", "updated_at"])
        else:
            post.delete()
    articolo.refresh_from_db()
    return {
        "articolo": dettaglio_articolo(articolo),
        "post_rimosso": not mantieni,
        "post_id": post.id if mantieni else None,
    }


def _risposta_validazione(exc):
    if isinstance(exc, DjangoValidationError):
        messaggi = getattr(exc, "messages", None) or [str(exc)]
        return Response({"detail": messaggi[0] if len(messaggi) == 1 else messaggi}, status=status.HTTP_400_BAD_REQUEST)
    dettaglio = exc.detail
    if isinstance(dettaglio, list) and len(dettaglio) == 1:
        dettaglio = dettaglio[0]
    return Response({"detail": str(dettaglio)}, status=status.HTTP_400_BAD_REQUEST)


class SocialStaffContenutiView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        richiedi_staff_contenuti(request)
        try:
            payload = elenca_contenuti(request.query_params)
        except (ValidationError, DjangoValidationError) as exc:
            return _risposta_validazione(exc)
        return Response(payload)


class SocialStaffPostDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _post(self, post_id):
        post = (
            SocialPost.objects.select_related(
                "autore",
                "autore__proprietario",
                "autore__social_profile",
                "evento",
                "korp_visibilita",
                "articolo_collegato",
                "articolo_collegato__rubrica",
            )
            .filter(id=post_id)
            .first()
        )
        if not post:
            return None
        return post

    def get(self, request, post_id):
        richiedi_staff_contenuti(request)
        post = self._post(post_id)
        if not post:
            return Response({"detail": "Post non trovato."}, status=status.HTTP_404_NOT_FOUND)
        return Response(dettaglio_post(post))

    def patch(self, request, post_id):
        richiedi_staff_contenuti(request)
        post = self._post(post_id)
        if not post:
            return Response({"detail": "Post non trovato."}, status=status.HTTP_404_NOT_FOUND)
        try:
            aggiorna_post(post, request.data)
        except (ValidationError, DjangoValidationError) as exc:
            return _risposta_validazione(exc)
        post.refresh_from_db()
        return Response(dettaglio_post(post))


class SocialStaffSpostaPostView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, post_id):
        richiedi_staff_contenuti(request)
        post = SocialPost.objects.filter(id=post_id).first()
        if not post:
            return Response({"detail": "Post non trovato."}, status=status.HTTP_404_NOT_FOUND)
        try:
            payload = sposta_post_in_rubrica(post, request.data, user=request.user)
        except (ValidationError, DjangoValidationError) as exc:
            return _risposta_validazione(exc)
        return Response(payload, status=status.HTTP_201_CREATED)


class SocialStaffArticoloDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _articolo(self, articolo_id):
        return (
            RubricaArticolo.objects.select_related(
                "rubrica",
                "autore_personaggio",
                "autore_personaggio__proprietario",
                "autore_personaggio__social_profile",
                "evento",
            )
            .filter(id=articolo_id)
            .first()
        )

    def get(self, request, articolo_id):
        richiedi_staff_contenuti(request)
        articolo = self._articolo(articolo_id)
        if not articolo:
            return Response({"detail": "Articolo non trovato."}, status=status.HTTP_404_NOT_FOUND)
        return Response(dettaglio_articolo(articolo))

    def patch(self, request, articolo_id):
        richiedi_staff_contenuti(request)
        articolo = self._articolo(articolo_id)
        if not articolo:
            return Response({"detail": "Articolo non trovato."}, status=status.HTTP_404_NOT_FOUND)
        try:
            aggiorna_articolo(articolo, request.data)
        except (ValidationError, DjangoValidationError) as exc:
            return _risposta_validazione(exc)
        articolo.refresh_from_db()
        return Response(dettaglio_articolo(articolo))
