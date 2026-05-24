from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from gestione_plot.iscrizioni_evento_logic import importo_minimo_iscrizione, risolvi_scelte_iscrizione
from gestione_plot.models import Evento, EventoIscrizioneOpzione

User = get_user_model()


class IscrizioneOpzioniLogicTests(TestCase):
    def setUp(self):
        now = timezone.now()
        self.evento = Evento.objects.create(
            titolo="Test",
            data_inizio=now,
            data_fine=now,
            iscrizione_costo_euro=Decimal("30.00"),
            iscrizione_apertura=now,
            iscrizione_chiusura=now,
        )
        self.user = User.objects.create_user(username="t1", password="x")

    def test_importo_minimo_con_automatica_e_obbligatoria(self):
        EventoIscrizioneOpzione.objects.create(
            evento=self.evento,
            nome="Pasto",
            costo_euro=Decimal("10"),
            scelta_giocatore=False,
        )
        obb = EventoIscrizioneOpzione.objects.create(
            evento=self.evento,
            nome="Pernotto",
            costo_euro=Decimal("15"),
            scelta_giocatore=True,
            obbligatoria=True,
        )
        self.assertEqual(importo_minimo_iscrizione(self.evento), Decimal("55.00"))
        scelte, tot, err = risolvi_scelte_iscrizione(
            self.evento,
            modalita="iscrizione",
            utente=self.user,
            opzione_sync_ids_raw=[str(obb.sync_id)],
        )
        self.assertEqual(err, [])
        self.assertEqual(tot, Decimal("55.00"))
        self.assertEqual(len(scelte), 2)

    def test_facoltativa_solo_se_selezionata(self):
        fac = EventoIscrizioneOpzione.objects.create(
            evento=self.evento,
            nome="T-Shirt",
            costo_euro=Decimal("5"),
            scelta_giocatore=True,
            obbligatoria=False,
        )
        scelte, tot, err = risolvi_scelte_iscrizione(
            self.evento,
            modalita="iscrizione",
            utente=self.user,
            opzione_sync_ids_raw=[],
        )
        self.assertEqual(err, [])
        self.assertEqual(tot, Decimal("30.00"))
        self.assertEqual(len(scelte), 0)

        scelte2, tot2, err2 = risolvi_scelte_iscrizione(
            self.evento,
            modalita="iscrizione",
            utente=self.user,
            opzione_sync_ids_raw=[str(fac.sync_id)],
        )
        self.assertEqual(err2, [])
        self.assertEqual(tot2, Decimal("35.00"))
        self.assertEqual(len(scelte2), 1)

    def test_obbligatoria_mancante_errore(self):
        obb = EventoIscrizioneOpzione.objects.create(
            evento=self.evento,
            nome="Assicurazione",
            costo_euro=Decimal("3"),
            scelta_giocatore=True,
            obbligatoria=True,
        )
        _ = obb
        _, _, err = risolvi_scelte_iscrizione(
            self.evento,
            modalita="iscrizione",
            utente=self.user,
            opzione_sync_ids_raw=[],
        )
        self.assertTrue(any("obbligatoria" in e.lower() for e in err))
