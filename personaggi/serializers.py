from rest_framework import serializers
from rest_framework.authtoken.models import Token


from .models import (
    Abilita, Tier, Spell, Mattone, Punteggio, Tabella,
    abilita_tier, abilita_requisito, abilita_sbloccata,
    abilita_punteggio, abilita_prerequisito,
    spell_mattone, spell_elemento
)

from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name' )
        extra_kwargs = {'password': {'write_only': True, 'required' : True, }}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.is_active = False
        # token = Token.objects.create(user=user)
        return user

class TierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tier
        fields = '__all__'


class TabellaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tabella
        fields = '__all__'


class PunteggioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Punteggio
        fields = '__all__'

class AbilSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSerializer(many=False)
    tiers = TierSerializer(many=True)
    requisiti = PunteggioSerializer(many=True, required=False)
    punteggio_acquisito = PunteggioSerializer(many=True, required=False)
    class Meta:
        model = Abilita
        fields = '__all__'

class AbilitaSerializer(serializers.ModelSerializer):
    # caratteristica = PunteggioSerializer(many=False)
    # tiers = TierSerializer(many=True)
    # requisiti = PunteggioSerializer(many=True, required=False)
    # punteggio_acquisito = PunteggioSerializer(many=True, required=False)
    class Meta:
        model = Abilita
        fields = '__all__'

class AbilitaSmallSerializer(serializers.ModelSerializer):
    caratteristica = PunteggioSerializer(many=False)
    class Meta:
        model = Abilita
        fields = ("id", "nome", "caratteristica", "descrizione")



class AbilitaTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_tier
        fields = ['id', 'abilita', 'tabella', 'costo', 'ordine']

class AbilitaRequisitoSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_requisito
        fields = ['id', 'abilita', 'requisito', 'valore']

class AbilitaSbloccataSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_sbloccata
        fields = ['id', 'abilita', 'sbloccata']

class AbilitaPunteggioSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_punteggio
        fields = ['id', 'abilita', 'punteggio', 'valore']

class AbilitaPrerequisitoSerializer(serializers.ModelSerializer):
    class Meta:
        model = abilita_prerequisito
        fields = ['id', 'abilita', 'prerequisito']

class SpellMattoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = spell_mattone
        fields = ['id', 'spell', 'mattone', 'valore']

class SpellElementoSerializer(serializers.ModelSerializer):
    class Meta:
        model = spell_elemento
        fields = ['id', 'spell', 'elemento']



class MattoneSerializer(serializers.ModelSerializer):
    elemento = PunteggioSerializer()
    aura = PunteggioSerializer()

    class Meta:
        model = Mattone
        fields = '__all__'

class SpellSerializer(serializers.ModelSerializer):
    mattoni = MattoneSerializer(many=True, read_only=True)

    class Meta:
        model = Spell
        fields = '__all__'



class AbilitaUpdateSerializer(serializers.ModelSerializer):
    requisiti = AbilitaRequisitoSerializer(many=True, required=False)
    punteggio_acquisito = AbilitaPunteggioSerializer(many=True, required=False)

    class Meta:
        model = Abilita
        fields = ['id', 'nome', 'descrizione', 'caratteristica', 'requisiti', 'punteggio_acquisito']

    def update(self, instance, validated_data):
        requisiti_data = validated_data.pop('requisiti', [])
        punteggi_data = validated_data.pop('punteggio_acquisito', [])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if requisiti_data:
            instance.requisiti.clear()
            for item in requisiti_data:
                abilita_requisito.objects.create(abilita=instance, **item)

        if punteggi_data:
            instance.punteggio_acquisito.clear()
            for item in punteggi_data:
                abilita_punteggio.objects.create(abilita=instance, **item)

        return instance

