from rest_framework import serializers
from .models import (
    Abilita, Tier, Punteggio, Tabella, Spell, Mattone,
    abilita_tier, abilita_requisito, abilita_sbloccata, abilita_punteggio, abilita_prerequisito,
    spell_mattone, spell_elemento
)

class AbilitaTierSerializer(serializers.ModelSerializer):
    tabella_nome = serializers.CharField(source='tabella.nome', read_only=True)

    class Meta:
        model = abilita_tier
        fields = ['id', 'tabella', 'tabella_nome', 'costo', 'ordine']

    def create(self, validated_data):
        try:
            return abilita_tier.objects.create(**validated_data)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating abilita_tier: {str(e)}")

    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Error updating abilita_tier: {str(e)}")

class AbilitaRequisitoSerializer(serializers.ModelSerializer):
    requisito_nome = serializers.CharField(source='requisito.nome', read_only=True)

    class Meta:
        model = abilita_requisito
        fields = ['id', 'requisito', 'requisito_nome', 'valore']

    def create(self, validated_data):
        try:
            return abilita_requisito.objects.create(**validated_data)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating abilita_requisito: {str(e)}")

    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Error updating abilita_requisito: {str(e)}")

class AbilitaSbloccataSerializer(serializers.ModelSerializer):
    sbloccata_nome = serializers.CharField(source='sbloccata.nome', read_only=True)

    class Meta:
        model = abilita_sbloccata
        fields = ['id', 'sbloccata', 'sbloccata_nome']

    def create(self, validated_data):
        try:
            return abilita_sbloccata.objects.create(**validated_data)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating abilita_sbloccata: {str(e)}")

    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Error updating abilita_sbloccata: {str(e)}")

class AbilitaPunteggioSerializer(serializers.ModelSerializer):
    punteggio_nome = serializers.CharField(source='punteggio.nome', read_only=True)

    class Meta:
        model = abilita_punteggio
        fields = ['id', 'punteggio', 'punteggio_nome', 'valore']

    def create(self, validated_data):
        try:
            return abilita_punteggio.objects.create(**validated_data)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating abilita_punteggio: {str(e)}")

    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Error updating abilita_punteggio: {str(e)}")

class AbilitaPrerequisitoSerializer(serializers.ModelSerializer):
    prerequisito_nome = serializers.CharField(source='prerequisito.nome', read_only=True)

    class Meta:
        model = abilita_prerequisito
        fields = ['id', 'prerequisito', 'prerequisito_nome', 'valore']

    def create(self, validated_data):
        try:
            return abilita_prerequisito.objects.create(**validated_data)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating abilita_prerequisito: {str(e)}")

    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Error updating abilita_prerequisito: {str(e)}")

