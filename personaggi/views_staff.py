from rest_framework import viewsets, permissions, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from gestione_plot.permissions import IsStaffOrMaster
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from .models import (
    PropostaTecnica, Personaggio, Messaggio, Punteggio,
    Infusione, Tessitura, Cerimoniale,
    QrCode, Oggetto, OggettoBase, ClasseOggetto,
    STATO_PROPOSTA_BOZZA, STATO_PROPOSTA_APPROVATA, STATO_PROPOSTA_IN_VALUTAZIONE,
    TIPO_PROPOSTA_INFUSIONE, TIPO_PROPOSTA_TESSITURA, TIPO_PROPOSTA_CERIMONIALE
)

from .serializers import (
    InfusioneFullEditorSerializer,
    OggettoBaseFullEditorSerializer,
    OggettoFullEditorSerializer, 
    TessituraFullEditorSerializer, 
    CerimonialeFullEditorSerializer,
    OggettoSerializer,
    OggettoBaseSerializer,
    ClasseOggettoSerializer,
    InfusioneSerializer,
    TessituraSerializer,
    CerimonialeSerializer,
    PropostaTecnicaSerializer,
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

# class ApprovaPropostaView(APIView):
#     permission_classes = [IsAdminUser]

#     def post(self, request, proposta_id):
#         try:
#             proposta = PropostaTecnica.objects.get(pk=proposta_id)
#             if proposta.stato == 'APPROVATA':
#                 return Response({'error': 'Proposta già approvata'}, status=400)

#             nuova_istanza = None
            
#             # Logica differenziata per tipo
#             if proposta.tipo == 'TES':
#                 nuova_istanza = Tessitura.objects.create(
#                     nome=proposta.nome, testo=proposta.descrizione,
#                     aura_richiesta=proposta.aura, elemento_principale=proposta.aura_infusione,
#                     proposta_creazione=proposta
#                 )
#             elif proposta.tipo == 'INF':
#                 nuova_istanza = Infusione.objects.create(
#                     nome=proposta.nome, testo=proposta.descrizione,
#                     aura_richiesta=proposta.aura, aura_infusione=proposta.aura_infusione,
#                     proposta_creazione=proposta, 
#                     tipo_risultato=proposta.tipo_risultato_atteso or 'POT'
#                 )
#             elif proposta.tipo == 'CER':
#                 nuova_istanza = Cerimoniale.objects.create(
#                     nome=proposta.nome, prerequisiti=proposta.prerequisiti,
#                     svolgimento=proposta.svolgimento, effetto=proposta.effetto,
#                     aura_richiesta=proposta.aura, liv=proposta.livello_proposto,
#                     proposta_creazione=proposta
#                 )

#             if nuova_istanza:
#                 # Copia automatica dei componenti (mattoni/caratteristiche)
#                 for comp in proposta.componenti.all():
#                     nuova_istanza.componenti.create(
#                         caratteristica=comp.caratteristica, 
#                         valore=comp.valore
#                     )
                
#                 proposta.stato = 'APPROVATA'
#                 proposta.save()
#                 return Response({
#                     'status': 'approvata', 
#                     'tipo': proposta.tipo, 
#                     'id_generato': nuova_istanza.id
#                 })

#         except PropostaTecnica.DoesNotExist:
#             return Response({'error': 'Proposta non trovata'}, status=404)
        
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
    
class RifiutaPropostaView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        proposta = get_object_or_404(PropostaTecnica, pk=pk)
        note_staff = request.data.get('note_staff', '')
        
        with transaction.atomic():
            proposta.stato = STATO_PROPOSTA_BOZZA
            proposta.note_staff = note_staff
            proposta.save()
            
            # Invia messaggio al creatore
            Messaggio.objects.create(
                mittente=request.user,
                destinatario_personaggio=proposta.personaggio,
                titolo=f"Proposta Rifiutata: {proposta.nome}",
                testo=f"La tua proposta per '{proposta.nome}' è stata rifiutata e riportata in bozza.\n\nNote Staff:\n{note_staff}"
            )
            
        return Response({'status': 'success', 'message': 'Proposta rifiutata'}, status=status.HTTP_200_OK)
    
class ProposteValutazioneList(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = PropostaTecnicaSerializer

    def get_queryset(self):
        return PropostaTecnica.objects.filter(stato=STATO_PROPOSTA_IN_VALUTAZIONE).order_by('data_invio')

class ApprovaPropostaView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        proposta = get_object_or_404(PropostaTecnica, pk=pk)
        
        # Facciamo una copia mutabile dei dati ricevuti dal frontend
        data = request.data.copy()
        
        personaggio = proposta.personaggio
        tipo = proposta.tipo
        aura = proposta.aura
        
        # --- 1. Calcolo Costi ---
        stat_costo = None
        if tipo == TIPO_PROPOSTA_INFUSIONE:
            stat_costo = aura.stat_costo_creazione_infusione
        elif tipo == TIPO_PROPOSTA_TESSITURA:
            stat_costo = aura.stat_costo_creazione_tessitura
        elif tipo == TIPO_PROPOSTA_CERIMONIALE:
            stat_costo = aura.stat_costo_creazione_cerimoniale
            
        costo_unitario = 0
        if stat_costo:
            # Calcola il costo usando il metodo del personaggio (Correzione precedente)
            costo_unitario = personaggio.get_valore_statistica(stat_costo.sigla)

        livello_finale = data.get('livello', proposta.livello)
        if tipo == TIPO_PROPOSTA_CERIMONIALE:
             livello_finale = data.get('liv', proposta.livello_proposto) or 1

        costo_totale = int(costo_unitario) * int(livello_finale)

        # Verifica Crediti
        if personaggio.crediti < costo_totale:
            return Response(
                {'error': f"Crediti insufficienti. Richiesti: {costo_totale}, Posseduti: {personaggio.crediti}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- 2. Esecuzione Atomica ---
        try:
            with transaction.atomic():
                # A. Prepara i dati obbligatori per il salvataggio
                # Iniettiamo gli ID nei dati che passeremo al serializer
                data['proposta_creazione'] = proposta.id
                data['aura_richiesta'] = aura.id
                
                # Serializer Selection (Usiamo i FullEditor per abilitare la scrittura)
                serializer = None
                
                if tipo == TIPO_PROPOSTA_INFUSIONE:
                    if proposta.aura_infusione:
                        data['aura_infusione'] = proposta.aura_infusione.id
                    serializer = InfusioneFullEditorSerializer(data=data)
                    
                elif tipo == TIPO_PROPOSTA_TESSITURA:
                    if proposta.aura_infusione:
                        # Le tessiture usano 'elemento_principale'
                        data['elemento_principale'] = proposta.aura_infusione.id
                    serializer = TessituraFullEditorSerializer(data=data)
                    
                elif tipo == TIPO_PROPOSTA_CERIMONIALE:
                    # Assicuriamoci che il livello sia settato
                    if 'liv' not in data:
                        data['liv'] = livello_finale
                    serializer = CerimonialeFullEditorSerializer(data=data)
                
                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                # B. Salva la Tecnica
                # I FullEditorSerializer gestiscono automaticamente anche il salvataggio dei componenti
                nuova_tecnica = serializer.save()
                
                # C. Assegna al Personaggio (Many2Many)
                if tipo == TIPO_PROPOSTA_INFUSIONE:
                    personaggio.infusioni_possedute.add(nuova_tecnica)
                elif tipo == TIPO_PROPOSTA_TESSITURA:
                    personaggio.tessiture_possedute.add(nuova_tecnica)
                elif tipo == TIPO_PROPOSTA_CERIMONIALE:
                    personaggio.cerimoniali_posseduti.add(nuova_tecnica)

                # D. Paga i crediti
                if costo_totale > 0:
                    personaggio.modifica_crediti(-costo_totale, f"Creazione {proposta.get_tipo_display()}: {nuova_tecnica.nome}")

                # E. Aggiorna Proposta
                proposta.stato = STATO_PROPOSTA_APPROVATA
                proposta.note_staff = data.get('note_staff', proposta.note_staff)
                proposta.save()

                # F. Invia Messaggio
                Messaggio.objects.create(
                    mittente=request.user,
                    destinatario_personaggio=personaggio,
                    titolo=f"Approvazione: {nuova_tecnica.nome}",
                    testo=(
                        f"La tua tecnica '{nuova_tecnica.nome}' è stata approvata e creata.\n"
                        f"Costo sostenuto: {costo_totale} crediti.\n\n"
                        f"NOTE STAFF:\n{proposta.note_staff}"
                    )
                )

            return Response({'status': 'success', 'id': nuova_tecnica.id}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)