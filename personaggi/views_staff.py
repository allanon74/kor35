from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from .models import QrCode, PropostaTecnica, Tessitura, Infusione, Cerimoniale, Oggetto, OggettoBase, ClasseOggetto
from gestione_plot.permissions import IsStaffOrMaster

from .serializers import (
    InfusioneFullEditorSerializer,
    OggettoBaseFullEditorSerializer,
    OggettoFullEditorSerializer, 
    TessituraFullEditorSerializer, 
    CerimonialeFullEditorSerializer,
    OggettoSerializer,
    OggettoBaseSerializer,
    ClasseOggettoSerializer,
)

class QrInspectorView(APIView):
    """
    Strumento STAFF: Legge un QR e dice cos'è senza attivare nulla.
    """
    permission_classes = [IsStaffOrMaster]

    def get(self, request, qr_id):
        try:
            qr = QrCode.objects.get(id=qr_id)
            data = {
                'id': qr.id,
                'tipo_contenuto': qr.vista.__class__.__name__ if qr.vista else "Vuoto",
                'nome_contenuto': str(qr.vista) if qr.vista else "Nessuno",
                'testo_raw': qr.testo
            }
            return Response(data)
        except QrCode.DoesNotExist:
            return Response({'error': 'Non trovato'}, status=404)

class ApprovaPropostaView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, proposta_id):
        try:
            proposta = PropostaTecnica.objects.get(pk=proposta_id)
            if proposta.stato == 'APPROVATA':
                return Response({'error': 'Proposta già approvata'}, status=400)

            nuova_istanza = None
            
            # Logica differenziata per tipo
            if proposta.tipo == 'TES':
                nuova_istanza = Tessitura.objects.create(
                    nome=proposta.nome, testo=proposta.descrizione,
                    aura_richiesta=proposta.aura, elemento_principale=proposta.aura_infusione,
                    proposta_creazione=proposta
                )
            elif proposta.tipo == 'INF':
                nuova_istanza = Infusione.objects.create(
                    nome=proposta.nome, testo=proposta.descrizione,
                    aura_richiesta=proposta.aura, aura_infusione=proposta.aura_infusione,
                    proposta_creazione=proposta, 
                    tipo_risultato=proposta.tipo_risultato_atteso or 'POT'
                )
            elif proposta.tipo == 'CER':
                nuova_istanza = Cerimoniale.objects.create(
                    nome=proposta.nome, prerequisiti=proposta.prerequisiti,
                    svolgimento=proposta.svolgimento, effetto=proposta.effetto,
                    aura_richiesta=proposta.aura, liv=proposta.livello_proposto,
                    proposta_creazione=proposta
                )

            if nuova_istanza:
                # Copia automatica dei componenti (mattoni/caratteristiche)
                for comp in proposta.componenti.all():
                    nuova_istanza.componenti.create(
                        caratteristica=comp.caratteristica, 
                        valore=comp.valore
                    )
                
                proposta.stato = 'APPROVATA'
                proposta.save()
                return Response({
                    'status': 'approvata', 
                    'tipo': proposta.tipo, 
                    'id_generato': nuova_istanza.id
                })

        except PropostaTecnica.DoesNotExist:
            return Response({'error': 'Proposta non trovata'}, status=404)
        
class InfusioneMasterViewSet(viewsets.ModelViewSet):
    """
    CRUD completo per le Infusioni, usato dai Master.
    Gestisce salvataggi atomici di componenti e statistiche.
    """
    queryset = Infusione.objects.all()
    serializer_class = InfusioneFullEditorSerializer
    permission_classes = [IsAdminUser]

class TessituraMasterViewSet(viewsets.ModelViewSet):
    """
    CRUD completo per le Tessiture, usato dai Master.
    """
    queryset = Tessitura.objects.all()
    serializer_class = TessituraFullEditorSerializer
    permission_classes = [IsAdminUser]

class CerimonialeMasterViewSet(viewsets.ModelViewSet):
    """
    CRUD completo per i Cerimoniali, usato dai Master.
    """
    queryset = Cerimoniale.objects.all()
    serializer_class = CerimonialeFullEditorSerializer
    permission_classes = [IsAdminUser]
    
class OggettoStaffViewSet(viewsets.ModelViewSet):
    queryset = Oggetto.objects.all().select_related('aura', 'classe_oggetto')
    serializer_class = OggettoFullEditorSerializer
    permission_classes = [IsStaffOrMaster]

class OggettoBaseStaffViewSet(viewsets.ModelViewSet):
    queryset = OggettoBase.objects.all().select_related('classe_oggetto')
    serializer_class = OggettoBaseFullEditorSerializer
    permission_classes = [IsStaffOrMaster]

class ClasseOggettoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClasseOggetto.objects.all()
    serializer_class = ClasseOggettoSerializer
    permission_classes = [IsStaffOrMaster]