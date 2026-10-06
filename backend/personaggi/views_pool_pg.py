"""API staff: modelli messaggio, invio individuale agli iscritti evento, pool sorteggio."""

from __future__ import annotations

import random
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from gestione_plot.models import Evento
from gestione_plot.permissions import IsStaffOrMaster
from personaggi.models import (
    Messaggio,
    MessaggioModelloStaff,
    Personaggio,
    PersonaggioPool,
    PersonaggioPoolMembro,
    PersonaggioPoolSorteggio,
    PersonaggioPoolSorteggioEsito,
    Statistica,
)
from personaggi.pool_sorteggio import (
    PLACEHOLDER_CAMPI,
    campiona_pesato,
    client_ip,
    conteggi_sorteggi_pool,
    evento_in_corso,
    giocatore_display_name,
    membri_attivi_qs,
    payload_pool_giocatore,
    peso_sorteggio,
    placeholder_context,
    pool_visibile_per_personaggio,
    render_placeholders,
    rimanenti_attivazioni_giocatore,
)
from personaggi.views import _get_active_campaign


def _ws_prioritario(user_id, payload: dict) -> None:
    from personaggi.signals import _ws_notify_users

    if user_id:
        _ws_notify_users([user_id], payload)


def _crea_messaggio_staff_individuale(*, mittente, personaggio, titolo, testo, campagna):
    return Messaggio.objects.create(
        mittente=mittente,
        destinatario_personaggio=personaggio,
        tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
        is_staff_message=True,
        titolo=(titolo or "Messaggio staff")[:150],
        testo=testo or "",
        campagna=campagna,
        salva_in_cronologia=True,
    )


def esegui_sorteggio_pool(
    *,
    pool,
    campagna,
    mittente,
    n_min=None,
    n_max=None,
    origine=PersonaggioPoolSorteggio.ORIGINE_STAFF,
    avviato_da_personaggio=None,
):
    """Estrazione pesata condivisa tra staff e attivazione giocatore.

    In caso di errore restituisce una Response DRF; altrimenti il payload JSON.
    """
    try:
        n_min = int(n_min if n_min is not None else pool.sorteggio_min)
        n_max = int(n_max if n_max is not None else pool.sorteggio_max)
    except (TypeError, ValueError):
        return Response({"error": "Numeri di sorteggio non validi."}, status=400)
    if n_min < 1:
        return Response({"error": "Il minimo deve essere almeno 1."}, status=400)
    if n_max < n_min:
        n_min, n_max = n_max, n_min
    attivi = list(membri_attivi_qs(pool))
    if not attivi:
        return Response({"error": "Nessun personaggio attivo nel pool."}, status=400)
    if n_max > len(attivi):
        n_max = len(attivi)
    if n_min > n_max:
        n_min = n_max
    k = random.randint(n_min, n_max)
    counts = conteggi_sorteggi_pool(pool)
    fattore = float(pool.fattore_peso)
    candidati = [(pg, peso_sorteggio(fattore, counts.get(pg.id, 0))) for pg in attivi]
    estratti = campiona_pesato(candidati, k)
    evento = evento_in_corso()
    prioritario = bool(pool.invio_prioritario)
    now = timezone.now()
    titolo_default = (
        "Sorteggio staff"
        if origine == PersonaggioPoolSorteggio.ORIGINE_STAFF
        else f"Sorteggio {pool.nome}"
    )

    with transaction.atomic():
        sorteggio = PersonaggioPoolSorteggio.objects.create(
            pool=pool,
            campagna=campagna,
            creato_da=mittente,
            origine=origine,
            avviato_da_personaggio=avviato_da_personaggio,
            evento=evento,
            n_min=n_min,
            n_max=n_max,
            n_estratti=len(estratti),
            fattore_usato=pool.fattore_peso,
            prioritario=prioritario,
            messaggio_titolo_snapshot=pool.messaggio_titolo,
            messaggio_testo_snapshot=pool.messaggio_testo,
        )
        esiti_payload = []
        for pg in estratti:
            pregressi = counts.get(pg.id, 0)
            peso = peso_sorteggio(fattore, pregressi)
            ctx = placeholder_context(personaggio=pg, pool=pool, evento=evento, when=now)
            titolo = render_placeholders(pool.messaggio_titolo or titolo_default, ctx)
            testo = render_placeholders(pool.messaggio_testo or "", ctx)
            messaggio = None
            if (pool.messaggio_titolo or "").strip() or (pool.messaggio_testo or "").strip():
                messaggio = _crea_messaggio_staff_individuale(
                    mittente=mittente,
                    personaggio=pg,
                    titolo=titolo,
                    testo=testo or titolo,
                    campagna=campagna,
                )
            esito = PersonaggioPoolSorteggioEsito.objects.create(
                sorteggio=sorteggio,
                pool=pool,
                personaggio=pg,
                peso=Decimal(str(round(peso, 6))),
                sorteggi_pregressi=pregressi,
                messaggio=messaggio,
                ack_richiesto=prioritario,
            )
            if prioritario and pg.proprietario_id:
                _ws_prioritario(
                    pg.proprietario_id,
                    {
                        "action": "MSG_PRIORITARIO",
                        "esito_id": str(esito.id),
                        "messaggio_id": messaggio.id if messaggio else None,
                        "titolo": titolo,
                        "testo": testo or titolo,
                        "destinatario_id": pg.id,
                        "tipo": "INDV",
                    },
                )
            esiti_payload.append(
                {
                    "id": str(esito.id),
                    "personaggio_id": pg.id,
                    "personaggio_nome": pg.nome,
                    "giocatore_nome": giocatore_display_name(pg.proprietario),
                    "peso": str(esito.peso),
                    "sorteggi_pregressi": pregressi,
                    "messaggio_id": messaggio.id if messaggio else None,
                    "ack_richiesto": prioritario,
                }
            )

    return {
        "sorteggio_id": str(sorteggio.id),
        "n_estratti": len(estratti),
        "n_min": n_min,
        "n_max": n_max,
        "evento_id": evento.id if evento else None,
        "evento_titolo": evento.titolo if evento else "",
        "prioritario": prioritario,
        "origine": origine,
        "esiti": esiti_payload,
    }


