"""
Serializers carte collezionabili.
"""
import json

from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from personaggi.carte_collezionabili_models import (
    BustinaCarte,
    CARTE_ACCESSO_OFF,
    CARTE_ACCESSO_OPEN,
    CartaCollezionabile,
    ComboReliquiario,
    ConfigurazioneCarteCollezionabili,
    EspansioneCarte,
    KeywordCarta,
    TagCarta,
)
from personaggi.models import CartaReliquiarioStatistica, ComboReliquiarioStatistica
from personaggi.serializers import StatisticaSerializer


def _parse_json_field(value, field_name):
    if value in (None, "", []):
        return value if value != "" else None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError({field_name: "JSON non valido."}) from exc
    return value


class CartaReliquiarioStatisticaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartaReliquiarioStatistica
        fields = "__all__"
        read_only_fields = ["carta", "id", "sync_id", "created_at", "updated_at"]
        validators = []

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["statistica"] = StatisticaSerializer(instance.statistica).data
        rep["limit_a_aure"] = list(instance.limit_a_aure.values_list("id", flat=True))
        rep["limit_a_elementi"] = list(instance.limit_a_elementi.values_list("id", flat=True))
        return rep


class ComboReliquiarioStatisticaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComboReliquiarioStatistica
        fields = "__all__"
        read_only_fields = ["combo", "id", "sync_id", "created_at", "updated_at"]
        validators = []

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["statistica"] = StatisticaSerializer(instance.statistica).data
        rep["limit_a_aure"] = list(instance.limit_a_aure.values_list("id", flat=True))
        rep["limit_a_elementi"] = list(instance.limit_a_elementi.values_list("id", flat=True))
        return rep


def _save_condizione_stat_rows(model_cls, parent_field, parent_instance, rows):
    if rows is None:
        return
    fk_name = parent_field
    filter_kw = {fk_name: parent_instance}
    model_cls.objects.filter(**filter_kw).delete()
    for item in rows:
        data = dict(item)
        aure = data.pop("limit_a_aure", []) or []
        elementi = data.pop("limit_a_elementi", []) or []
        data.pop("id", None)
        data.pop("sync_id", None)
        data.pop("created_at", None)
        data.pop("updated_at", None)
        stat = data.pop("statistica", None)
        if isinstance(stat, dict):
            stat = stat.get("id")
        if not stat:
            continue
        data["statistica_id"] = stat
        row = model_cls.objects.create(**filter_kw, **data)
        if aure:
            row.limit_a_aure.set(aure)
        if elementi:
            row.limit_a_elementi.set(elementi)


class EspansioneCarteSerializer(serializers.ModelSerializer):
    immagine_url = serializers.SerializerMethodField()
    bustine_count = serializers.SerializerMethodField()
    carte_count = serializers.SerializerMethodField()

    class Meta:
        model = EspansioneCarte
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "nome",
            "slug",
            "descrizione",
            "immagine",
            "immagine_url",
            "ordine",
            "attiva",
            "bustine_count",
            "carte_count",
        ]
        read_only_fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "immagine_url",
            "bustine_count",
            "carte_count",
        ]

    def get_immagine_url(self, obj):
        if obj.immagine:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.immagine.url)
            return obj.immagine.url
        return None

    def get_bustine_count(self, obj):
        return getattr(obj, "bustine_count", None) or obj.bustine.count()

    def get_carte_count(self, obj):
        return getattr(obj, "carte_count", None) or obj.carte.count()

    def validate(self, attrs):
        nome = attrs.get("nome") or (self.instance.nome if self.instance else "")
        slug = attrs.get("slug") or (self.instance.slug if self.instance else "")
        if not slug and nome:
            attrs["slug"] = slugify(nome)[:80]
        if not attrs.get("slug"):
            raise serializers.ValidationError({"slug": "Slug obbligatorio."})
        return attrs


