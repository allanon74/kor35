from rest_framework import serializers

from personaggi.negozio_mercante_models import (
    NegozioMercante,
    NegozioMercanteBundle,
    NegozioMercanteBundleRiga,
    NegozioMercanteVoce,
)


class NegozioMercanteVoceSerializer(serializers.ModelSerializer):
    entita_nome = serializers.SerializerMethodField()
    tipo_risultato = serializers.SerializerMethodField()

    class Meta:
        model = NegozioMercanteVoce
        fields = "__all__"

    def get_entita_nome(self, obj):
        from personaggi.negozio_mercante_service import _voce_consegna_istanza, _voce_entita

        ent = _voce_entita(obj)
        nome = getattr(ent, "nome", None) or obj.consumabile_nome or ""
        if obj.tipo_voce == "INF" and _voce_consegna_istanza(obj):
            tipo = getattr(ent, "tipo_risultato", "")
            suffisso = "aumento" if tipo == "AUM" else "istanza"
            return f"{nome} ({suffisso})" if nome else suffisso
        return nome

    def get_tipo_risultato(self, obj):
        inf = getattr(obj, "infusione", None)
        return getattr(inf, "tipo_risultato", None) if inf else None


class NegozioMercanteBundleRigaSerializer(serializers.ModelSerializer):
    voce_nome = serializers.SerializerMethodField()
    voce_tipo = serializers.CharField(source="voce.tipo_voce", read_only=True)

    class Meta:
        model = NegozioMercanteBundleRiga
        fields = (
            "id",
            "bundle",
            "voce",
            "quantita",
            "ordine",
            "voce_nome",
            "voce_tipo",
            "created_at",
            "updated_at",
            "sync_id",
        )
        read_only_fields = ("created_at", "updated_at", "sync_id")

    def get_voce_nome(self, obj):
        from personaggi.negozio_mercante_service import _nome_voce_catalogo

        return _nome_voce_catalogo(obj.voce) if obj.voce_id else ""


class NegozioMercanteBundleSerializer(serializers.ModelSerializer):
    righe = NegozioMercanteBundleRigaSerializer(many=True, read_only=True)
    componenti_count = serializers.SerializerMethodField()

    class Meta:
        model = NegozioMercanteBundle
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "sync_id")

    def get_componenti_count(self, obj):
        return obj.righe.count()

    def _replace_righe(self, bundle, rows):
        from personaggi.negozio_mercante_service import _voce_permette_quantita_multipla

        if rows is None:
            return
        if not isinstance(rows, list):
            raise serializers.ValidationError({"righe": "Atteso un elenco di componenti."})

        seen_voce = set()
        parsed = []
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                raise serializers.ValidationError({"righe": "Ogni riga deve essere un oggetto."})
            voce_id = row.get("voce") or row.get("voce_id")
            if not voce_id:
                raise serializers.ValidationError({"righe": "Ogni riga richiede 'voce'."})
            try:
                voce = NegozioMercanteVoce.objects.get(pk=voce_id, negozio_id=bundle.negozio_id)
            except NegozioMercanteVoce.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"righe": f"Voce {voce_id} non trovata in questo negozio."}
                ) from exc
            if voce.id in seen_voce:
                raise serializers.ValidationError(
                    {"righe": f"Voce duplicata nel bundle: {voce_id}."}
                )
            seen_voce.add(voce.id)
            quantita = int(row.get("quantita") or 1)
            if quantita < 1:
                raise serializers.ValidationError({"righe": "Quantità minima: 1."})
            if quantita > 1 and not _voce_permette_quantita_multipla(voce):
                raise serializers.ValidationError(
                    {
                        "righe": (
                            f"La voce «{voce}» non supporta quantità > 1 "
                            "(solo oggetti base, consumabili o istanze non-AUM)."
                        )
                    }
                )
            ordine = int(row["ordine"]) if row.get("ordine") is not None else idx
            parsed.append((voce, quantita, ordine))

        NegozioMercanteBundleRiga.objects.filter(bundle=bundle).delete()
        NegozioMercanteBundleRiga.objects.bulk_create(
            [
                NegozioMercanteBundleRiga(
                    bundle=bundle,
                    voce=voce,
                    quantita=quantita,
                    ordine=ordine,
                )
                for voce, quantita, ordine in parsed
            ]
        )

    def create(self, validated_data):
        bundle = NegozioMercanteBundle.objects.create(**validated_data)
        if "righe" in self.initial_data:
            self._replace_righe(bundle, self.initial_data.get("righe"))
        return bundle

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if "righe" in self.initial_data:
            self._replace_righe(instance, self.initial_data.get("righe"))
        return instance


class NegozioMercanteSerializer(serializers.ModelSerializer):
    voci = NegozioMercanteVoceSerializer(many=True, read_only=True)
    bundle = NegozioMercanteBundleSerializer(many=True, read_only=True)

    class Meta:
        model = NegozioMercante
        fields = "__all__"
        read_only_fields = (
            "campagna",
            "inventario",
            "qr_code",
            "created_at",
            "updated_at",
        )
