"""
Serializer DRF per l'app pilotaggio.

Espone i cataloghi (sottosistemi, comandi, eventi, sequenze) e lo stato
runtime (sessione di volo, evento attivo, sottosistemi).
"""
from __future__ import annotations

from rest_framework import serializers

from .models import (
    ComandoNave,
    EventoAttivoSessione,
    EventoNave,
    IntensitaComando,
    PilotConsoleToken,
    SequenzaVolo,
    SessioneVolo,
    SottosistemaNave,
    StatoSottosistemaSessione,
    TentativoCodice,
)


class SottosistemaNaveSerializer(serializers.ModelSerializer):
    """
    Non espone a_vista né id QR grezzi: solo stato sintetico per l'interfaccia staff.
    """

    stato_qr = serializers.SerializerMethodField()

    class Meta:
        model = SottosistemaNave
        fields = [
            "id",
            "codice",
            "nome",
            "descrizione",
            "durata_ripristino_secondi",
            "attivo",
            "stato_qr",
        ]
        read_only_fields = ["id", "stato_qr"]

    def get_stato_qr(self, obj):
        """nessuno = no vista; incompleto = vista senza QR; pronto = QR collegato alla vista."""
        if not obj.a_vista_id:
            return "nessuno"
        try:
            qr = getattr(obj.a_vista, "qrcode", None)
        except Exception:
            qr = None
        return "pronto" if qr else "incompleto"


class ComandoNaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComandoNave
        fields = ["id", "codice", "nome", "descrizione", "attivo"]
        read_only_fields = ["id"]


class IntensitaComandoSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntensitaComando
        fields = ["id", "valore", "nome", "descrizione", "attivo"]
        read_only_fields = ["id"]


class EventoNaveSerializer(serializers.ModelSerializer):
    sottosistema_codice = serializers.CharField(
        source="sottosistema.codice", read_only=True, default=None
    )

    class Meta:
        model = EventoNave
        fields = [
            "id",
            "nome",
            "descrizione",
            "codice_soluzione_esatta",
            "codici_soluzione_parziale",
            "durata_base_secondi",
            "peso_random",
            "sottosistema",
            "sottosistema_codice",
            "attivo",
        ]
        read_only_fields = ["id", "sottosistema_codice"]


class SequenzaVoloSerializer(serializers.ModelSerializer):
    class Meta:
        model = SequenzaVolo
        fields = ["id", "tipo", "nome", "codici", "attiva"]
        read_only_fields = ["id"]


class StatoSottosistemaRuntimeSerializer(serializers.ModelSerializer):
    codice = serializers.CharField(source="sottosistema.codice", read_only=True)
    nome = serializers.CharField(source="sottosistema.nome", read_only=True)

    class Meta:
        model = StatoSottosistemaSessione
        fields = [
            "id",
            "codice",
            "nome",
            "online",
            "guasto_at",
            "recovery_at",
        ]


class EventoAttivoSerializer(serializers.ModelSerializer):
    nome = serializers.CharField(source="evento.nome", read_only=True)
    descrizione = serializers.CharField(source="evento.descrizione", read_only=True)

    class Meta:
        model = EventoAttivoSessione
        fields = [
            "id",
            "nome",
            "descrizione",
            "deadline_at",
            "esito",
            "codice_inserito",
            "risolto_at",
        ]


class TentativoCodiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TentativoCodice
        fields = [
            "id",
            "codice",
            "esito",
            "defcon_pre",
            "defcon_post",
            "note",
            "created_at",
        ]


class SessioneVoloSerializer(serializers.ModelSerializer):
    pilota_nome = serializers.CharField(source="pilota.nome", read_only=True)
    partenza_nome = serializers.CharField(
        source="prefettura_partenza.nome", read_only=True, default=None
    )
    arrivo_nome = serializers.CharField(
        source="prefettura_arrivo.nome", read_only=True, default=None
    )

    class Meta:
        model = SessioneVolo
        fields = [
            "id",
            "stato",
            "defcon",
            "durata_pianificata_secondi",
            "started_at",
            "decollo_completato_at",
            "atterraggio_iniziato_at",
            "ended_at",
            "decollo_idx",
            "atterraggio_idx",
            "next_event_at",
            "pilota",
            "pilota_nome",
            "prefettura_partenza",
            "prefettura_arrivo",
            "partenza_nome",
            "arrivo_nome",
        ]
        read_only_fields = fields


class PilotConsoleTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = PilotConsoleToken
        fields = ["id", "token", "pilota", "created_at", "revocato_at"]
        read_only_fields = fields
