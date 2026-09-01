"""API rubriche InstaFame: CRUD, permessi di scrittura, like/commenti, post di lancio, wiki."""

import logging
import os

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from personaggi.campagna_moduli import (
    MODULO_RUBRICHE,
    ModuloStaffGateMixin,
    modulo_accesso_error,
)
from personaggi.models import Korp, Personaggio, PersonaggioCarrieraMembership

from .influencer import compute_like_peso, random_likes_base
from .models import SOCIAL_VISIBILITY_KORP, SOCIAL_VISIBILITY_PUBLIC, SocialPost, SocialPostImage
from .models_rubriche import (
    RUBRICA_ARTICOLO_PUBBLICATO,
    Rubrica,
    RubricaArticolo,
    RubricaArticoloComment,
    RubricaArticoloCommentLike,
    RubricaArticoloLike,
    RubricaPermessoScrittura,
    testo_semplice_da_html,
)
from .permissions_rubriche import (
    IsArticoloAuthenticated,
    IsRubricaReadOrMaster,
    is_master_rubriche,
    is_staff_rubriche,
    personaggio_puo_scrivere,
    rubriche_scrivibili_ids,
)
from .rubriche_media import apply_articolo_media_from_request
from .rubriche_wiki import sync_rubrica_to_wiki
from .serializers import resolve_active_personaggio
from .serializers_rubriche import (
    RubricaArticoloCommentSerializer,
    RubricaArticoloDetailSerializer,
    RubricaArticoloListSerializer,
    RubricaArticoloWriteSerializer,
    RubricaPermessoScritturaSerializer,
    RubricaSerializer,
)
from .views import (
    SocialCommentPagination,
    SocialPostPagination,
    gate_modulo_social,
    get_evento_in_corso,
)

logger = logging.getLogger(__name__)


def gate_modulo_rubriche(request, personaggio):
    """
    Modulo campagna «rubriche»: in TEST la sezione in-game resta ai soli staff/PnG.
    Il caso OFF è già respinto da ModuloStaffGateMixin, che copre anche gli utenti
    senza personaggio attivo.
    """
    if not personaggio:
        return None
    msg = modulo_accesso_error(personaggio, MODULO_RUBRICHE, user=getattr(request, "user", None))
    if msg:
        raise PermissionDenied(msg)
    return personaggio


class RubricheContextMixin(ModuloStaffGateMixin):
    modulo_key = MODULO_RUBRICHE

    def get_personaggio(self):
        if not self.request.user.is_authenticated:
            return None
        requested = self.request.query_params.get("personaggio_id") or self.request.data.get(
            "personaggio_id"
        )
        personaggio = resolve_active_personaggio(self.request.user, requested, request=self.request)
        personaggio = gate_modulo_social(self.request, personaggio)
        return gate_modulo_rubriche(self.request, personaggio)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        personaggio = self.get_personaggio()
        ctx["personaggio"] = personaggio
        ctx["is_staff_rubriche"] = is_staff_rubriche(self.request)
        ctx["rubriche_scrivibili"] = rubriche_scrivibili_ids(personaggio)
        return ctx


