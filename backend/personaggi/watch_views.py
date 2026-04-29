import hashlib
import secrets
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings

from .models import (
    Campagna,
    Personaggio,
    WatchDeviceBinding,
    WatchDeviceEventLog,
    WatchPairingCode,
)
from .serializers import PersonaggioDetailSerializer
from .watch_serializers import (
    WatchDeviceBindingSerializer,
    WatchDisconnectSerializer,
    WatchPairConfirmSerializer,
    WatchPairStatusSerializer,
    WatchPairStartSerializer,
    WatchSyncSerializer,
)

PAIR_CODE_TTL_SECONDS = 120


def _active_campaign(request):
    slug = (request.headers.get("X-Campagna") or request.query_params.get("campagna") or "kor35").strip().lower()
    return Campagna.objects.filter(slug=slug, attiva=True).first() or Campagna.objects.filter(slug="kor35").first()


def _hash_code(raw_code):
    return hashlib.sha256(raw_code.encode("utf-8")).hexdigest()


def _new_pair_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


def _pair_token():
    return secrets.token_urlsafe(32)


def _broadcast_watch_sync(personaggio_id):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        "kor35_notifications",
        {
            "type": "send_notification",
            "message": {
                "action": "WATCH_SYNC",
                "payload": {"personaggio_id": int(personaggio_id)},
            },
        },
    )


def _apply_watch_delta(personaggio, stat_sigla, delta):
    delta = int(delta or 0)
    if delta == 0:
        return
    current = int(personaggio.get_risorsa_corrente(stat_sigla))
    max_v = int(personaggio.get_valore_massimo_risorsa_runtime(stat_sigla))
    if max_v < 0:
        max_v = 0
    new_value = max(0, min(max_v, current + delta))
    personaggio.imposta_risorsa_pool_tattica(stat_sigla, new_value)
    if stat_sigla == "PV":
        from .views import _sync_coma_state  # import locale per evitare dipendenze circolari hard

        _sync_coma_state(personaggio)


class WatchPairStartView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = WatchPairStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        campaign = _active_campaign(request)
        if not campaign:
            return Response({"error": "Campagna non trovata."}, status=status.HTTP_400_BAD_REQUEST)

        raw_code = _new_pair_code()
        expires_at = timezone.now() + timedelta(seconds=PAIR_CODE_TTL_SECONDS)

        WatchPairingCode.objects.create(
            campagna=campaign,
            device_id=data["device_id"].strip(),
            code_hash=_hash_code(raw_code),
            expires_at=expires_at,
        )
        return Response(
            {
                "status": "ok",
                "pairing_code": raw_code,
                "expires_at": expires_at.isoformat(),
                "expires_in_seconds": PAIR_CODE_TTL_SECONDS,
            },
            status=status.HTTP_201_CREATED,
        )


class WatchPairConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = WatchPairConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        campaign = _active_campaign(request)
        pg = get_object_or_404(Personaggio, pk=data["char_id"], proprietario=request.user, campagna=campaign)
        if not pg.watch_enabled:
            return Response({"error": "Watch non abilitato da staff su questo personaggio."}, status=status.HTTP_403_FORBIDDEN)

        raw_code = str(data["code"]).strip().upper()
        code_hash = _hash_code(raw_code)
        now = timezone.now()
        pair_row = (
            WatchPairingCode.objects.select_for_update()
            .filter(campagna=campaign, code_hash=code_hash, used_at__isnull=True, expires_at__gte=now)
            .order_by("-created_at")
            .first()
        )
        if not pair_row:
            return Response({"error": "Codice pairing non valido o scaduto."}, status=status.HTTP_400_BAD_REQUEST)

        WatchDeviceBinding.objects.filter(personaggio=pg, is_active=True).update(is_active=False, updated_at=now)
        WatchDeviceBinding.objects.filter(device_id=pair_row.device_id, is_active=True).update(is_active=False, updated_at=now)

        binding = WatchDeviceBinding.objects.create(
            campagna=campaign,
            personaggio=pg,
            device_id=pair_row.device_id,
            pair_token=_pair_token(),
            transport_mode=data["transport_mode"],
            is_active=True,
            last_seen_at=now,
        )
        pair_row.used_at = now
        pair_row.save(update_fields=["used_at", "updated_at"])
        _broadcast_watch_sync(pg.id)
        return Response(
            {
                "status": "ok",
                "binding": WatchDeviceBindingSerializer(binding).data,
                "pair_token": binding.pair_token,
            }
        )


class WatchPairStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        serializer = WatchPairStatusSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        campaign = _active_campaign(request)
        if not campaign:
            return Response({"error": "Campagna non trovata."}, status=status.HTTP_400_BAD_REQUEST)

        raw_code = str(data["code"]).strip().upper()
        pair_row = (
            WatchPairingCode.objects.filter(
                campagna=campaign,
                device_id=data["device_id"].strip(),
                code_hash=_hash_code(raw_code),
            )
            .order_by("-created_at")
            .first()
        )
        if not pair_row:
            return Response({"status": "invalid"}, status=status.HTTP_200_OK)
        if pair_row.used_at is None:
            if pair_row.expires_at < timezone.now():
                return Response({"status": "expired"}, status=status.HTTP_200_OK)
            return Response({"status": "pending"}, status=status.HTTP_200_OK)

        binding = (
            WatchDeviceBinding.objects.filter(
                campagna=campaign,
                device_id=data["device_id"].strip(),
                is_active=True,
                updated_at__gte=pair_row.used_at - timedelta(seconds=5),
            )
            .order_by("-updated_at")
            .first()
        )
        if not binding:
            return Response({"status": "pending"}, status=status.HTTP_200_OK)
        return Response(
            {
                "status": "paired",
                "pair_token": binding.pair_token,
                "binding": WatchDeviceBindingSerializer(binding).data,
            },
            status=status.HTTP_200_OK,
        )


class WatchDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = WatchDisconnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pg = get_object_or_404(Personaggio, pk=serializer.validated_data["char_id"], proprietario=request.user)
        updated = WatchDeviceBinding.objects.filter(personaggio=pg, is_active=True).update(is_active=False, updated_at=timezone.now())
        _broadcast_watch_sync(pg.id)
        return Response({"status": "ok", "disconnected": int(updated)})


class WatchBindingStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        char_id = request.query_params.get("char_id")
        pg = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user)
        binding = (
            WatchDeviceBinding.objects.filter(personaggio=pg, is_active=True)
            .order_by("-updated_at")
            .first()
        )
        return Response(
            {
                "watch_enabled": bool(pg.watch_enabled),
                "binding": WatchDeviceBindingSerializer(binding).data if binding else None,
            }
        )


class WatchProfileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        device_id = str(request.query_params.get("device_id") or "").strip()
        pair_token = str(request.headers.get("X-KOR35-Pair-Token") or "").strip()
        if not device_id or not pair_token:
            return Response({"error": "device_id e token obbligatori."}, status=status.HTTP_400_BAD_REQUEST)
        binding = (
            WatchDeviceBinding.objects.filter(device_id=device_id, pair_token=pair_token, is_active=True)
            .select_related("personaggio")
            .first()
        )
        if not binding:
            return Response({"error": "Binding non valido."}, status=status.HTTP_403_FORBIDDEN)
        binding.last_seen_at = timezone.now()
        binding.save(update_fields=["last_seen_at", "updated_at"])
        detail = PersonaggioDetailSerializer(binding.personaggio).data
        return Response(
            {
                "status": "ok",
                "personaggio": {
                    "id": detail.get("id"),
                    "nome": detail.get("nome"),
                    "statistiche_primarie": detail.get("statistiche_primarie", []),
                    "risorse_pool_ui": detail.get("risorse_pool_ui", []),
                    "impostazioni_ui": detail.get("impostazioni_ui", {}),
                },
                "timers": detail.get("rigenerazioni_auto_ui", []),
            }
        )