def _personaggio_richiedente(request):
    personaggio_id = request.query_params.get("personaggio_id") or request.data.get(
        "personaggio_id"
    )
    if not personaggio_id:
        return None, Response({"error": "personaggio_id obbligatorio."}, status=400)
    pg = Personaggio.objects.filter(
        pk=personaggio_id,
        proprietario=request.user,
        eliminato_at__isnull=True,
    ).first()
    if not pg:
        return None, Response({"error": "Personaggio non trovato."}, status=404)
    return pg, None


class MessaggioModelloStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessaggioModelloStaff
        fields = ("id", "nome", "titolo", "testo", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class MessaggioModelloStaffViewSet(viewsets.ModelViewSet):
    serializer_class = MessaggioModelloStaffSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrMaster]
    pagination_class = None

    def get_queryset(self):
        campagna = _get_active_campaign(self.request)
        return MessaggioModelloStaff.objects.filter(campagna=campagna).order_by("nome")

    def perform_create(self, serializer):
        serializer.save(
            campagna=_get_active_campaign(self.request),
            creato_da=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(campagna=_get_active_campaign(self.request))


class MessaggioEventoInvioView(APIView):
    """Invia un messaggio individuale (inbox + notifiche) a ogni PG iscritto all'evento."""

    permission_classes = [permissions.IsAuthenticated, IsStaffOrMaster]

    @transaction.atomic
    def post(self, request):
        campagna = _get_active_campaign(request)
        evento_id = request.data.get("evento_id")
        destinatario_id = request.data.get("destinatario_id")
        titolo = (request.data.get("titolo") or "").strip()
        testo = request.data.get("testo") or ""
        if not titolo or not testo.strip():
            return Response({"error": "Titolo e testo sono obbligatori."}, status=400)
        if destinatario_id and not evento_id:
            pg = get_object_or_404(
                Personaggio, pk=destinatario_id, campagna=campagna, eliminato_at__isnull=True
            )
            msg = _crea_messaggio_staff_individuale(
                mittente=request.user,
                personaggio=pg,
                titolo=titolo,
                testo=testo,
                campagna=campagna,
            )
            return Response({"inviati": 1, "messaggio_ids": [msg.id]}, status=201)
        if not evento_id:
            return Response({"error": "evento_id obbligatorio."}, status=400)
        evento = get_object_or_404(Evento, pk=evento_id)
        destinatari = list(
            evento.partecipanti.filter(campagna=campagna, eliminato_at__isnull=True)
            .select_related("proprietario")
            .distinct()
        )
        if not destinatari:
            return Response(
                {"error": "Nessun personaggio iscritto a questo evento nella campagna attiva."},
                status=400,
            )
        creati = []
        for pg in destinatari:
            ctx = placeholder_context(personaggio=pg, pool=type("X", (), {"nome": ""})(), evento=evento)
            msg = _crea_messaggio_staff_individuale(
                mittente=request.user,
                personaggio=pg,
                titolo=render_placeholders(titolo, ctx),
                testo=render_placeholders(testo, ctx),
                campagna=campagna,
            )
            creati.append(msg.id)
        return Response(
            {
                "inviati": len(creati),
                "evento_id": evento.id,
                "evento_titolo": evento.titolo,
                "messaggio_ids": creati,
            },
            status=201,
        )


class PersonaggioPoolSerializer(serializers.ModelSerializer):
    attivi_count = serializers.SerializerMethodField()
    sorteggi_count = serializers.SerializerMethodField()
    statistica_sigla = serializers.SerializerMethodField()
    statistica_nome = serializers.SerializerMethodField()

    class Meta:
        model = PersonaggioPool
        fields = (
            "id",
            "nome",
            "escludi_png",
            "sorteggio_min",
            "sorteggio_max",
            "fattore_peso",
            "messaggio_titolo",
            "messaggio_testo",
            "invio_prioritario",
            "max_sorteggi_giorno",
            "statistica",
            "statistica_sigla",
            "statistica_nome",
            "created_at",
            "updated_at",
            "attivi_count",
            "sorteggi_count",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "attivi_count",
            "sorteggi_count",
            "statistica_sigla",
            "statistica_nome",
        )

    def get_attivi_count(self, obj):
        if getattr(obj, "attivi_count", None) is not None:
            return obj.attivi_count
        if not obj.pk:
            return 0
        return obj.membri.filter(attivo=True).count()

    def get_sorteggi_count(self, obj):
        if getattr(obj, "sorteggi_count", None) is not None:
            return obj.sorteggi_count
        if not obj.pk:
            return 0
        return obj.sorteggi.count()

    def get_statistica_sigla(self, obj):
        stat = getattr(obj, "statistica", None)
        return (stat.sigla if stat else "") or ""

    def get_statistica_nome(self, obj):
        stat = getattr(obj, "statistica", None)
        return (stat.nome if stat else "") or ""

    def validate(self, attrs):
        smin = attrs.get("sorteggio_min", getattr(self.instance, "sorteggio_min", 1))
        smax = attrs.get("sorteggio_max", getattr(self.instance, "sorteggio_max", 1))
        try:
            smin = int(smin)
            smax = int(smax)
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError("I numeri di sorteggio devono essere interi.") from exc
        if smin < 1:
            raise serializers.ValidationError({"sorteggio_min": "Minimo 1."})
        if smax < smin:
            raise serializers.ValidationError({"sorteggio_max": "Il massimo deve essere ≥ al minimo."})
        fattore = attrs.get("fattore_peso", getattr(self.instance, "fattore_peso", Decimal("0.8")))
        try:
            f = Decimal(str(fattore))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise serializers.ValidationError({"fattore_peso": "Fattore non valido."}) from exc
        if f < 0:
            raise serializers.ValidationError({"fattore_peso": "Il fattore non può essere negativo."})
        massimo = attrs.get(
            "max_sorteggi_giorno",
            getattr(self.instance, "max_sorteggi_giorno", 0),
        )
        try:
            massimo = int(massimo or 0)
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError(
                {"max_sorteggi_giorno": "Deve essere un intero ≥ 0."}
            ) from exc
        if massimo < 0:
            raise serializers.ValidationError({"max_sorteggi_giorno": "Non può essere negativo."})
        attrs["sorteggio_min"] = smin
        attrs["sorteggio_max"] = smax
        attrs["fattore_peso"] = f
        attrs["max_sorteggi_giorno"] = massimo
        return attrs


class PersonaggioPoolStaffViewSet(viewsets.ModelViewSet):
    serializer_class = PersonaggioPoolSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrMaster]
    pagination_class = None

    def get_queryset(self):
        campagna = _get_active_campaign(self.request)
        return (
            PersonaggioPool.objects.filter(campagna=campagna)
            .select_related("statistica")
            .annotate(
                attivi_count=Count(
                    "membri",
                    filter=Q(membri__attivo=True),
                    distinct=True,
                ),
                sorteggi_count=Count("sorteggi", distinct=True),
            )
            .order_by("nome")
        )

    def perform_create(self, serializer):
        serializer.save(campagna=_get_active_campaign(self.request))

    def perform_update(self, serializer):
        serializer.save(campagna=_get_active_campaign(self.request))

    @action(detail=False, methods=["get"], url_path="meta")
    def meta(self, request):
        campagna = _get_active_campaign(request)
        eventi = Evento.objects.all().order_by("-data_inizio")
        payload_eventi = [
            {
                "id": ev.id,
                "titolo": ev.titolo,
                "data_inizio": ev.data_inizio,
                "data_fine": ev.data_fine,
                "in_corso": bool(
                    (ev.started_at and not ev.ended_at)
                    or (
                        ev.data_inizio
                        and ev.data_fine
                        and ev.data_inizio <= timezone.now() <= ev.data_fine
                        and not ev.ended_at
                    )
                ),
            }
            for ev in eventi
        ]
        corso = evento_in_corso()
        statistiche = [
            {
                "id": st.id,
                "sigla": st.sigla,
                "nome": st.nome,
                "parametro": st.parametro or "",
            }
            for st in Statistica.objects.order_by("ordine", "nome", "sigla")
        ]
        return Response(
            {
                "placeholders": PLACEHOLDER_CAMPI,
                "eventi": payload_eventi,
                "evento_in_corso_id": corso.id if corso else None,
                "campagna_id": str(campagna.id) if campagna else None,
                "statistiche": statistiche,
            }
        )

    @action(detail=True, methods=["get"], url_path="personaggi")
    def personaggi(self, request, pk=None):
        pool = self.get_object()
        q = (request.query_params.get("q") or "").strip()
        escludi_png = request.query_params.get("escludi_png")
        if escludi_png is None:
            hide_png = pool.escludi_png
        else:
            hide_png = str(escludi_png).lower() in ("1", "true", "yes")
        evento_id = request.query_params.get("evento_id")
        iscritti_ids: set[int] = set()
        if evento_id:
            evento = get_object_or_404(Evento, pk=evento_id)
            iscritti_ids = set(evento.partecipanti.values_list("id", flat=True))

        qs = Personaggio.objects.filter(
            campagna=pool.campagna,
            eliminato_at__isnull=True,
        ).select_related("proprietario", "tipologia")
        if hide_png:
            qs = qs.filter(tipologia__giocante=True)
        if q:
            qs = qs.filter(
                Q(nome__icontains=q)
                | Q(proprietario__username__icontains=q)
                | Q(proprietario__first_name__icontains=q)
                | Q(proprietario__last_name__icontains=q)
            )

        attivi_ids = set(
            PersonaggioPoolMembro.objects.filter(pool=pool, attivo=True).values_list(
                "personaggio_id", flat=True
            )
        )
        counts = conteggi_sorteggi_pool(pool)
        rows = []
        for pg in qs.order_by("nome"):
            iscritto = pg.id in iscritti_ids
            attivo = pg.id in attivi_ids
            rows.append(
                {
                    "id": pg.id,
                    "nome": pg.nome,
                    "giocatore_nome": giocatore_display_name(pg.proprietario),
                    "giocatore_username": pg.proprietario.username if pg.proprietario else "",
                    "is_png": not bool(pg.tipologia and pg.tipologia.giocante),
                    "iscritto_evento": iscritto,
                    "attivo": attivo,
                    "sorteggi_count": counts.get(pg.id, 0),
                }
            )
        if evento_id:
            rows.sort(
                key=lambda r: (
                    0 if r["iscritto_evento"] else (1 if r["attivo"] else 2),
                    r["nome"].lower(),
                )
            )
        else:
            rows.sort(key=lambda r: (0 if r["attivo"] else 1, r["nome"].lower()))
        return Response(
            {
                "results": rows,
                "attivi": len(attivi_ids),
                "totale": len(rows),
            }
        )

    @action(detail=True, methods=["post"], url_path="membri")
    def set_membro(self, request, pk=None):
        pool = self.get_object()
        personaggio_id = request.data.get("personaggio_id")
        attivo = bool(request.data.get("attivo"))
        if not personaggio_id:
            return Response({"error": "personaggio_id obbligatorio."}, status=400)
        pg = get_object_or_404(
            Personaggio,
            pk=personaggio_id,
            campagna=pool.campagna,
            eliminato_at__isnull=True,
        )
        if attivo:
            PersonaggioPoolMembro.objects.update_or_create(
                pool=pool,
                personaggio=pg,
                defaults={"attivo": True},
            )
        else:
            PersonaggioPoolMembro.objects.filter(pool=pool, personaggio=pg).delete()
        return Response({"personaggio_id": pg.id, "attivo": attivo})

    @action(detail=True, methods=["post"], url_path="membri-bulk")
    def set_membri_bulk(self, request, pk=None):
        pool = self.get_object()
        ids = request.data.get("personaggio_ids") or []
        attivo = bool(request.data.get("attivo"))
        if not isinstance(ids, list):
            return Response({"error": "personaggio_ids deve essere una lista."}, status=400)
        pgs = Personaggio.objects.filter(
            id__in=ids,
            campagna=pool.campagna,
            eliminato_at__isnull=True,
        )
        found = {p.id: p for p in pgs}
        with transaction.atomic():
            if attivo:
                for pg in found.values():
                    PersonaggioPoolMembro.objects.update_or_create(
                        pool=pool,
                        personaggio=pg,
                        defaults={"attivo": True},
                    )
            else:
                PersonaggioPoolMembro.objects.filter(pool=pool, personaggio_id__in=found.keys()).delete()
        return Response({"aggiornati": len(found), "attivo": attivo})

    @action(detail=True, methods=["get"], url_path="conteggi")
    def conteggi(self, request, pk=None):
        pool = self.get_object()
        counts = conteggi_sorteggi_pool(pool)
        attivi = membri_attivi_qs(pool)
        rows = []
        for pg in attivi.order_by("nome"):
            n = counts.get(pg.id, 0)
            peso = peso_sorteggio(float(pool.fattore_peso), n)
            rows.append(
                {
                    "id": pg.id,
                    "nome": pg.nome,
                    "giocatore_nome": giocatore_display_name(pg.proprietario),
                    "sorteggi_count": n,
                    "peso": round(peso, 6),
                    "is_png": not bool(pg.tipologia and pg.tipologia.giocante),
                }
            )
        rows.sort(key=lambda r: (-r["sorteggi_count"], r["nome"].lower()))
        tot_peso = sum(r["peso"] for r in rows) or 0
        for r in rows:
            r["probabilita"] = round((r["peso"] / tot_peso), 6) if tot_peso else 0
        return Response(
            {
                "fattore_peso": str(pool.fattore_peso),
                "attivi": len(rows),
                "results": rows,
            }
        )

    @action(detail=True, methods=["get"], url_path="log")
    def log(self, request, pk=None):
        pool = self.get_object()
        sorteggi = (
            PersonaggioPoolSorteggio.objects.filter(pool=pool)
            .select_related("evento", "creato_da", "avviato_da_personaggio")
            .prefetch_related("esiti__personaggio__proprietario", "esiti__messaggio")
            .order_by("-created_at")
        )
        data = []
        for s in sorteggi:
            esiti = []
            for e in s.esiti.all():
                pg = e.personaggio
                esiti.append(
                    {
                        "id": str(e.id),
                        "personaggio_id": pg.id if pg else None,
                        "personaggio_nome": pg.nome if pg else "",
                        "giocatore_nome": giocatore_display_name(pg.proprietario) if pg else "",
                        "peso": str(e.peso),
                        "sorteggi_pregressi": e.sorteggi_pregressi,
                        "messaggio_id": e.messaggio_id,
                        "ack_richiesto": e.ack_richiesto,
                        "confermato_at": e.confermato_at,
                        "confermato_user_agent": e.confermato_user_agent,
                        "confermato_ip": e.confermato_ip,
                        "confermato_dispositivo": e.confermato_dispositivo or {},
                        "created_at": e.created_at,
                    }
                )
            data.append(
                {
                    "id": str(s.id),
                    "created_at": s.created_at,
                    "n_min": s.n_min,
                    "n_max": s.n_max,
                    "n_estratti": s.n_estratti,
                    "fattore_usato": str(s.fattore_usato),
                    "prioritario": s.prioritario,
                    "evento_id": s.evento_id,
                    "evento_titolo": s.evento.titolo if s.evento_id else "",
                    "creato_da": s.creato_da.username if s.creato_da else "",
                    "origine": s.origine,
                    "avviato_da_personaggio_id": s.avviato_da_personaggio_id,
                    "esiti": esiti,
                }
            )
        return Response(data)

    @action(detail=True, methods=["post"], url_path="sorteggia")
    def sorteggia(self, request, pk=None):
        pool = self.get_object()
        campagna = _get_active_campaign(request)
        try:
            n_min = int(request.data.get("sorteggio_min", pool.sorteggio_min) or pool.sorteggio_min)
            n_max = int(request.data.get("sorteggio_max", pool.sorteggio_max) or pool.sorteggio_max)
        except (TypeError, ValueError):
            return Response({"error": "Numeri di sorteggio non validi."}, status=400)
        result = esegui_sorteggio_pool(
            pool=pool,
            campagna=campagna,
            mittente=request.user,
            n_min=n_min,
            n_max=n_max,
            origine=PersonaggioPoolSorteggio.ORIGINE_STAFF,
        )
        if isinstance(result, Response):
            return result
        return Response(result, status=201)


