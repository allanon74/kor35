"""
Serializers carte collezionabili.
"""
from django.utils.text import slugify
from rest_framework import serializers

from personaggi.carte_collezionabili_models import (
    BustinaCarte,
    CARTE_ACCESSO_OFF,
    CARTE_ACCESSO_OPEN,
    CartaCollezionabile,
    ConfigurazioneCarteCollezionabili,
    EspansioneCarte,
    KeywordCarta,
)


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
            "set_collezione",
            "campagna_origine",
            "legame_id",
            "tag_tematici",
            "bonus_equip",
            "duplicabile",
            "immagine",
            "immagine_url",
            "attiva",
            "ordine_set",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "immagine_url", "espansione_nome"]

    def get_immagine_url(self, obj):
        if obj.immagine:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.immagine.url)
            return obj.immagine.url
        return None


class BustinaCarteSerializer(serializers.ModelSerializer):
    espansione_nome = serializers.CharField(source="espansione.nome", read_only=True, allow_null=True)

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