class WatchSyncView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = WatchSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        pair_token = str(request.headers.get("X-KOR35-Pair-Token") or "").strip()
        if not pair_token:
            return Response({"error": "Token mancante."}, status=status.HTTP_400_BAD_REQUEST)
        binding = (
            WatchDeviceBinding.objects.select_for_update()
            .select_related("personaggio")
            .filter(device_id=data["device_id"], pair_token=pair_token, is_active=True)
            .first()
        )
        if not binding:
            return Response({"error": "Binding non valido."}, status=status.HTTP_403_FORBIDDEN)

        if data.get("firmware_version"):
            binding.firmware_version = data["firmware_version"]
        binding.last_seen_at = timezone.now()
        binding.save(update_fields=["firmware_version", "last_seen_at", "updated_at"])

        pg = binding.personaggio
        applied_events = 0
        for event in data.get("events", []):
            event_id = event["client_event_id"]
            if WatchDeviceEventLog.objects.filter(binding=binding, client_event_id=event_id).exists():
                continue
            _apply_watch_delta(pg, event["stat_sigla"], event["delta"])
            WatchDeviceEventLog.objects.create(
                binding=binding,
                personaggio=pg,
                client_event_id=event_id,
                stat_sigla=event["stat_sigla"],
                delta=event["delta"],
                applied=True,
            )
            applied_events += 1

        pg.save(update_fields=["risorse_consumabili", "impostazioni_ui", "updated_at"])
        _broadcast_watch_sync(pg.id)
        detail = PersonaggioDetailSerializer(pg).data
        return Response(
            {
                "status": "ok",
                "applied_events": applied_events,
                "risorse_pool_ui": detail.get("risorse_pool_ui", []),
                "impostazioni_ui": detail.get("impostazioni_ui", {}),
            }
        )


class WatchOtaManifestView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not getattr(settings, "WATCH_OTA_ENABLED", True):
            return Response({"enabled": False}, status=status.HTTP_404_NOT_FOUND)
        version = str(getattr(settings, "WATCH_OTA_VERSION", "0.1.0"))
        bin_path = str(getattr(settings, "WATCH_OTA_BIN_PATH", "/watch-ota/lilygo-twatch-2021/firmware.bin"))
        if not bin_path.startswith("/"):
            bin_path = f"/{bin_path}"
        firmware_url = request.build_absolute_uri(bin_path)
        return Response(
            {
                "enabled": True,
                "version": version,
                "firmware_url": firmware_url,
                "min_battery_pct": 30,
            },
            status=status.HTTP_200_OK,
        )


class WatchWearManifestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        char_id = request.query_params.get("char_id")
        campaign = _active_campaign(request)
        pg = get_object_or_404(Personaggio, pk=char_id, proprietario=request.user, campagna=campaign)
        if not pg.watch_enabled:
            return Response({"error": "Watch non abilitato da staff su questo personaggio."}, status=status.HTTP_403_FORBIDDEN)
        if not getattr(settings, "WATCH_WEAR_ENABLED", True):
            return Response({"enabled": False}, status=status.HTTP_404_NOT_FOUND)

        version = str(getattr(settings, "WATCH_WEAR_VERSION", "0.1.0"))
        apk_path = str(getattr(settings, "WATCH_WEAR_APK_PATH", "/watch-apps/wearos-kor35/app-release.apk"))
        if not apk_path.startswith("/"):
            apk_path = f"/{apk_path}"
        apk_url = request.build_absolute_uri(apk_path)
        return Response(
            {
                "enabled": True,
                "version": version,
                "apk_url": apk_url,
                "platform": "wearos",
            },
            status=status.HTTP_200_OK,
        )