class CartaCollezionabileSerializer(serializers.ModelSerializer):
    immagine_url = serializers.SerializerMethodField()
    espansione_nome = serializers.CharField(source="espansione.nome", read_only=True, allow_null=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=TagCarta.objects.all(),
        source="tags",
        required=False,
    )
    tag_codici = serializers.SerializerMethodField()
    statistiche_reliquiario = CartaReliquiarioStatisticaSerializer(
        source="reliquiario_statistiche",
        many=True,
        required=False,
    )

    class Meta:
        model = CartaCollezionabile
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "espansione",
            "espansione_nome",
            "codice",
            "nome",
            "tipo",
            "energia",
            "rarita",
            "costo_gioco",
            "attacco",
            "salute",
            "iniziativa",
            "testo_gioco",
            "testo_lore",
            "testo_reliquiario",
            "set_collezione",
            "campagna_origine",
            "legame_id",
            "tag_tematici",
            "tag_ids",
            "tag_codici",
            "bonus_equip",
            "effect_scripts",
            "statistiche_reliquiario",
            "duplicabile",
            "immagine",
            "immagine_url",
            "attiva",
            "ordine_set",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "immagine_url", "espansione_nome", "tag_codici"]

    def get_tag_codici(self, obj):
        return [t.codice for t in obj.tags.filter(attiva=True).order_by("nome")]

    def get_immagine_url(self, obj):
        if obj.immagine:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.immagine.url)
            return obj.immagine.url
        return None

    def validate_bonus_equip(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from personaggi.carte_equip_bonus import validate_bonus_equip

        parsed = _parse_json_field(value, "bonus_equip")
        try:
            return validate_bonus_equip(parsed)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

    def validate_effect_scripts(self, value):
        from django.core.exceptions import ValidationError as DjangoValidationError

        from personaggi.carte_carta_effects import validate_carta_effect_scripts

        parsed = _parse_json_field(value, "effect_scripts")
        try:
            return validate_carta_effect_scripts(parsed)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

    def validate_statistiche_reliquiario(self, value):
        return _parse_json_field(value, "statistiche_reliquiario") or []

    def validate_tag_tematici(self, value):
        parsed = _parse_json_field(value, "tag_tematici")
        return parsed if parsed is not None else []

    @transaction.atomic
    def create(self, validated_data):
        stats = validated_data.pop("reliquiario_statistiche", [])
        tags = validated_data.pop("tags", None)
        carta = CartaCollezionabile.objects.create(**validated_data)
        if tags is not None:
            carta.tags.set(tags)
        _save_condizione_stat_rows(CartaReliquiarioStatistica, "carta", carta, stats)
        return carta

    @transaction.atomic
    def update(self, instance, validated_data):
        stats = validated_data.pop("reliquiario_statistiche", None)
        tags = validated_data.pop("tags", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        if stats is not None:
            _save_condizione_stat_rows(CartaReliquiarioStatistica, "carta", instance, stats)
        return instance


class ComboReliquiarioSerializer(serializers.ModelSerializer):
    statistiche = ComboReliquiarioStatisticaSerializer(many=True, required=False)

    class Meta:
        model = ComboReliquiario
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "codice",
            "nome",
            "testo",
            "colore",
            "tipo_trigger",
            "param_legame_id",
            "param_set_collezione",
            "param_carte_codici",
            "param_min_count",
            "ordine",
            "attiva",
            "statistiche",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at"]

    def validate_param_carte_codici(self, value):
        parsed = _parse_json_field(value, "param_carte_codici")
        if parsed is None:
            return []
        if not isinstance(parsed, list):
            raise serializers.ValidationError("Deve essere una lista di codici carta.")
        return [str(c).strip() for c in parsed if str(c).strip()]

    @transaction.atomic
    def create(self, validated_data):
        stats = validated_data.pop("statistiche", [])
        combo = ComboReliquiario.objects.create(**validated_data)
        _save_condizione_stat_rows(ComboReliquiarioStatistica, "combo", combo, stats)
        return combo

    @transaction.atomic
    def update(self, instance, validated_data):
        stats = validated_data.pop("statistiche", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if stats is not None:
            _save_condizione_stat_rows(ComboReliquiarioStatistica, "combo", instance, stats)
        return instance


class BustinaCarteSerializer(serializers.ModelSerializer):
    espansione_nome = serializers.CharField(source="espansione.nome", read_only=True, allow_null=True)
    qr_code_id = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = BustinaCarte
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "espansione",
            "espansione_nome",
            "nome",
            "descrizione",
            "costo_crediti",
            "carte_per_bustina",
            "set_collezione",
            "probabilita_rarita",
            "garantisce_min_rarita",
            "attiva",
            "ordine",
            "qr_code_id",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "qr_code_id", "espansione_nome"]


class ConfigurazioneCarteCollezionabiliSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigurazioneCarteCollezionabili
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "abilitata",
            "accesso_modo",
            "pity_soglia",
            "max_bustine_giorno",
            "mercato_commissione_pct",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at"]

    def validate(self, attrs):
        modo = attrs.get("accesso_modo")
        abilitata = attrs.get("abilitata")
        if modo is None and abilitata is not None and "accesso_modo" not in attrs:
            attrs["accesso_modo"] = CARTE_ACCESSO_OPEN if abilitata else CARTE_ACCESSO_OFF
        elif modo is not None:
            attrs["abilitata"] = modo == CARTE_ACCESSO_OPEN
        return attrs


class TagCartaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TagCarta
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "codice",
            "nome",
            "descrizione",
            "colore",
            "attiva",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "campagna"]

    def validate_codice(self, value):
        return (value or "").strip().upper()


class KeywordCartaSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeywordCarta
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "codice",
            "nome",
            "testo_regola",
            "reminder_breve",
            "priorita",
            "attiva",
            "effect_script",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "campagna"]

    def validate_codice(self, value):
        return (value or "").strip().upper()

    def validate_effect_script(self, value):
        from personaggi.carte_effect_script import validate_effect_script

        if value in (None, "", {}):
            return {}
        return validate_effect_script(value)

    def validate(self, attrs):
        from personaggi.carte_keyword_utils import keyword_ha_parametri, placeholder_nomi
        from personaggi.carte_effect_script import validate_effect_script_for_keyword

        nome = attrs.get("nome") or (self.instance.nome if self.instance else "")
        if keyword_ha_parametri(nome):
            required = placeholder_nomi(nome)
            testo = attrs.get("testo_regola")
            if testo is None and self.instance:
                testo = self.instance.testo_regola
            if testo:
                missing = [p for p in required if f"[{p}]" not in testo]
                if missing:
                    raise serializers.ValidationError({
                        "testo_regola": (
                            f"Per una keyword parametrizzata includi i placeholder "
                            f"{', '.join(f'[{p}]' for p in missing)} nel testo regola."
                        ),
                    })
        script = attrs.get("effect_script")
        if script is None and self.instance:
            script = self.instance.effect_script
        codice = attrs.get("codice") or (self.instance.codice if self.instance else "")
        if script:
            try:
                validate_effect_script_for_keyword(script, nome=nome, codice=codice)
            except Exception as exc:
                from django.core.exceptions import ValidationError as DjangoValidationError

                msg = exc.messages[0] if isinstance(exc, DjangoValidationError) else str(exc)
                raise serializers.ValidationError({"effect_script": msg}) from exc
        return attrs
