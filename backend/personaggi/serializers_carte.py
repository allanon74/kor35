"""
Serializers carte collezionabili.
"""
import json

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers

from personaggi.carte_collezionabili_models import (
    BustinaCarte,
    CARTE_ACCESSO_OFF,
    CARTE_ACCESSO_OPEN,
    CartaCollezionabile,
    CartaErrata,
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
            "sigla",
            "descrizione",
            "immagine",
            "immagine_url",
            "ordine",
            "attiva",
            "in_vendita",
            "vendita_dal",
            "vendita_al",
            "legale_duello",
            "disclaimer_disattiva",
            "gioco_definizione",
            "default_studio_template",
            "studio_set_spec",
            "mse_set_riferimento",
            "bustine_count",
            "carte_count",
        ]
        read_only_fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
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

    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = dict(data)
            for key in ("vendita_dal", "vendita_al"):
                if data.get(key) == "":
                    data[key] = None
        return super().to_internal_value(data)

    def validate(self, attrs):
        from personaggi.carte_set_codice import normalize_sigla, suggest_sigla_from_nome

        nome = attrs.get("nome") or (self.instance.nome if self.instance else "")
        slug = attrs.get("slug") or (self.instance.slug if self.instance else "")
        if attrs.get("vendita_dal") == "":
            attrs["vendita_dal"] = None
        if attrs.get("vendita_al") == "":
            attrs["vendita_al"] = None
        if not slug and nome:
            attrs["slug"] = slugify(nome)[:80]
        if not attrs.get("slug") and not (self.instance and self.instance.slug):
            raise serializers.ValidationError({"slug": "Slug obbligatorio."})

        # Sigla corta per codici carta (KBE-001). Auto da nome se vuota.
        if "sigla" in attrs:
            attrs["sigla"] = normalize_sigla(attrs.get("sigla") or "")
        sigla = attrs.get("sigla")
        if sigla is None and self.instance:
            sigla = self.instance.sigla
        if not (sigla or "").strip():
            attrs["sigla"] = suggest_sigla_from_nome(nome)
        elif "sigla" in attrs:
            attrs["sigla"] = normalize_sigla(sigla)

        campagna = self.instance.campagna if self.instance else self.context.get("campagna")
        slug_val = attrs.get("slug", slug)
        if campagna and slug_val:
            dup_qs = EspansioneCarte.objects.filter(campagna=campagna, slug=slug_val)
            if self.instance:
                dup_qs = dup_qs.exclude(pk=self.instance.pk)
            if dup_qs.exists():
                raise serializers.ValidationError(
                    {"slug": "Esiste già un set con questo codice in questa campagna."}
                )
        sigla_val = attrs.get("sigla") or (self.instance.sigla if self.instance else "")
        if campagna and sigla_val:
            dup_sigla = EspansioneCarte.objects.filter(campagna=campagna, sigla__iexact=sigla_val)
            if self.instance:
                dup_sigla = dup_sigla.exclude(pk=self.instance.pk)
            if dup_sigla.exists():
                raise serializers.ValidationError(
                    {"sigla": "Esiste già un set con questa sigla in questa campagna."}
                )
        vendita_dal = attrs.get("vendita_dal")
        vendita_al = attrs.get("vendita_al")
        if self.instance:
            if vendita_dal is None and "vendita_dal" not in attrs:
                vendita_dal = self.instance.vendita_dal
            if vendita_al is None and "vendita_al" not in attrs:
                vendita_al = self.instance.vendita_al
        if vendita_dal and vendita_al and vendita_dal > vendita_al:
            raise serializers.ValidationError(
                {"vendita_al": "La fine vendita deve essere successiva all'inizio vendita."}
            )
        return attrs

    def validate_studio_set_spec(self, value):
        parsed = _parse_json_field(value, "studio_set_spec")
        return parsed if parsed is not None else {}

    def validate_default_studio_template(self, value):
        if value is None:
            return None
        campagna = self.instance.campagna if self.instance else self.context.get("campagna")
        if campagna and value.campagna_id != campagna.id:
            raise serializers.ValidationError("Template non appartenente alla campagna attiva.")
        return value

    @transaction.atomic
    def update(self, instance, validated_data):
        from personaggi.carte_set_codice import normalize_sigla, renumber_carte_in_espansione

        old_sigla = normalize_sigla(instance.sigla or "")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        new_sigla = normalize_sigla(instance.sigla or "")
        if old_sigla != new_sigla and instance.carte.exists():
            renumber_carte_in_espansione(instance.campagna, instance)
        return instance


