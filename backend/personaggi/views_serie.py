"""API giocatore: inventario serie, documenti archiviati (Serie e testi)."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from personaggi import qr_random_pool
from personaggi.models import DocumentoArchiviato, Manifesto, Personaggio, SerieAssegnazione


def _resolve_own_personaggio(request, raw_pid):
    qs = Personaggio.objects.filter(proprietario=request.user)
    if raw_pid not in (None, ""):
        try:
            return qs.filter(pk=int(raw_pid)).first()
        except (TypeError, ValueError):
            return None
    return qs.first()


class SerieInventarioView(APIView):
    """
    GET — pezzi serie + documenti archiviati del personaggio.

    Response: { serie: [...], documenti: [...], personaggio_id }
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        pg = _resolve_own_personaggio(request, request.query_params.get("personaggio_id"))
        if not pg:
            return Response(
                {"error": "Personaggio non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serie = qr_random_pool.inventario_serie_per_personaggio(pg, request=request)
        documenti = qr_random_pool.inventario_documenti_per_personaggio(pg, request=request)
        return Response(
            {
                "serie": serie,
                "documenti": documenti,
                "personaggio_id": pg.pk,
            }
        )


class SerieAssegnazioneTrasferisciView(APIView):
    """
    POST — trasferisce un pezzo dell'inventario serie a un altro personaggio.

    Body: { personaggio_id, destinatario_personaggio_id }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, assegnazione_id):
        mittente = _resolve_own_personaggio(request, request.data.get("personaggio_id"))
        if not mittente:
            return Response(
                {"error": "Personaggio mittente non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        raw_dest = request.data.get("destinatario_personaggio_id")
        try:
            dest_id = int(raw_dest)
        except (TypeError, ValueError):
            return Response(
                {"error": "destinatario_personaggio_id obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        destinatario = Personaggio.objects.filter(pk=dest_id).first()
        if not destinatario:
            return Response(
                {"error": "Personaggio destinatario non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            ass = SerieAssegnazione.objects.select_related(
                "serie", "immagine", "personaggio", "oggetto"
            ).get(pk=assegnazione_id)
        except (SerieAssegnazione.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": "Pezzo serie non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payload, err = qr_random_pool.trasferisci_assegnazione_serie(
            assegnazione=ass,
            destinatario=destinatario,
            mittente=mittente,
        )
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "status": "success",
                "messaggio": (
                    f"Trasferito «{payload.get('etichetta')}» a {destinatario.nome}."
                ),
                "pezzo": payload,
            }
        )


class SerieAssegnazioneEliminaView(APIView):
    """DELETE — il giocatore elimina un pezzo serie dal proprio inventario."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, assegnazione_id):
        pg = _resolve_own_personaggio(
            request,
            request.query_params.get("personaggio_id") or request.data.get("personaggio_id"),
        )
        if not pg:
            return Response(
                {"error": "Personaggio non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            ass = SerieAssegnazione.objects.get(pk=assegnazione_id)
        except (SerieAssegnazione.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": "Pezzo serie non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        err = qr_random_pool.elimina_assegnazione_serie(assegnazione=ass, personaggio=pg)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"status": "success", "deleted": True})


class DocumentoArchiviatoSalvaView(APIView):
    """
    POST — salva snapshot manifesto/testo in «Serie e testi».

    Body: {
      personaggio_id, tipo: manifesto|testo, titolo, testo,
      testo_condizionato?, manifesto_id?,
      immagine_url?, audio_url?, video_url?
    }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        pg = _resolve_own_personaggio(request, request.data.get("personaggio_id"))
        if not pg:
            return Response(
                {"error": "Personaggio non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        tipo = (request.data.get("tipo") or "").strip().lower()
        manifesto = None
        raw_mid = request.data.get("manifesto_id")
        if raw_mid not in (None, ""):
            try:
                manifesto = Manifesto.objects.filter(pk=int(raw_mid)).first()
            except (TypeError, ValueError):
                manifesto = None
            if manifesto is None:
                return Response(
                    {"error": "Manifesto non trovato."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if tipo == "" or tipo == DocumentoArchiviato.TIPO_MANIFESTO:
                tipo = DocumentoArchiviato.TIPO_MANIFESTO

        titolo = request.data.get("titolo") or ""
        testo = request.data.get("testo") or ""
        testo_cond = request.data.get("testo_condizionato") or ""
        # Se manifesto e testo non passato: usa payload risolto (solo se leggibile)
        if manifesto is not None and not (testo or "").strip():
            from personaggi.qr_logic import risolvi_payload_manifesto

            payload = risolvi_payload_manifesto(manifesto, pg)
            if not payload.get("puo_leggere"):
                return Response(
                    {"error": payload.get("messaggio_accesso") or "Non puoi salvare questo manifesto."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            titolo = titolo or payload.get("nome") or manifesto.nome
            testo = payload.get("testo") or ""
            if payload.get("mostra_testo_condizionato"):
                testo_cond = payload.get("testo_condizionato") or ""

        doc, err = qr_random_pool.salva_documento_da_scan(
            personaggio=pg,
            tipo=tipo or DocumentoArchiviato.TIPO_TESTO,
            titolo=titolo,
            testo=testo,
            testo_condizionato=testo_cond,
            manifesto=manifesto,
            immagine_url=request.data.get("immagine_url") or "",
            audio_url=request.data.get("audio_url") or "",
            video_url=request.data.get("video_url") or "",
        )
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"status": "success", "messaggio": f"Salvato «{doc.get('titolo')}».", "documento": doc},
            status=status.HTTP_201_CREATED,
        )


class DocumentoArchiviatoTrasferisciView(APIView):
    """POST — trasferisce un documento archiviato a un altro personaggio."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, documento_id):
        mittente = _resolve_own_personaggio(request, request.data.get("personaggio_id"))
        if not mittente:
            return Response(
                {"error": "Personaggio mittente non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        raw_dest = request.data.get("destinatario_personaggio_id")
        try:
            dest_id = int(raw_dest)
        except (TypeError, ValueError):
            return Response(
                {"error": "destinatario_personaggio_id obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        destinatario = Personaggio.objects.filter(pk=dest_id).first()
        if not destinatario:
            return Response(
                {"error": "Personaggio destinatario non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            doc = DocumentoArchiviato.objects.get(pk=documento_id)
        except (DocumentoArchiviato.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": "Documento non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        payload, err = qr_random_pool.trasferisci_documento_archiviato(
            documento=doc,
            destinatario=destinatario,
            mittente=mittente,
        )
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "status": "success",
                "messaggio": f"Trasferito «{payload.get('titolo')}» a {destinatario.nome}.",
                "documento": payload,
            }
        )


class DocumentoArchiviatoEliminaView(APIView):
    """DELETE — elimina un documento dall'archivio del giocatore."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, documento_id):
        pg = _resolve_own_personaggio(
            request,
            request.query_params.get("personaggio_id") or request.data.get("personaggio_id"),
        )
        if not pg:
            return Response(
                {"error": "Personaggio non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            doc = DocumentoArchiviato.objects.get(pk=documento_id)
        except (DocumentoArchiviato.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": "Documento non trovato."},
                status=status.HTTP_404_NOT_FOUND,
            )
        err = qr_random_pool.elimina_documento_archiviato(documento=doc, personaggio=pg)
        if err:
            return Response({"error": err}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"status": "success", "deleted": True})
