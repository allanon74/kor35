"""
Serializers Card Studio / Card Arena (piattaforma).
"""
from rest_framework import serializers

from personaggi.carte_platform_models import (
    CarteArenaRuleset,
    CarteGiocoDefinizione,
    CartePlatformExchangeJob,
    CartePlatformGiocatore,
    CarteStudioTemplate,
)
from personaggi.serializers_carte import _parse_json_field


class CarteGiocoDefinizioneSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarteGiocoDefinizione
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "slug",
            "nome",
            "descrizione",
            "platform_version",
            "studio_abilitato",
            "arena_abilitata",
            "mse_game_name",
            "meta",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "campagna"]

    def validate_meta(self, value):
        parsed = _parse_json_field(value, "meta")
        return parsed if parsed is not None else {}


class CarteStudioTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarteStudioTemplate
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "gioco_definizione",
            "campagna",
            "slug",
            "nome",
            "mse_style_riferimento",
            "layout_spec",
            "campi_schema",
            "attivo",
            "ordine",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "campagna"]

    def validate_layout_spec(self, value):
        parsed = _parse_json_field(value, "layout_spec")
        return parsed if parsed is not None else {}

    def validate_campi_schema(self, value):
        parsed = _parse_json_field(value, "campi_schema")
        return parsed if parsed is not None else {}


class CarteArenaRulesetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarteArenaRuleset
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "gioco_definizione",
            "campagna",
            "ruleset_version",
            "zones_spec",
            "win_conditions",
            "formato_mazzo",
            "effect_engine_version",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "campagna"]

    def validate_zones_spec(self, value):
        parsed = _parse_json_field(value, "zones_spec")
        return parsed if parsed is not None else {}

    def validate_win_conditions(self, value):
        parsed = _parse_json_field(value, "win_conditions")
        return parsed if parsed is not None else {}

    def validate_formato_mazzo(self, value):
        parsed = _parse_json_field(value, "formato_mazzo")
        return parsed if parsed is not None else {}


class CartePlatformGiocatoreSerializer(serializers.ModelSerializer):
    personaggio_nome = serializers.CharField(source="personaggio.nome", read_only=True, allow_null=True)

    class Meta:
        model = CartePlatformGiocatore
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "gioco_definizione",
            "user",
            "personaggio",
            "personaggio_nome",
            "display_name",
            "external_player_ref",
            "meta",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "campagna", "personaggio_nome"]

    def validate_meta(self, value):
        parsed = _parse_json_field(value, "meta")
        return parsed if parsed is not None else {}


class CartePlatformExchangeJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartePlatformExchangeJob
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "gioco_definizione",
            "tipo",
            "stato",
            "richiesto_da",
            "payload",
            "risultato",
            "errore",
            "completato_at",
        ]
        read_only_fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "stato",
            "risultato",
            "errore",
            "completato_at",
        ]

    def validate_payload(self, value):
        parsed = _parse_json_field(value, "payload")
        return parsed if parsed is not None else {}
