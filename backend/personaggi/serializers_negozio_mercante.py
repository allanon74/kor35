from rest_framework import serializers

from personaggi.negozio_mercante_models import NegozioMercante, NegozioMercanteVoce


class NegozioMercanteVoceSerializer(serializers.ModelSerializer):
    entita_nome = serializers.SerializerMethodField()

    class Meta:
        model = NegozioMercanteVoce
        fields = "__all__"

    def get_entita_nome(self, obj):
        from personaggi.negozio_mercante_service import _voce_entita

        ent = _voce_entita(obj)
        if ent:
            return getattr(ent, "nome", str(ent))
        return obj.consumabile_nome or ""


class NegozioMercanteSerializer(serializers.ModelSerializer):
    voci = NegozioMercanteVoceSerializer(many=True, read_only=True)
    class Meta:
        model = NegozioMercante
        fields = "__all__"
