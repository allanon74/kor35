from rest_framework import serializers

from .models import WatchDeviceBinding


class WatchPairStartSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=96)
    firmware_version = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")


class WatchPairStatusSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=96)
    code = serializers.CharField(max_length=12)


class WatchPairConfirmSerializer(serializers.Serializer):
    char_id = serializers.IntegerField()
    code = serializers.CharField(max_length=12)
    transport_mode = serializers.ChoiceField(choices=["WIFI", "BT_BRIDGE"], required=False, default="WIFI")


class WatchDisconnectSerializer(serializers.Serializer):
    char_id = serializers.IntegerField()


class WatchStatEventSerializer(serializers.Serializer):
    client_event_id = serializers.CharField(max_length=80)
    stat_sigla = serializers.ChoiceField(choices=["PV", "PA", "PS", "CHA"])
    delta = serializers.IntegerField(min_value=-1, max_value=1)


class WatchSyncSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=96)
    firmware_version = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    events = WatchStatEventSerializer(many=True, required=False, default=list)


class WatchDeviceBindingSerializer(serializers.ModelSerializer):
    personaggio_id = serializers.IntegerField(source="personaggio.id", read_only=True)
    personaggio_nome = serializers.CharField(source="personaggio.nome", read_only=True)

    class Meta:
        model = WatchDeviceBinding
        fields = (
            "id",
            "device_id",
            "transport_mode",
            "is_active",
            "last_seen_at",
            "firmware_version",
            "personaggio_id",
            "personaggio_nome",
        )
