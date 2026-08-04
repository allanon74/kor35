"""API Task/Missioni."""
from __future__ import annotations

from django.db.models import Count, Prefetch
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

from personaggi.campagna_moduli import MODULO_TASKS, ModuloStaffGateMixin
from personaggi.models import Personaggio, PropostaTecnica

from .models import Evento, GiornoEvento, Missione, MissioneEvento, MissioneRisoluzione, Quest
from .missioni_service import (
    assegna_risoluzione,
    lista_missioni_per_personaggio,
    riepilogo_premi_evento,
)
from .views import IsMasterOrReadOnly, _is_campaign_staff_plus


class IsStaffOrMasterWrite(permissions.BasePermission):
    """Lettura autenticata; scrittura Master/Staffer (campagna)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return _is_campaign_staff_plus(request)


class MissioneListSerializer(ModelSerializer):
    """Payload leggero per la lista staff (niente nested eventi completi)."""

    korp_nome = CharField(source="korp.nome", read_only=True, allow_null=True)
    eventi_count = IntegerField(read_only=True)

    class Meta:
        model = Missione
        fields = (
            "id",
            "titolo",
            "korp",
            "korp_nome",
            "esclusiva",
            "reward_crediti",
            "reward_prestigio",
            "tipo_risoluzione",
            "premio_solo_primo",
            "attiva",
            "ordine",
            "eventi_count",
        )


class MissioneSerializer(ModelSerializer):
    """Dettaglio / create / update: include eventi e campi premio avanzati."""

    korp_nome = CharField(source="korp.nome", read_only=True, allow_null=True)
    eventi_ids = ListField(child=IntegerField(), write_only=True, required=False)
    eventi = SerializerMethodField()

    class Meta:
        model = Missione
        fields = (
            "id", "sync_id", "updated_at", "created_at",
            "titolo", "descrizione", "korp", "korp_nome", "esclusiva",
            "reward_crediti", "reward_prestigio", "tipo_risoluzione",
            "premio_solo_primo",
            "malus_non_primo_crediti", "malus_non_primo_prestigio",
            "bonus_successive_crediti", "bonus_successive_prestigio",
            "attiva", "ordine", "eventi", "eventi_ids",
        )
        read_only_fields = ("id", "sync_id", "updated_at", "created_at", "korp_nome")

    def get_eventi(self, obj):
        # Prefetch ordinato in get_queryset (retrieve/write).
        return [{"id": e.id, "titolo": e.titolo} for e in obj.eventi.all()]

    def validate(self, attrs):
        esclusiva = attrs.get("esclusiva", getattr(self.instance, "esclusiva", False))
        korp = attrs.get("korp", getattr(self.instance, "korp", None))
        if esclusiva and not korp:
            raise ValidationError({"esclusiva": "Una task esclusiva richiede una KORP."})
        if korp is not None and getattr(getattr(korp, "tipo_carriera", None), "codice", None) != "korp":
            raise ValidationError({"korp": "La carriera selezionata non è una KORP."})
        return attrs

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
            "id", "sync_id", "updated_at", "created_at",
            "missione", "missione_titolo", "evento", "evento_titolo",
            "personaggio", "personaggio_nome", "resolved_at", "is_primo",
            "reward_crediti", "reward_prestigio",
            "ricompensa_reclamata", "reclamata_at",
            "proposta_tecnica", "social_post", "quest", "giorno", "note",
        )
        read_only_fields = fields


class AssegnaRisoluzioneSerializer(Serializer):
    missione_id = UUIDField()
    evento_id = IntegerField()
    personaggio_id = IntegerField()
    proposta_tecnica_id = IntegerField(required=False, allow_null=True)
    social_post_id = IntegerField(required=False, allow_null=True)
    quest_id = IntegerField(required=False, allow_null=True)
    giorno_id = IntegerField(required=False, allow_null=True)
    note = CharField(required=False, allow_blank=True, default="")


class MissioneViewSet(ModuloStaffGateMixin, viewsets.ModelViewSet):
    modulo_key = MODULO_TASKS
    queryset = Missione.objects.all().select_related("korp")
    serializer_class = MissioneSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return MissioneListSerializer
        return MissioneSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve", "mie", "riepilogo_evento"):
            return [permissions.IsAuthenticated()]
        if self.action == "assegna":
            return [permissions.IsAuthenticated(), IsStaffOrMasterWrite()]
        # CRUD definizione: Master (IsMasterOrReadOnly già richiede staff+ e write=master)
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
        if getattr(self, "action", None) == "list":
            return qs.annotate(eventi_count=Count("eventi", distinct=True)).distinct()
        # retrieve / write: prefetch eventi per MissioneSerializer.get_eventi
        return qs.distinct().prefetch_related(
            Prefetch("eventi", queryset=Evento.objects.order_by("-data_inizio")),
        )

    @action(detail=False, methods=["get"], url_path="mie")
    def mie(self, request):
        from personaggi.campagna_moduli import modulo_gate_response

        pg_id = request.query_params.get("personaggio")
        if not pg_id:
            return Response({"detail": "Parametro personaggio obbligatorio."}, status=400)
        pg = get_object_or_404(Personaggio, pk=pg_id)
        user = request.user
        is_staff = _is_campaign_staff_plus(request)
        if not is_staff and pg.proprietario_id != user.id:
            return Response({"detail": "Non autorizzato."}, status=403)
        gate = modulo_gate_response(pg, MODULO_TASKS, user=user, error_key="detail")
        if gate:
            return gate
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
        from personaggi.campagna_moduli import modulo_gate_response

        ser = AssegnaRisoluzioneSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        missione = get_object_or_404(Missione, pk=data["missione_id"])
        evento = get_object_or_404(Evento, pk=data["evento_id"])
        personaggio = get_object_or_404(Personaggio, pk=data["personaggio_id"])
        gate = modulo_gate_response(
            personaggio, MODULO_TASKS, user=request.user, error_key="detail"
        )
        if gate:
            return gate
        kwargs = {"note": data.get("note") or ""}
        if data.get("proposta_tecnica_id"):
            kwargs["proposta_tecnica"] = get_object_or_404(PropostaTecnica, pk=data["proposta_tecnica_id"])
        if data.get("social_post_id"):
            from social.models import SocialPost
            kwargs["social_post"] = get_object_or_404(SocialPost, pk=data["social_post_id"])
        if data.get("quest_id"):
            kwargs["quest"] = get_object_or_404(Quest, pk=data["quest_id"])
        if data.get("giorno_id"):
            kwargs["giorno"] = get_object_or_404(GiornoEvento, pk=data["giorno_id"])
        try:
            ris = assegna_risoluzione(
                missione=missione, evento=evento, personaggio=personaggio, **kwargs
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(MissioneRisoluzioneSerializer(ris).data, status=201)


class MissioneRisoluzioneViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MissioneRisoluzione.objects.all().select_related("missione", "evento", "personaggio")
    serializer_class = MissioneRisoluzioneSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        for key in ("evento", "missione", "personaggio", "giorno", "quest"):
            val = self.request.query_params.get(key)
            if val:
                qs = qs.filter(**{f"{key}_id": val})
        return qs
