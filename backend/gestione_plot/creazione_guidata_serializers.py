from rest_framework import serializers

from .creazione_guidata_publish import (
    get_sandbox_for_produzione,
    sandbox_ha_modifiche_non_pubblicate,
)
from .models import (
    CreazioneGuidataFlusso,
    CreazioneGuidataPasso,
    CreazioneGuidataScelta,
)


class CreazioneGuidataSceltaSerializer(serializers.ModelSerializer):
    passo_destinazione_slug = serializers.SlugField(
        source='passo_destinazione.slug',
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = CreazioneGuidataScelta
        fields = [
            'id',
            'sync_id',
            'passo',
            'etichetta',
            'descrizione',
            'ordine',
            'tipo_azione',
            'passo_destinazione',
            'passo_destinazione_slug',
            'payload',
            'updated_at',
        ]
        read_only_fields = ['sync_id', 'updated_at']


class CreazioneGuidataPassoSerializer(serializers.ModelSerializer):
    scelte = CreazioneGuidataSceltaSerializer(many=True, required=False)

    class Meta:
        model = CreazioneGuidataPasso
        fields = [
            'id',
            'sync_id',
            'flusso',
            'slug',
            'titolo',
            'contenuto',
            'immagine',
            'ordine',
            'opzioni_ui',
            'scelte',
            'updated_at',
        ]
        read_only_fields = ['sync_id', 'updated_at']

    def create(self, validated_data):
        scelte_data = validated_data.pop('scelte', [])
        passo = CreazioneGuidataPasso.objects.create(**validated_data)
        for scelta_data in scelte_data:
            CreazioneGuidataScelta.objects.create(passo=passo, **scelta_data)
        return passo

    def update(self, instance, validated_data):
        scelte_data = validated_data.pop('scelte', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if scelte_data is not None:
            instance.scelte.all().delete()
            for scelta_data in scelte_data:
                CreazioneGuidataScelta.objects.create(passo=instance, **scelta_data)
        return instance


class CreazioneGuidataPassoPlayerSerializer(serializers.ModelSerializer):
    """Passo per il giocatore: include scelte con payload per accumulo effetti."""

    scelte = CreazioneGuidataSceltaSerializer(many=True, read_only=True)
    immagine_url = serializers.SerializerMethodField()
    widget_fondo = serializers.JSONField(read_only=True, required=False, allow_null=True)

    class Meta:
        model = CreazioneGuidataPasso
        fields = [
            'id',
            'sync_id',
            'slug',
            'titolo',
            'contenuto',
            'immagine_url',
            'opzioni_ui',
            'scelte',
            'widget_fondo',
        ]

    def get_immagine_url(self, obj):
        if not obj.immagine:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.immagine.url)
        return obj.immagine.url


class CreazioneGuidataFlussoSerializer(serializers.ModelSerializer):
    passi = CreazioneGuidataPassoSerializer(many=True, required=False)
    passo_iniziale_slug = serializers.SlugField(
        source='passo_iniziale.slug',
        read_only=True,
        allow_null=True,
    )
    flusso_produzione_titolo = serializers.CharField(
        source='flusso_produzione.titolo',
        read_only=True,
        allow_null=True,
    )
    sandbox_test_id = serializers.SerializerMethodField()
    sandbox_modifiche_pending = serializers.SerializerMethodField()

    class Meta:
        model = CreazioneGuidataFlusso
        fields = [
            'id',
            'sync_id',
            'slug',
            'titolo',
            'attivo',
            'modalita_test',
            'flusso_produzione',
            'flusso_produzione_titolo',
            'sandbox_test_id',
            'sandbox_modifiche_pending',
            'campagna',
            'passo_iniziale',
            'passo_iniziale_slug',
            'passi',
            'updated_at',
        ]
        read_only_fields = [
            'sync_id',
            'updated_at',
            'sandbox_test_id',
            'sandbox_modifiche_pending',
            'flusso_produzione_titolo',
        ]

    def get_sandbox_test_id(self, obj):
        if obj.modalita_test:
            return None
        sandbox = get_sandbox_for_produzione(obj)
        return str(sandbox.id) if sandbox else None

    def get_sandbox_modifiche_pending(self, obj):
        if obj.modalita_test:
            return False
        return sandbox_ha_modifiche_non_pubblicate(obj)

    def create(self, validated_data):
        passi_data = validated_data.pop('passi', [])
        flusso = CreazioneGuidataFlusso.objects.create(**validated_data)
        for passo_data in passi_data:
            scelte_data = passo_data.pop('scelte', [])
            passo = CreazioneGuidataPasso.objects.create(flusso=flusso, **passo_data)
            for scelta_data in scelte_data:
                CreazioneGuidataScelta.objects.create(passo=passo, **scelta_data)
        return flusso

    def update(self, instance, validated_data):
        passi_data = validated_data.pop('passi', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if passi_data is not None:
            instance.passi.all().delete()
            for passo_data in passi_data:
                scelte_data = passo_data.pop('scelte', [])
                passo = CreazioneGuidataPasso.objects.create(flusso=instance, **passo_data)
                for scelta_data in scelte_data:
                    CreazioneGuidataScelta.objects.create(passo=passo, **scelta_data)
        return instance


class CreazioneGuidataFlussoListSerializer(serializers.ModelSerializer):
    passo_iniziale_slug = serializers.SlugField(
        source='passo_iniziale.slug',
        read_only=True,
        allow_null=True,
    )
    num_passi = serializers.IntegerField(source='passi.count', read_only=True)
    flusso_produzione_titolo = serializers.CharField(
        source='flusso_produzione.titolo',
        read_only=True,
        allow_null=True,
    )
    sandbox_modifiche_pending = serializers.SerializerMethodField()

    class Meta:
        model = CreazioneGuidataFlusso
        fields = [
            'id',
            'sync_id',
            'slug',
            'titolo',
            'attivo',
            'modalita_test',
            'flusso_produzione',
            'flusso_produzione_titolo',
            'sandbox_modifiche_pending',
            'campagna',
            'passo_iniziale',
            'passo_iniziale_slug',
            'num_passi',
            'updated_at',
        ]

    def get_sandbox_modifiche_pending(self, obj):
        if obj.modalita_test:
            return False
        return sandbox_ha_modifiche_non_pubblicate(obj)