class PoolPgGiocatoreVisibiliView(APIView):
    """Pool visibili in area personaggio (statistica del PG > 0)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        pg, err = _personaggio_richiedente(request)
        if err:
            return err
        campagna = _get_active_campaign(request)
        qs = (
            PersonaggioPool.objects.filter(campagna=campagna, statistica__isnull=False)
            .select_related("statistica")
            .order_by("nome")
        )
        results = [
            payload_pool_giocatore(pool, pg)
            for pool in qs
            if pool.campagna_id == pg.campagna_id and pool_visibile_per_personaggio(pool, pg)
        ]
        return Response({"results": results})


class PoolPgGiocatoreDettaglioView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pool_id):
        pg, err = _personaggio_richiedente(request)
        if err:
            return err
        campagna = _get_active_campaign(request)
        pool = get_object_or_404(
            PersonaggioPool.objects.select_related("statistica"),
            pk=pool_id,
            campagna=campagna,
        )
        if not pool_visibile_per_personaggio(pool, pg):
            return Response({"error": "Pool non visibile per questo personaggio."}, status=404)
        return Response(payload_pool_giocatore(pool, pg, include_esiti=True))


class PoolPgGiocatoreSorteggiaView(APIView):
    """Attivazione giocatore: stesso sorteggio pesato dello staff, con tetto giornaliero."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pool_id):
        pg, err = _personaggio_richiedente(request)
        if err:
            return err
        campagna = _get_active_campaign(request)
        with transaction.atomic():
            pool = (
                PersonaggioPool.objects.select_for_update()
                .filter(pk=pool_id, campagna=campagna)
                .first()
            )
            if not pool:
                return Response({"error": "Pool non trovato."}, status=404)
            if not pool_visibile_per_personaggio(pool, pg):
                return Response(
                    {"error": "Pool non visibile per questo personaggio."},
                    status=404,
                )
            rimanenti = rimanenti_attivazioni_giocatore(pool, pg)
            if rimanenti <= 0:
                return Response(
                    {
                        "error": (
                            "Nessuna attivazione rimanente per oggi."
                            if pool.max_sorteggi_giorno
                            else "Questo pool non ammette attivazioni da parte dei giocatori."
                        )
                    },
                    status=400,
                )
            result = esegui_sorteggio_pool(
                pool=pool,
                campagna=campagna,
                mittente=request.user,
                origine=PersonaggioPoolSorteggio.ORIGINE_GIOCATORE,
                avviato_da_personaggio=pg,
            )
        if isinstance(result, Response):
            return result
        payload = payload_pool_giocatore(pool, pg, include_esiti=True)
        payload.update(
            {
                "sorteggio_id": result["sorteggio_id"],
                "n_estratti": result["n_estratti"],
                "esiti": [
                    {
                        "id": e["id"],
                        "personaggio_nome": e["personaggio_nome"],
                    }
                    for e in result.get("esiti") or []
                ],
            }
        )
        return Response(payload, status=201)