class AbilitaSerializer(serializers.ModelSerializer):
    tiers = AbilitaTierSerializer(source='abilita_tier_set', many=True)
    requisiti = AbilitaRequisitoSerializer(source='abilita_requisito_set', many=True)
    tabelle_sbloccate = AbilitaSbloccataSerializer(source='abilita_sbloccata_set', many=True)
    punteggio_acquisito = AbilitaPunteggioSerializer(source='abilita_punteggio_set', many=True)
    prerequisiti = AbilitaPrerequisitoSerializer(source='abilita_prerequisito_set', many=True)

    class Meta:
        model = Abilita
        fields = [
            'id', 'nome', 'descrizione', 'caratteristica',
            'tiers', 'requisiti', 'tabelle_sbloccate', 'punteggio_acquisito', 'prerequisiti'
        ]

    def create(self, validated_data):
        try:
            tiers_data = validated_data.pop('abilita_tier_set', [])
            requisiti_data = validated_data.pop('abilita_requisito_set', [])
            tabelle_sbloccate_data = validated_data.pop('abilita_sbloccata_set', [])
            punteggio_acquisito_data = validated_data.pop('abilita_punteggio_set', [])
            prerequisiti_data = validated_data.pop('abilita_prerequisito_set', [])
            abilita = Abilita.objects.create(**validated_data)
            for tier in tiers_data:
                abilita_tier.objects.create(abilita=abilita, **tier)
            for requisito in requisiti_data:
                abilita_requisito.objects.create(abilita=abilita, **requisito)
            for sbloccata in tabelle_sbloccate_data:
                abilita_sbloccata.objects.create(abilita=abilita, **sbloccata)
            for punteggio in punteggio_acquisito_data:
                abilita_punteggio.objects.create(abilita=abilita, **punteggio)
            for prerequisito in prerequisiti_data:
                abilita_prerequisito.objects.create(abilita=abilita, **prerequisito)
            return abilita
        except Exception as e:
            raise serializers.ValidationError(f"Error creating Abilita: {str(e)}")

    def update(self, instance, validated_data):
        try:
            tiers_data = validated_data.pop('abilita_tier_set', [])
            requisiti_data = validated_data.pop('abilita_requisito_set', [])
            tabelle_sbloccate_data = validated_data.pop('abilita_sbloccata_set', [])
            punteggio_acquisito_data = validated_data.pop('abilita_punteggio_set', [])
            prerequisiti_data = validated_data.pop('abilita_prerequisito_set', [])
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            instance.abilita_tier_set.all().delete()
            instance.abilita_requisito_set.all().delete()
            instance.abilita_sbloccata_set.all().delete()
            instance.abilita_punteggio_set.all().delete()
            instance.abilita_prerequisito_set.all().delete()
            for tier in tiers_data:
                abilita_tier.objects.create(abilita=instance, **tier)
            for requisito in requisiti_data:
                abilita_requisito.objects.create(abilita=instance, **requisito)
            for sbloccata in tabelle_sbloccate_data:
                abilita_sbloccata.objects.create(abilita=instance, **sbloccata)
            for punteggio in punteggio_acquisito_data:
                abilita_punteggio.objects.create(abilita=instance, **punteggio)
            for prerequisito in prerequisiti_data:
                abilita_prerequisito.objects.create(abilita=instance, **prerequisito)
            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Error updating Abilita: {str(e)}")

class MattoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mattone
        fields = ['id', 'nome', 'descrizione', 'elemento', 'aura']

    def create(self, validated_data):
        try:
            return Mattone.objects.create(**validated_data)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating Mattone: {str(e)}")

    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Error updating Mattone: {str(e)}")

class SpellMattoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = spell_mattone
        fields = ['id', 'mattone', 'valore']

    def create(self, validated_data):
        try:
            return spell_mattone.objects.create(**validated_data)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating spell_mattone: {str(e)}")

    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Error updating spell_mattone: {str(e)}")

class SpellElementoSerializer(serializers.ModelSerializer):
    class Meta:
        model = spell_elemento
        fields = ['id', 'elemento']

    def create(self, validated_data):
        try:
            return spell_elemento.objects.create(**validated_data)
        except Exception as e:
            raise serializers.ValidationError(f"Error creating spell_elemento: {str(e)}")

    def update(self, instance, validated_data):
        try:
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Error updating spell_elemento: {str(e)}")

class SpellSerializer(serializers.ModelSerializer):
    mattoni = SpellMattoneSerializer(source='spell_mattone_set', many=True)
    elementi = SpellElementoSerializer(source='spell_elemento_set', many=True)

    class Meta:
        model = Spell
        fields = ['id', 'nome', 'descrizione', 'mattoni', 'elementi']

    def create(self, validated_data):
        try:
            mattoni_data = validated_data.pop('spell_mattone_set', [])
            elementi_data = validated_data.pop('spell_elemento_set', [])
            spell = Spell.objects.create(**validated_data)
            for m in mattoni_data:
                spell_mattone.objects.create(spell=spell, **m)
            for e in elementi_data:
                spell_elemento.objects.create(spell=spell, **e)
            return spell
        except Exception as e:
            raise serializers.ValidationError(f"Error creating Spell: {str(e)}")

    def update(self, instance, validated_data):
        try:
            mattoni_data = validated_data.pop('spell_mattone_set', [])
            elementi_data = validated_data.pop('spell_elemento_set', [])
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            instance.spell_mattone_set.all().delete()
            instance.spell_elemento_set.all().delete()
            for m in mattoni_data:
                spell_mattone.objects.create(spell=instance, **m)
            for e in elementi_data:
                spell_elemento.objects.create(spell=instance, **e)
            return instance
        except Exception as e:
            raise serializers.ValidationError(f"Error updating Spell: {str(e)}")