def _default_studio_template_for_espansione(espansione):
    """Default stylesheet: set → gioco (is_default_for_new_cards)."""
    if not espansione:
        return None
    if espansione.default_studio_template_id:
        return espansione.default_studio_template
    if espansione.gioco_definizione_id:
        return (
            espansione.gioco_definizione.studio_templates.filter(
                is_default_for_new_cards=True,
                attivo=True,
            )
            .order_by("ordine", "nome")
            .first()
        )
    return None


class CartaCollezionabileSerializer(serializers.ModelSerializer):
    immagine_url = serializers.SerializerMethodField()
    espansione_nome = serializers.CharField(source="espansione.nome", read_only=True, allow_null=True)
    # Nome può arrivare come MSE «name»; hydrate in validate().
    nome = serializers.CharField(required=False, allow_blank=True, max_length=120)
    # Codice auto-assegnato in create se vuoto + espansione presente.
    codice = serializers.CharField(required=False, allow_blank=True, max_length=40)
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
            "legale_duello",
            "bandita",
            "ban_reason",
            "layout_versione",
            "studio_template",
            "studio_carta_spec",
            "arena_playable_spec",
            "mse_campi",
            "statistiche_reliquiario",
            "duplicabile",
            "immagine",
            "immagine_url",
            "attiva",
            "ordine_set",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "campagna", "immagine_url", "espansione_nome", "tag_codici"]

    def get_tag_codici(self, obj):
        return [t.codice for t in obj.tags.filter(attiva=True).order_by("nome")]

    def get_immagine_url(self, obj):
        if obj.immagine:
            # Path relativo same-origin per Card Studio / nginx.
            try:
                return obj.immagine.url
            except ValueError:
                return None
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

    def validate_studio_carta_spec(self, value):
        parsed = _parse_json_field(value, "studio_carta_spec")
        return parsed if parsed is not None else {}

    def validate_arena_playable_spec(self, value):
        parsed = _parse_json_field(value, "arena_playable_spec")
        return parsed if parsed is not None else {}

    def validate_mse_campi(self, value):
        parsed = _parse_json_field(value, "mse_campi")
        return parsed if parsed is not None else {}

    def to_internal_value(self, data):
        """Normalizza type/rarity Magic prima della ChoiceField validation DRF."""
        from personaggi.carte_collezionabili_models import (
            CARTA_ENERGIA_CHOICES,
            CARTA_ENERGIA_MARZIALE,
            CARTA_RARITA_CHOICES,
            CARTA_RARITA_COMUNE,
            CARTA_TIPO_CHOICES,
            CARTA_TIPO_PERSONAGGIO,
        )

        mutable = data.copy() if hasattr(data, "copy") else dict(data)
        tipo_ok = {c for c, _ in CARTA_TIPO_CHOICES}
        energia_ok = {c for c, _ in CARTA_ENERGIA_CHOICES}
        rarita_ok = {c for c, _ in CARTA_RARITA_CHOICES}

        tipo = mutable.get("tipo")
        if tipo is not None and tipo != "" and tipo not in tipo_ok:
            mutable["tipo"] = (
                self.instance.tipo
                if self.instance and self.instance.tipo in tipo_ok
                else CARTA_TIPO_PERSONAGGIO
            )
        energia = mutable.get("energia")
        if energia is not None and energia != "" and energia not in energia_ok:
            mutable["energia"] = (
                self.instance.energia
                if self.instance and self.instance.energia in energia_ok
                else CARTA_ENERGIA_MARZIALE
            )
        rarita = mutable.get("rarita")
        if rarita is not None and rarita != "" and rarita not in rarita_ok:
            mutable["rarita"] = (
                self.instance.rarita
                if self.instance and self.instance.rarita in rarita_ok
                else CARTA_RARITA_COMUNE
            )
        return super().to_internal_value(mutable)

    def validate_tipo(self, value):
        from personaggi.carte_collezionabili_models import CARTA_TIPO_CHOICES, CARTA_TIPO_PERSONAGGIO

        ok = {c for c, _ in CARTA_TIPO_CHOICES}
        if value in ok:
            return value
        # Magic freeform (Creature — …): resta in mse_campi, catalogo tiene default.
        if self.instance and self.instance.tipo in ok:
            return self.instance.tipo
        return CARTA_TIPO_PERSONAGGIO

    def validate_energia(self, value):
        from personaggi.carte_collezionabili_models import CARTA_ENERGIA_CHOICES, CARTA_ENERGIA_MARZIALE

        ok = {c for c, _ in CARTA_ENERGIA_CHOICES}
        if value in ok:
            return value
        if self.instance and self.instance.energia in ok:
            return self.instance.energia
        return CARTA_ENERGIA_MARZIALE

    def validate_rarita(self, value):
        from personaggi.carte_collezionabili_models import CARTA_RARITA_CHOICES, CARTA_RARITA_COMUNE

        ok = {c for c, _ in CARTA_RARITA_CHOICES}
        if value in ok:
            return value
        if self.instance and self.instance.rarita in ok:
            return self.instance.rarita
        return CARTA_RARITA_COMUNE

    def _hydrate_nome_from_mse_campi(self, attrs):
        """Name (MSE) → nome catalogo. Evita 400 «nome omesso» dopo edit Card Studio."""
        current = attrs.get("nome")
        if current is None and self.instance is not None:
            current = self.instance.nome
        if (current or "").strip():
            attrs["nome"] = str(current).strip()[:120]
            return attrs

        mse = attrs.get("mse_campi")
        if mse is None and self.instance is not None:
            mse = getattr(self.instance, "mse_campi", None)
        mse = mse or {}
        for key in ("name", "nome", "full name", "full_name", "title", "card_name"):
            raw = mse.get(key)
            if raw is None and "_" in key:
                raw = mse.get(key.replace("_", " "))
            if raw is not None and str(raw).strip():
                attrs["nome"] = str(raw).strip()[:120]
                return attrs
        raise serializers.ValidationError(
            {
                "nome": (
                    "Nome obbligatorio: compila il campo MSE «name» (Name). "
                    "Viene salvato come nome catalogo."
                )
            }
        )

    def validate(self, attrs):
        attrs = self._hydrate_nome_from_mse_campi(attrs)

        bandita = attrs.get("bandita")
        ban_reason = attrs.get("ban_reason")
        if self.instance:
            if bandita is None and "bandita" not in attrs:
                bandita = self.instance.bandita
            if ban_reason is None and "ban_reason" not in attrs:
                ban_reason = self.instance.ban_reason
        if bandita and not (ban_reason or "").strip():
            raise serializers.ValidationError(
                {"ban_reason": "Inserisci una motivazione ban quando la carta è bandita."}
            )

        espansione = attrs.get("espansione", self.instance.espansione if self.instance else None)
        studio_template = attrs.get("studio_template", self.instance.studio_template if self.instance else None)
        if studio_template and espansione and espansione.campagna_id != studio_template.campagna_id:
            raise serializers.ValidationError(
                {"studio_template": "Template non compatibile con la campagna dell'espansione."}
            )

        if self.instance:
            cfg = ConfigurazioneCarteCollezionabili.objects.filter(
                campagna=self.instance.campagna
            ).first()
            accesso = cfg.accesso_modo if cfg else CARTE_ACCESSO_OFF
            if accesso == CARTE_ACCESSO_OPEN:
                locked_fields = {
                    "tipo",
                    "energia",
                    "rarita",
                    "costo_gioco",
                    "attacco",
                    "salute",
                    "iniziativa",
                    "testo_gioco",
                    "effect_scripts",
                    "tag_tematici",
                    "tags",
                    "legale_duello",
                    "bandita",
                    "ban_reason",
                }
                touched = []
                for field in locked_fields:
                    if field not in attrs:
                        continue
                    if field == "tags":
                        new_ids = {
                            getattr(t, "pk", t)
                            for t in (attrs.get("tags") or [])
                        }
                        old_ids = set(self.instance.tags.values_list("pk", flat=True))
                        if new_ids != old_ids:
                            touched.append("tag_ids")
                        continue
                    if attrs[field] != getattr(self.instance, field):
                        touched.append(field)
                if touched:
                    raise serializers.ValidationError(
                        {
                            "detail": (
                                "Campagna in OPEN: campi gameplay bloccati. "
                                f"Campi non modificabili: {', '.join(sorted(set(touched)))}."
                            )
                        }
                    )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from personaggi.carte_set_codice import (
            renumber_carte_in_espansione,
            suggest_carta_codice_for_espansione,
        )

        stats = validated_data.pop("reliquiario_statistiche", [])
        tags = validated_data.pop("tags", None)
        espansione = validated_data.get("espansione")
        # Codice sempre automatico alla creazione in un set: placeholder poi rinumera.
        if espansione:
            campagna = validated_data.get("campagna") or espansione.campagna
            ordine, codice = suggest_carta_codice_for_espansione(campagna, espansione)
            validated_data["codice"] = codice
            if not validated_data.get("ordine_set"):
                validated_data["ordine_set"] = ordine
        elif not (validated_data.get("codice") or "").strip():
            raise serializers.ValidationError(
                {"codice": "Codice obbligatorio se la carta non ha un'espansione."}
            )
        if not validated_data.get("studio_template"):
            default_template = _default_studio_template_for_espansione(
                validated_data.get("espansione")
            )
            if default_template:
                validated_data["studio_template"] = default_template
        carta = CartaCollezionabile.objects.create(**validated_data)
        if tags is not None:
            carta.tags.set(tags)
        _save_condizione_stat_rows(CartaReliquiarioStatistica, "carta", carta, stats)
        if carta.espansione_id:
            renumber_carte_in_espansione(carta.campagna, carta.espansione)
            carta.refresh_from_db()
        return carta

    @transaction.atomic
    def update(self, instance, validated_data):
        from personaggi.carte_set_codice import renumber_carte_in_espansione

        stats = validated_data.pop("reliquiario_statistiche", None)
        tags = validated_data.pop("tags", None)
        old_esp = instance.espansione
        old_nome = instance.nome
        old_energia = instance.energia
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # Legacy: carte senza override ereditano il default del set al salvataggio.
        if not instance.studio_template_id:
            default_template = _default_studio_template_for_espansione(instance.espansione)
            if default_template:
                instance.studio_template = default_template
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        if stats is not None:
            _save_condizione_stat_rows(CartaReliquiarioStatistica, "carta", instance, stats)

        # Rinumera se cambia set / colore / nome (ordine Magic).
        new_esp = instance.espansione
        old_esp_id = getattr(old_esp, "pk", None)
        new_esp_id = getattr(new_esp, "pk", None)
        order_fields_changed = (
            old_esp_id != new_esp_id
            or old_nome != instance.nome
            or old_energia != instance.energia
        )
        if order_fields_changed:
            if old_esp_id and old_esp_id != new_esp_id:
                renumber_carte_in_espansione(instance.campagna, old_esp)
            if new_esp:
                renumber_carte_in_espansione(instance.campagna, new_esp)
                instance.refresh_from_db()
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
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "campagna"]

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


class CartaErrataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartaErrata
        fields = [
            "id",
            "sync_id",
            "created_at",
            "updated_at",
            "campagna",
            "carta",
            "effective_from",
            "attiva",
            "versione",
            "pubblicata",
            "pubblicata_at",
            "pubblicata_nota",
            "titolo",
            "descrizione",
            "testo_gioco_override",
            "costo_gioco_override",
            "attacco_override",
            "salute_override",
            "iniziativa_override",
            "effect_scripts_override",
        ]
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "campagna"]

    def validate(self, attrs):
        if not attrs.get("effective_from") and not (self.instance and self.instance.effective_from):
            raise serializers.ValidationError({"effective_from": "Data efficacia obbligatoria."})
        pubblicata = attrs.get("pubblicata")
        if pubblicata is None and self.instance:
            pubblicata = self.instance.pubblicata
        if pubblicata and not attrs.get("pubblicata_at") and not (self.instance and self.instance.pubblicata_at):
            attrs["pubblicata_at"] = timezone.now()
        return attrs

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
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "campagna", "qr_code_id", "espansione_nome"]


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
        read_only_fields = ["id", "sync_id", "created_at", "updated_at", "campagna"]

    def validate(self, attrs):
        modo = attrs.get("accesso_modo")
        abilitata = attrs.get("abilitata")
        if modo is None and abilitata is not None and "accesso_modo" not in attrs:
            attrs["accesso_modo"] = CARTE_ACCESSO_OPEN if abilitata else CARTE_ACCESSO_OFF
        elif modo is not None:
            attrs["abilitata"] = modo == CARTE_ACCESSO_OPEN
        return attrs

    def _sync_moduli_campagna(self, instance):
        """Allinea Campagna.moduli_accesso['carte'] con accesso_modo."""
        from personaggi.campagna_moduli import MODULO_CARTE, MODULO_ACCESSO_VALIDI

        campagna = instance.campagna
        if not campagna:
            return
        modo = getattr(instance, "accesso_modo", None) or CARTE_ACCESSO_OFF
        if modo not in MODULO_ACCESSO_VALIDI:
            return
        raw = dict(campagna.moduli_accesso or {})
        if raw.get(MODULO_CARTE) == modo:
            return
        raw[MODULO_CARTE] = modo
        campagna.moduli_accesso = raw
        campagna.save(update_fields=["moduli_accesso", "updated_at"])

    def create(self, validated_data):
        instance = super().create(validated_data)
        self._sync_moduli_campagna(instance)
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self._sync_moduli_campagna(instance)
        return instance


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
            "mse_match_pattern",
            "mse_reminder_template",
            "mse_export_mode",
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
