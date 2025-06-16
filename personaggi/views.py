# from django.shortcuts import render
# from rest_framework.authtoken.admin import User
# from rest_framework.decorators import action
# from django.shortcuts import render
# from rest_framework import viewsets, status, permissions
# from rest_framework.authentication import TokenAuthentication
# from rest_framework.response import Response

# from . import serializers
# from .serializers import AbilitaSerializer, AbilitaSmallSerializer, UserSerializer

# from personaggi.models import Abilita

# class UserViewSet(viewsets.ModelViewSet):
#     queryset = User.objects.all()
#     serializer_class = UserSerializer
#     authentication_classes = (TokenAuthentication,)
#     permission_classes = (permissions.IsAuthenticated, )


# class AbilitaViewSet(viewsets.ModelViewSet):
#     queryset = Abilita.objects.all()
#     serializer_class = AbilitaSerializer
#     authentication_classes = (TokenAuthentication,)

# class AbilitaSmallViewSet(viewsets.ModelViewSet):
#     queryset = Abilita.objects.all()
#     serializer_class = AbilitaSmallSerializer
#     authentication_classes = (TokenAuthentication,)

#     def retrieve(self, request, *args, **kwargs):
#         instance = self.get_object()
#         serializer = AbilitaSerializer(instance)
#         return Response(serializer.data)
    
#     @action(detail=True, methods=['POST', ])
#     def prova(self, request, pk=None):
#         instance = self.get_object()
#         abilita = Abilita.objects.get(pk=pk)
#         if 'azione' in request.data:
#             abilita.nome += " q"
#             abilita.save()
#             serializer = AbilitaSerializer(abilita, many=False)
#             response ={'message': f"Funziona!!! azione = {request.data['azione']}", 'result' : serializer.data}
#             return Response(response, status=status.HTTP_200_OK)

#         else:
#             response = {'message': 'Manca il parametro azione'}
#             return Response(response, status=status.HTTP_400_BAD_REQUEST)

# Create your views here.

from rest_framework import viewsets, status, permissions
from rest_framework.authtoken.admin import User
from rest_framework.authentication import TokenAuthentication
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken


from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({'detail': 'CSRF cookie set'})



class MyAuthToken(ObtainAuthToken):
    permisson_classes = (AllowAny,)

from .models import (
    Abilita, Tier, Spell, Mattone, Punteggio, Tabella,
    abilita_tier, abilita_requisito, abilita_sbloccata,
    abilita_punteggio, abilita_prerequisito,
    spell_mattone, spell_elemento
)
from .serializers import (
    AbilSerializer, AbilitaSerializer, AbilitaUpdateSerializer, TierSerializer, SpellSerializer, MattoneSerializer, PunteggioSerializer, TabellaSerializer,
    AbilitaTierSerializer, AbilitaRequisitoSerializer, AbilitaSbloccataSerializer,
    AbilitaPunteggioSerializer, AbilitaPrerequisitoSerializer,
    SpellMattoneSerializer, SpellElementoSerializer, UserSerializer
)

class AbilitaViewSet(viewsets.ModelViewSet):
    queryset = Abilita.objects.all()
    authentication_classes = (TokenAuthentication,)
    serializer_class = AbilitaSerializer

class AbilViewSet(viewsets.ModelViewSet):
    queryset = Abilita.objects.all()
    authentication_classes = (TokenAuthentication,)

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return AbilitaUpdateSerializer
        return AbilSerializer

class TierViewSet(viewsets.ModelViewSet):
    queryset = Tier.objects.all()
    serializer_class = TierSerializer
    authentication_classes = (TokenAuthentication,)

class SpellViewSet(viewsets.ModelViewSet):
    queryset = Spell.objects.all()
    serializer_class = SpellSerializer
    authentication_classes = (TokenAuthentication,)

class MattoneViewSet(viewsets.ModelViewSet):
    queryset = Mattone.objects.all()
    serializer_class = MattoneSerializer
    authentication_classes = (TokenAuthentication,)

class PunteggioViewSet(viewsets.ModelViewSet):
    queryset = Punteggio.objects.all()
    serializer_class = PunteggioSerializer
    authentication_classes = (TokenAuthentication,)

class TabellaViewSet(viewsets.ModelViewSet):
    queryset = Tabella.objects.all()
    serializer_class = TabellaSerializer
    authentication_classes = (TokenAuthentication,)

# THROUGH VIEWSETS

class AbilitaTierViewSet(viewsets.ModelViewSet):
    queryset = abilita_tier.objects.all()
    serializer_class = AbilitaTierSerializer
    authentication_classes = (TokenAuthentication,)

class AbilitaRequisitoViewSet(viewsets.ModelViewSet):
    queryset = abilita_requisito.objects.all()
    serializer_class = AbilitaRequisitoSerializer
    authentication_classes = (TokenAuthentication,)

class AbilitaSbloccataViewSet(viewsets.ModelViewSet):
    queryset = abilita_sbloccata.objects.all()
    serializer_class = AbilitaSbloccataSerializer
    authentication_classes = (TokenAuthentication,)

class AbilitaPunteggioViewSet(viewsets.ModelViewSet):
    queryset = abilita_punteggio.objects.all()
    serializer_class = AbilitaPunteggioSerializer
    authentication_classes = (TokenAuthentication,)

class AbilitaPrerequisitoViewSet(viewsets.ModelViewSet):
    queryset = abilita_prerequisito.objects.all()
    serializer_class = AbilitaPrerequisitoSerializer
    authentication_classes = (TokenAuthentication,)

class SpellMattoneViewSet(viewsets.ModelViewSet):
    queryset = spell_mattone.objects.all()
    serializer_class = SpellMattoneSerializer
    authentication_classes = (TokenAuthentication,)

class SpellElementoViewSet(viewsets.ModelViewSet):
    queryset = spell_elemento.objects.all()
    serializer_class = SpellElementoSerializer
    authentication_classes = (TokenAuthentication,)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated, )