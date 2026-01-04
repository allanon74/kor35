from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from ..gestione_plot.models import QrCode, PropostaTecnica, Tessitura, Infusione, Cerimoniale
from ..gestione_plot.views import IsStaffOrMaster

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
    """
    Strumento MASTER: Trasforma una proposta in un elemento di gioco reale.
    """
    permission_classes = [IsAdminUser] # Solo Master

    def post(self, request, proposta_id):
        proposta = PropostaTecnica.objects.get(pk=proposta_id)
        
        # Logica di "promozione":
        if proposta.tipo == 'TES':
            # Creazione automatica Tessitura dai dati della proposta
            nuova = Tessitura.objects.create(
                nome=proposta.nome,
                testo=proposta.descrizione,
                aura_richiesta=proposta.aura,
                proposta_creazione=proposta
            )
            # Copiamo i componenti (mattoni)
            for comp in proposta.componenti.all():
                nuova.componenti.create(caratteristica=comp.caratteristica, valore=comp.valore)
        
        proposta.stato = 'APPROVATA'
        proposta.save()
        return Response({'status': 'promossa', 'id': nuova.id})