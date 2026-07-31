"""API Task/Missioni: CRUD staff, lista giocatore, risoluzione, claim, riepilogo."""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import (
    CharField,
    IntegerField,
    ListField,
    ModelSerializer,
    Serializer,
    SerializerMethodField,
    UUIDField,
    ValidationError,
)

from personaggi.models import Personaggio, PropostaTecnica

from .models import Evento, GiornoEvento, Missione, MissioneEvento, MissioneRisoluzione, Quest
from .missioni_service import (
    assegna_risoluzione,
    lista_missioni_per_personaggio,
    reclama_ricompensa,
    riepilogo_premi_evento,
)
from .views import IsMasterOrReadOnly


class MissioneSerializer(ModelSerializer):
    korp_nome = CharField(source="korp.nome", read_only=True, allow_null=True)
    eventi_ids = ListField(
        child=IntegerField(),
        write_only=True,
        required=False,
    )
    eventi = SerializerMethodField()

    class Meta:
        model = Missione
        fields = (
            "id",
            "sync_id",
            "updated_at",
            "created_at",
            "titolo",
            "descrizione",
            "korp",
            "korp_nome",
            "reward_crediti",
            "reward_prestigio",
            "tipo_risoluzione",
            "premio_solo_primo",
            "malus_non_primo_crediti",
            "malus_non_primo_prestigio",
            "bonus_successive_crediti",
            "bonus_successive_prestigio",
            "attiva",
            "ordine",
            "eventi",
            "eventi_ids",
        )
        read_only_fields = ("id", "sync_id", "updated_at", "created_at", "korp_nome")

    def get_eventi(self, obj):
        return [
            {"id": e.id, "titolo": e.titolo}
            for e in obj.eventi.all().order_by("-data_inizio")
        ]

    def validate_korp(self, value):
        if value is None:
            return value
        if getattr(getattr(value, "tipo_carriera", None), "codice", None) != "korp":
            raise ValidationError("La carriera selezionata non è una KORP.")
        return value

    def _sync_eventi(self, missione, eventi_ids):
        if eventi_ids is None:
            return
        ids = [int(x) for x in eventi_ids]
        esistenti = set(
            MissioneEvento.objects.filter(missione=missione).values_list("evento_id", flat=True)
        )
        target = set(ids)
        for eid in esistenti - target:
            MissioneEvento.objects.filter(missione=missione, evento_id=eid).delete()
        for eid in target - esistenti:
            if Evento.objects.filter(pk=eid).exists():
                MissioneEvento.objects.get_or_create(missione=missione, evento_id=eid)

    def create(self, validated_data):
        eventi_ids = validated_data.pop("eventi_ids", None)
        missione = Missione.objects.create(**validated_data)
        self._sync_eventi(missione, eventi_ids)
        return missione

    def update(self, instance, validated_data):
        eventi_ids = validated_data.pop("eventi_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        self._sync_eventi(instance, eventi_ids)
        return instance


class MissioneRisoluzioneSerializer(ModelSerializer):
    personaggio_nome = CharField(source="personaggio.nome", read_only=True)
    missione_titolo = CharField(source="missione.titolo", read_only=True)
    evento_titolo = CharField(source="evento.titolo", read_only=True)

    class Meta:
        model = MissioneRisoluzione
        fields = (
            "id",
            "sync_id",
            "updated_at",
            "created_at",
            "missione",
            "missione_titolo",
            "evento",
            "evento_titolo",
            "personaggio",
            "personaggio_nome",
            "resolved_at",
            "is_primo",
            "reward_crediti",
            "reward_prestigio",
            "ricompensa_reclamata",
            "reclamata_at",
            "proposta_tecnica",
            "social_post",
            "quest",
            "giorno",
            "note",
        )
        read_only_fields = (
            "id",
            "sync_id",
            "updated_at",
            "created_at",
            "resolved_at",
            "is_primo",
            "reward_crediti",
            "reward_prestigio",
            "ricompensa_reclamata",
            "reclamata_at",
            "missione_titolo",
            "evento_titolo",
            "personaggio_nome",
        )


class AssegnaRisoluzioneSerializer(Serializer):
    missione_id = UUIDField()
    evento_id = IntegerField()
    personaggio_id = IntegerField()
    proposta_tecnica_id = IntegerField(required=False, allow_null=True)
    social_post_id = IntegerField(required=False, allow_null=True)
    quest_id = IntegerField(required=False, allow_null=True)
    giorno_id = IntegerField(required=False, allow_null=True)
    note = CharField(required=False, allow_blank=True, default="")


class MissioneViewSet(viewsets.ModelViewSet):
    """CRUD staff + azioni risoluzione/claim."""

    queryset = Missione.objects.all().select_related("korp").prefetch_related("eventi")
    serializer_class = MissioneSerializer
    permission_classes = [IsMasterOrReadOnly]

    def get_permissions(self):
        if self.action in ("list", "retrieve", "mie", "riepilogo_evento"):
            return [permissions.IsAuthenticated()]
        if self.action in ("claim",):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsMasterOrReadOnly()]

    def get_queryset(self):
        qs = super().get_queryset()
        evento_id = self.request.query_params.get("evento")
        if evento_id:
            qs = qs.filter(eventi__id=evento_id)
        tipo = self.request.query_params.get("tipo_risoluzione")
        if tipo:
            qs = qs.filter(tipo_risoluzione=tipo)
        korp = self.request.query_params.get("korp")
        if korp == "null":
            qs = qs.filter(korp__isnull=True)
        elif korp:
            qs = qs.filter(korp_id=korp)
        attiva = self.request.query_params.get("attiva")
        if attiva in ("1", "true", "True"):
            qs = qs.filter(attiva=True)
        elif attiva in ("0", "false", "False"):
            qs = qs.filter(attiva=False)
        return qs.distinct()

    @action(detail=False, methods=["get"], url_path="mie")
    def mie(self, request):
        pg_id = request.query_params.get("personaggio")
        if not pg_id:
            return Response({"detail": "Parametro personaggio obbligatorio."}, status=400)
        pg = get_object_or_404(Personaggio, pk=pg_id)
        # proprietario o staff
        user = request.user
        is_staff = bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
        if not is_staff and pg.proprietario_id != user.id:
            return Response({"detail": "Non autorizzato."}, status=403)
        return Response(lista_missioni_per_personaggio(pg))

    @action(detail=False, methods=["get"], url_path=r"riepilogo-evento/(?P<evento_id>[^/.]+)")
    def riepilogo_evento(self, request, evento_id=None):
        evento = get_object_or_404(Evento, pk=evento_id)
        return Response({
            "evento_id": evento.id,
            "evento_titolo": evento.titolo,
            "korps": riepilogo_premi_evento(evento),
        })

    @action(detail=False, methods=["post"], url_path="assegna-risoluzione")
    def assegna(self, request):
        ser = AssegnaRisoluzioneSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        missione = get_object_or_404(Missione, pk=data["missione_id"])
        evento = get_object_or_404(Evento, pk=data["evento_id"])
        personaggio = get_object_or_404(Personaggio, pk=data["personaggio_id"])

        kwargs = {"note": data.get("note") or ""}
        if data.get("proposta_tecnica_id"):
            kwargs["proposta_tecnica"] = get_object_or_404(
                PropostaTecnica, pk=data["proposta_tecnica_id"]
            )
        if data.get("social_post_id"):
            from social.models import SocialPost
            kwargs["social_post"] = get_object_or_404(SocialPost, pk=data["social_post_id"])
        if data.get("quest_id"):
            kwargs["quest"] = get_object_or_404(Quest, pk=data["quest_id"])
        if data.get("giorno_id"):
            kwargs["giorno"] = get_object_or_404(GiornoEvento, pk=data["giorno_id"])

        try:
            ris = assegna_risoluzione(
                missione=missione,
                evento=evento,
                personaggio=personaggio,
                **kwargs,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(MissioneRisoluzioneSerializer(ris).data, status=201)

    @action(detail=False, methods=["post"], url_path=r"claim/(?P<risoluzione_id>[^/.]+)")
    def claim(self, request, risoluzione_id=None):
        ris = get_object_or_404(
            MissioneRisoluzione.objects.select_related("personaggio", "missione"),
            pk=risoluzione_id,
        )
        user = request.user
        is_staff = bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
        if not is_staff and ris.personaggio.proprietario_id != user.id:
            return Response({"detail": "Non autorizzato."}, status=403)
        try:
            ris = reclama_ricompensa(ris)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(MissioneRisoluzioneSerializer(ris).data)


class MissioneRisoluzioneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MissioneRisoluzione.objects.all().select_related(
        "missione", "evento", "personaggio"
    )
    serializer_class = MissioneRisoluzioneSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        evento = self.request.query_params.get("evento")
        if evento:
            qs = qs.filter(evento_id=evento)
        missione = self.request.query_params.get("missione")
        if missione:
            qs = qs.filter(missione_id=missione)
        personaggio = self.request.query_params.get("personaggio")
        if personaggio:
            qs = qs.filter(personaggio_id=personaggio)
        giorno = self.request.query_params.get("giorno")
        if giorno:
            qs = qs.filter(giorno_id=giorno)
        quest = self.request.query_params.get("quest")
        if quest:
            qs = qs.filter(quest_id=quest)
        return qs