class SorteggioAckPendingView(APIView):
    """Overlay priorità: elenco conferme ancora aperte per il PG selezionato."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        personaggio_id = request.query_params.get("personaggio_id")
        if not personaggio_id:
            return Response({"error": "personaggio_id obbligatorio."}, status=400)
        pg = get_object_or_404(Personaggio, pk=personaggio_id, proprietario=request.user)
        qs = (
            PersonaggioPoolSorteggioEsito.objects.filter(
                personaggio=pg,
                ack_richiesto=True,
                confermato_at__isnull=True,
            )
            .select_related("messaggio", "sorteggio")
            .order_by("created_at")
        )
        results = []
        for e in qs:
            msg = e.messaggio
            results.append(
                {
                    "esito_id": str(e.id),
                    "titolo": (msg.titolo if msg else e.sorteggio.messaggio_titolo_snapshot) or "Messaggio staff",
                    "testo": (msg.testo if msg else e.sorteggio.messaggio_testo_snapshot) or "",
                    "created_at": e.created_at,
                }
            )
        return Response(results)


class SorteggioAckConfermaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, esito_id):
        personaggio_id = request.data.get("personaggio_id")
        if not personaggio_id:
            return Response({"error": "personaggio_id obbligatorio."}, status=400)
        pg = get_object_or_404(Personaggio, pk=personaggio_id, proprietario=request.user)
        esito = get_object_or_404(
            PersonaggioPoolSorteggioEsito,
            pk=esito_id,
            personaggio=pg,
        )
        if not esito.ack_richiesto:
            return Response({"error": "Questo sorteggio non richiede conferma."}, status=400)
        if not esito.confermato_at:
            dispositivo = request.data.get("dispositivo") or {}
            if not isinstance(dispositivo, dict):
                dispositivo = {"raw": str(dispositivo)}
            esito.confermato_at = timezone.now()
            esito.confermato_user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:256]
            esito.confermato_ip = client_ip(request)
            esito.confermato_dispositivo = {
                "platform": str(dispositivo.get("platform") or "")[:80],
                "language": str(dispositivo.get("language") or "")[:32],
                "screen": str(dispositivo.get("screen") or "")[:40],
                "native": bool(dispositivo.get("native")),
                "timezone": str(dispositivo.get("timezone") or "")[:64],
            }
            esito.save(
                update_fields=[
                    "confermato_at",
                    "confermato_user_agent",
                    "confermato_ip",
                    "confermato_dispositivo",
                    "updated_at",
                ]
            )
        return Response(
            {
                "esito_id": str(esito.id),
                "confermato_at": esito.confermato_at,
            }
        )