class RubricaViewSet(RubricheContextMixin, viewsets.ModelViewSet):
    serializer_class = RubricaSerializer
    permission_classes = [IsRubricaReadOrMaster]

    def get_queryset(self):
        qs = Rubrica.objects.select_related("wiki_parent", "wiki_pagina").annotate(
            articoli_pubblicati_count=Count(
                "articoli", filter=Q(articoli__stato=RUBRICA_ARTICOLO_PUBBLICATO), distinct=True
            )
        )
        if is_staff_rubriche(self.request):
            return qs
        return qs.filter(attiva=True)

    def perform_create(self, serializer):
        serializer.save(creata_da=self.request.user)

    @action(
        detail=True,
        methods=["get", "post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def permessi(self, request, pk=None):
        rubrica = self.get_object()
        if not is_staff_rubriche(request):
            raise PermissionDenied("Solo lo staff può gestire i permessi di scrittura.")

        if request.method.lower() == "get":
            righe = rubrica.permessi_scrittura.select_related(
                "personaggio", "personaggio__social_profile", "concesso_da"
            ).all()
            return Response(RubricaPermessoScritturaSerializer(righe, many=True).data)

        personaggio_id = request.data.get("personaggio_target_id") or request.data.get("personaggio")
        personaggio = Personaggio.objects.filter(id=personaggio_id).first()
        if not personaggio:
            return Response({"detail": "Personaggio non trovato."}, status=status.HTTP_404_NOT_FOUND)
        permesso, _ = RubricaPermessoScrittura.objects.update_or_create(
            rubrica=rubrica,
            personaggio=personaggio,
            defaults={
                "attivo": True,
                "concesso_da": request.user,
                "note": (request.data.get("note") or "")[:200],
            },
        )
        return Response(
            RubricaPermessoScritturaSerializer(permesso).data, status=status.HTTP_201_CREATED
        )

    @action(
        detail=True,
        methods=["delete"],
        permission_classes=[permissions.IsAuthenticated],
        url_path=r"permessi/(?P<permesso_id>[^/.]+)",
    )
    def revoca_permesso(self, request, pk=None, permesso_id=None):
        rubrica = self.get_object()
        if not is_staff_rubriche(request):
            raise PermissionDenied("Solo lo staff può gestire i permessi di scrittura.")
        permesso = RubricaPermessoScrittura.objects.filter(id=permesso_id, rubrica=rubrica).first()
        if not permesso:
            return Response({"detail": "Permesso non trovato."}, status=status.HTTP_404_NOT_FOUND)
        permesso.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="wiki-sync")
    def wiki_sync(self, request, pk=None):
        rubrica = self.get_object()
        if not is_master_rubriche(request):
            raise PermissionDenied("Solo master+ può rigenerare le pagine wiki.")
        try:
            esito = sync_rubrica_to_wiki(rubrica)
        except Exception as exc:
            logger.exception("Rigenerazione wiki rubrica fallita (rubrica_id=%s)", rubrica.pk)
            return Response(
                {"detail": f"Errore durante la generazione delle pagine wiki: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(esito, status=status.HTTP_200_OK)


class RubricaArticoloViewSet(RubricheContextMixin, viewsets.ModelViewSet):
    permission_classes = [IsArticoloAuthenticated]
    pagination_class = SocialPostPagination

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return RubricaArticoloWriteSerializer
        if self.action == "list":
            return RubricaArticoloListSerializer
        return RubricaArticoloDetailSerializer

    def get_queryset(self):
        personaggio = self.get_personaggio()
        qs = (
            RubricaArticolo.objects.select_related(
                "rubrica", "autore_personaggio", "autore_personaggio__social_profile"
            )
            .prefetch_related("immagini")
            .annotate(commenti_count=Count("comments", distinct=True))
        )
        if not is_staff_rubriche(self.request):
            visibili = Q(stato=RUBRICA_ARTICOLO_PUBBLICATO, rubrica__attiva=True)
            if personaggio:
                visibili |= Q(autore_personaggio=personaggio)
            qs = qs.filter(visibili)
        rubrica_id = self.request.query_params.get("rubrica")
        if rubrica_id:
            qs = qs.filter(rubrica_id=rubrica_id)
        stato = self.request.query_params.get("stato")
        if stato:
            qs = qs.filter(stato=stato)
        # Ordinamento esplicito: la paginazione DRF non si fida del Meta.ordering
        # quando il queryset è annotato.
        return qs.order_by("-data_pubblicazione", "-created_at", "-id")

    def _verifica_permesso_scrittura(self, rubrica, personaggio, autore_personaggio):
        if is_staff_rubriche(self.request):
            return
        if not personaggio:
            raise PermissionDenied("Nessun personaggio selezionabile per questo utente.")
        if not personaggio_puo_scrivere(rubrica, personaggio):
            raise PermissionDenied("Il personaggio non è autorizzato a scrivere in questa rubrica.")
        if autore_personaggio and autore_personaggio.id != personaggio.id:
            raise PermissionDenied("Puoi firmare gli articoli solo con il personaggio attivo.")

    def _verifica_permesso_modifica(self, articolo, personaggio):
        if is_staff_rubriche(self.request):
            return
        if not personaggio or articolo.autore_personaggio_id != getattr(personaggio, "id", None):
            raise PermissionDenied("Puoi modificare solo i tuoi articoli.")
        if not personaggio_puo_scrivere(articolo.rubrica, personaggio):
            raise PermissionDenied("Permesso di scrittura revocato su questa rubrica.")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Articolo e post di lancio nascono insieme: se l'annuncio fallisce non deve
        # restare un articolo salvato a metà.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        articolo = (
            self.get_queryset().filter(pk=serializer.instance.pk).first() or serializer.instance
        )
        return Response(
            RubricaArticoloDetailSerializer(articolo, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        articolo = self.get_queryset().filter(pk=serializer.instance.pk).first() or serializer.instance
        return Response(
            RubricaArticoloDetailSerializer(articolo, context=self.get_serializer_context()).data
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def perform_create(self, serializer):
        personaggio = self.get_personaggio()
        rubrica = serializer.validated_data.get("rubrica")
        autore = serializer.validated_data.get("autore_personaggio")
        if not is_staff_rubriche(self.request) and not autore:
            autore = personaggio
        self._verifica_permesso_scrittura(rubrica, personaggio, autore)

        articolo = serializer.save(
            autore_personaggio=autore,
            creato_da_user=self.request.user,
            evento=get_evento_in_corso(),
            likes_base=random_likes_base(autore) if autore else 1,
        )
        self._applica_media(articolo, replace_gallery=True)
        self._gestisci_annuncio_da_request(articolo)

    def perform_update(self, serializer):
        articolo = self.get_object()
        personaggio = self.get_personaggio()
        self._verifica_permesso_modifica(articolo, personaggio)
        articolo = serializer.save()
        # Append galleria; clear_immagini / immagini_meta gestiti in apply_articolo_media_from_request.
        self._applica_media(articolo, replace_gallery=False)
        self._gestisci_annuncio_da_request(articolo)

    def perform_destroy(self, instance):
        personaggio = self.get_personaggio()
        self._verifica_permesso_modifica(instance, personaggio)
        if str(self.request.query_params.get("elimina_annuncio", "")).lower() in {"1", "true", "yes"}:
            if instance.post_annuncio_id:
                instance.post_annuncio.delete()
        instance.delete()

    def _applica_media(self, articolo, *, replace_gallery):
        try:
            apply_articolo_media_from_request(articolo, self.request, replace_gallery=replace_gallery)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages if hasattr(exc, "messages") else str(exc))
        articolo.refresh_from_db()

    def _gestisci_annuncio_da_request(self, articolo):
        if str(self.request.data.get("crea_post_annuncio", "")).lower() not in {"1", "true", "yes"}:
            return
        if articolo.post_annuncio_id:
            return
        if articolo.stato != RUBRICA_ARTICOLO_PUBBLICATO:
            return
        try:
            crea_post_annuncio(
                articolo,
                request=self.request,
                personaggio_attivo=self.get_personaggio(),
                testo=self.request.data.get("annuncio_testo"),
                autore_id=self.request.data.get("annuncio_autore_personaggio_id"),
                visibilita=self.request.data.get("annuncio_visibilita"),
                korp_id=self.request.data.get("annuncio_korp_id"),
            )
        except ValidationError:
            raise
        except Exception:
            logger.exception("Creazione post di lancio fallita (articolo_id=%s)", articolo.pk)

    @action(detail=True, methods=["post"], url_path="post-annuncio")
    def post_annuncio(self, request, pk=None):
        articolo = self.get_object()
        personaggio = self.get_personaggio()
        if not is_staff_rubriche(request):
            self._verifica_permesso_modifica(articolo, personaggio)
        post = crea_post_annuncio(
            articolo,
            request=request,
            personaggio_attivo=personaggio,
            testo=request.data.get("annuncio_testo") or request.data.get("testo"),
            autore_id=request.data.get("annuncio_autore_personaggio_id"),
            visibilita=request.data.get("annuncio_visibilita"),
            korp_id=request.data.get("annuncio_korp_id"),
        )
        return Response({"post_id": post.id, "articolo_id": str(articolo.id)}, status=status.HTTP_201_CREATED)

    @post_annuncio.mapping.delete
    def elimina_post_annuncio(self, request, pk=None):
        articolo = self.get_object()
        personaggio = self.get_personaggio()
        if not is_staff_rubriche(request):
            self._verifica_permesso_modifica(articolo, personaggio)
        if not articolo.post_annuncio_id:
            return Response({"detail": "Nessun post di lancio da eliminare."}, status=status.HTTP_404_NOT_FOUND)
        articolo.post_annuncio.delete()
        articolo.refresh_from_db()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def like(self, request, pk=None):
        articolo = self.get_object()
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        like = RubricaArticoloLike.objects.filter(articolo=articolo, autore=personaggio).first()
        if like:
            like.delete()
            return Response({"liked": False}, status=status.HTTP_200_OK)
        proprietario = articolo.autore_personaggio or personaggio
        peso = compute_like_peso(personaggio, proprietario)
        RubricaArticoloLike.objects.create(articolo=articolo, autore=personaggio, peso_like=peso)
        return Response({"liked": True, "peso_like": peso}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def comments(self, request, pk=None):
        articolo = self.get_object()
        personaggio = self.get_personaggio()
        if request.method.lower() == "get":
            qs = articolo.comments.select_related("autore", "autore__social_profile").all()
            paginator = SocialCommentPagination()
            page = paginator.paginate_queryset(qs, request, view=self)
            serializer = RubricaArticoloCommentSerializer(
                page, many=True, context=self.get_serializer_context()
            )
            return paginator.get_paginated_response(serializer.data)

        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = RubricaArticoloCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        commento = serializer.save(
            articolo=articolo,
            autore=personaggio,
            evento=get_evento_in_corso(),
            likes_base=random_likes_base(personaggio),
        )
        return Response(
            RubricaArticoloCommentSerializer(commento, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        url_path=r"comments/(?P<comment_id>[^/.]+)/like",
    )
    def comment_like(self, request, pk=None, comment_id=None):
        articolo = self.get_object()
        personaggio = self.get_personaggio()
        if not personaggio:
            return Response({"detail": "Nessun personaggio disponibile."}, status=status.HTTP_400_BAD_REQUEST)
        commento = RubricaArticoloComment.objects.filter(id=comment_id, articolo=articolo).first()
        if not commento:
            return Response({"detail": "Commento non trovato."}, status=status.HTTP_404_NOT_FOUND)
        like = RubricaArticoloCommentLike.objects.filter(comment=commento, autore=personaggio).first()
        if like:
            like.delete()
            return Response({"liked": False}, status=status.HTTP_200_OK)
        peso = compute_like_peso(personaggio, commento.autore)
        RubricaArticoloCommentLike.objects.create(
            comment=commento, autore=personaggio, peso_like=peso
        )
        return Response({"liked": True, "peso_like": peso}, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["patch", "delete"],
        permission_classes=[permissions.IsAuthenticated],
        url_path=r"comments/(?P<comment_id>[^/.]+)",
    )
    def comment_detail(self, request, pk=None, comment_id=None):
        articolo = self.get_object()
        personaggio = self.get_personaggio()
        commento = RubricaArticoloComment.objects.filter(id=comment_id, articolo=articolo).first()
        if not commento:
            return Response({"detail": "Commento non trovato."}, status=status.HTTP_404_NOT_FOUND)

        puo_moderare = is_staff_rubriche(request)
        proprio = personaggio and commento.autore_id == personaggio.id
        if not (puo_moderare or proprio):
            raise PermissionDenied("Permessi insufficienti per modificare il commento.")

        if request.method.lower() == "delete":
            commento.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = RubricaArticoloCommentSerializer(commento, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        aggiornato = serializer.save()
        return Response(
            RubricaArticoloCommentSerializer(aggiornato, context=self.get_serializer_context()).data
        )


def _testo_annuncio_default(articolo) -> str:
    righe = []
    if articolo.occhiello:
        righe.append(articolo.occhiello.upper())
    righe.append(articolo.titolo)
    sommario = (articolo.sommario or "").strip() or testo_semplice_da_html(articolo.corpo)
    if sommario:
        righe.append(sommario[:240] + ("…" if len(sommario) > 240 else ""))
    righe.append(f"Leggi l'articolo su {articolo.rubrica.nome}.")
    return "\n\n".join(righe)


@transaction.atomic
def crea_post_annuncio(
    articolo,
    *,
    request,
    personaggio_attivo=None,
    testo=None,
    autore_id=None,
    visibilita=None,
    korp_id=None,
):
    """Crea il post InstaFame che annuncia l'uscita di un articolo pubblicato."""
    if articolo.stato != RUBRICA_ARTICOLO_PUBBLICATO:
        raise ValidationError("Puoi annunciare solo articoli pubblicati.")
    if articolo.post_annuncio_id:
        raise ValidationError("Esiste già un post di lancio per questo articolo.")

    autore = None
    if autore_id:
        autore = Personaggio.objects.filter(id=autore_id).first()
        if not autore:
            raise ValidationError("Personaggio indicato per il post di lancio non trovato.")
    if not autore:
        autore = articolo.autore_personaggio or personaggio_attivo
    if not autore:
        raise ValidationError(
            "Serve un personaggio che firmi il post di lancio: l'articolo ha solo una firma libera."
        )

    visibilita = (visibilita or SOCIAL_VISIBILITY_PUBLIC).upper()
    korp = None
    if visibilita == SOCIAL_VISIBILITY_KORP:
        korp = Korp.objects.filter(id=korp_id).first() if korp_id else None
        if not korp:
            raise ValidationError("Per la visibilità KORP devi indicare una KORP.")
        appartiene = PersonaggioCarrieraMembership.objects.filter(
            personaggio=autore, carriera=korp, data_a__isnull=True
        ).exists()
        if not appartiene:
            raise ValidationError("Il personaggio non appartiene alla KORP selezionata.")

    post = SocialPost.objects.create(
        autore=autore,
        titolo=articolo.titolo[:180],
        testo=(testo or "").strip() or _testo_annuncio_default(articolo),
        visibilita=visibilita,
        korp_visibilita=korp,
        evento=get_evento_in_corso(),
        likes_base=random_likes_base(autore),
        articolo_collegato=articolo,
    )

    _copia_hero_su_post(articolo, post)

    articolo.post_annuncio = post
    articolo.save(update_fields=["post_annuncio", "updated_at"])
    return post


def _copia_hero_su_post(articolo, post):
    """Copia (non sposta) l'immagine di apertura come copertina del post di lancio."""
    hero = articolo.hero_immagine
    if not hero or not getattr(hero, "name", ""):
        return
    try:
        with hero.storage.open(hero.name, "rb") as fh:
            contenuto = fh.read()
    except Exception:
        return
    nome = os.path.basename(hero.name.replace("\\", "/"))
    SocialPostImage.objects.create(
        post=post, immagine=ContentFile(contenuto, name=nome), ordine=0
    )
