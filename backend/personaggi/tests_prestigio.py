"""Prestigio come punteggio del personaggio.

Copre: punteggio editabile dallo staff, peso social dei like, premio evento,
ricompensa task con moltiplicatore KORP specifico, assenza di bonus da cariche.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from gestione_plot.evento_premi import applica_premio_presenza_personaggio
from gestione_plot.missioni_service import assegna_risoluzione
from gestione_plot.models import Evento, Missione, MissioneEvento
from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    Campagna,
    CampagnaUtente,
    Carica,
    Carriera,
    Personaggio,
    PersonaggioCarrieraMembership,
    PersonaggioLog,
    TipoCarriera,
    TipologiaPersonaggio,
)
from social.influencer import get_peso_social

User = get_user_model()


class PrestigioPunteggioTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(slug="prestigio", nome="Prestigio", attiva=True)
        self.tipologia = TipologiaPersonaggio.objects.create(nome="Giocante prestigio", giocante=True)
        self.pg = Personaggio.objects.create(
            nome="PG Prestigio",
            campagna=self.campagna,
            tipologia=self.tipologia,
        )

    def test_default_zero(self):
        self.assertEqual(self.pg.prestigio, 0)

    def test_modifica_prestigio_somma_e_logga(self):
        self.assertEqual(self.pg.modifica_prestigio(5, "test"), 5)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 5)
        self.assertTrue(
            PersonaggioLog.objects.filter(personaggio=self.pg, testo_log__contains="Prestigio +5").exists()
        )

    def test_modifica_prestigio_non_va_sotto_zero(self):
        self.pg.modifica_prestigio(3)
        self.assertEqual(self.pg.modifica_prestigio(-10), 0)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 0)

    def test_peso_social_minimo_uno(self):
        self.assertEqual(get_peso_social(self.pg), 1)
        self.pg.modifica_prestigio(7)
        self.assertEqual(get_peso_social(self.pg), 7)

    def test_cariche_non_assegnano_prestigio(self):
        tipo_korp, _ = TipoCarriera.objects.get_or_create(
            codice="korp", defaults={"nome": "KORP", "ordine": 0}
        )
        korp = Carriera.objects.create(nome="KORP Prestigio", tipo="T3", tipo_carriera=tipo_korp)
        carica = Carica.objects.create(nome="Comandante")
        carica.carriere.set([korp])
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pg,
            carriera=korp,
            tipo_carriera=tipo_korp,
            carica=carica,
        )
        self.pg.modifica_prestigio(4)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 4)
        self.assertEqual(get_peso_social(self.pg), 4)
        self.assertFalse(hasattr(carica, "bonus_peso_influencer"))


class PrestigioEventoTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(
            slug="prestigio-evento", nome="Prestigio evento", attiva=True
        )
        self.tipologia = TipologiaPersonaggio.objects.create(nome="Giocante ev", giocante=True)
        self.pg = Personaggio.objects.create(
            nome="PG Evento",
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        now = timezone.now()
        self.evento = Evento.objects.create(
            titolo="Evento prestigio",
            data_inizio=now - timedelta(hours=1),
            data_fine=now + timedelta(days=1),
        )

    def test_default_evento_non_assegna_prestigio(self):
        self.assertEqual(self.evento.prestigio_base_inizio_evento, 0)
        applica_premio_presenza_personaggio(self.evento, self.pg)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 0)

    def test_partecipazione_assegna_prestigio(self):
        self.evento.prestigio_base_inizio_evento = 3
        self.evento.save(update_fields=["prestigio_base_inizio_evento", "updated_at"])
        self.assertTrue(applica_premio_presenza_personaggio(self.evento, self.pg))
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 3)


class PrestigioTaskKorpTests(TestCase):
    """Moltiplicatore Prestigio della KORP, separato da quello dei Crediti."""

    def setUp(self):
        self.campagna = Campagna.objects.create(
            slug="prestigio-task", nome="Prestigio task", attiva=True
        )
        self.tipologia = TipologiaPersonaggio.objects.create(nome="Giocante task", giocante=True)
        self.tipo_korp, _ = TipoCarriera.objects.get_or_create(
            codice="korp", defaults={"nome": "KORP", "ordine": 0}
        )
        self.korp = Carriera.objects.create(
            nome="KORP Task",
            tipo="T3",
            tipo_carriera=self.tipo_korp,
            fattore_task_crediti=Decimal("1.00"),
            fattore_task_prestigio=Decimal("3.00"),
        )
        self.pg = Personaggio.objects.create(
            nome="PG Task",
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pg,
            carriera=self.korp,
            tipo_carriera=self.tipo_korp,
        )
        now = timezone.now()
        self.evento = Evento.objects.create(
            titolo="Evento task prestigio",
            data_inizio=now - timedelta(hours=1),
            data_fine=now + timedelta(days=1),
            started_at=now,
        )
        self.evento.partecipanti.add(self.pg)
        self.missione = Missione.objects.create(
            titolo="Task prestigiosa",
            korp=self.korp,
            reward_crediti=Decimal("10.00"),
            reward_prestigio=4,
        )
        MissioneEvento.objects.create(missione=self.missione, evento=self.evento, attiva=True)

    def test_task_assegna_prestigio_con_fattore_korp(self):
        ris = assegna_risoluzione(
            missione=self.missione,
            evento=self.evento,
            personaggio=self.pg,
        )
        self.assertEqual(ris.reward_prestigio, 12)
        self.assertEqual(ris.reward_crediti, Decimal("10.00"))
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 12)

    def test_fattore_prestigio_zero(self):
        self.korp.fattore_task_prestigio = Decimal("0.00")
        self.korp.save(update_fields=["fattore_task_prestigio", "updated_at"])
        self.missione.refresh_from_db()
        ris = assegna_risoluzione(
            missione=self.missione,
            evento=self.evento,
            personaggio=self.pg,
        )
        self.assertEqual(ris.reward_prestigio, 0)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 0)


class PrestigioStaffApiTests(TestCase):
    """Dashboard staff → Personaggi: il Prestigio è modificabile."""

    def setUp(self):
        self.campagna = Campagna.objects.create(
            slug="prestigio-staff", nome="Prestigio staff", attiva=True
        )
        self.master = User.objects.create_user(username="master_prestigio", password="x")
        CampagnaUtente.objects.create(
            campagna=self.campagna,
            user=self.master,
            ruolo=CAMPAGNA_ROLE_MASTER,
            attivo=True,
        )
        self.tipologia = TipologiaPersonaggio.objects.create(nome="Giocante staff", giocante=True)
        self.pg = Personaggio.objects.create(
            nome="PG Staff",
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.master)

    def test_patch_prestigio(self):
        resp = self.client.patch(
            f"/api/personaggi/api/staff/personaggi/{self.pg.pk}/",
            {"prestigio": 9},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data["prestigio"], 9)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 9)

    def test_patch_prestigio_zero_ammesso(self):
        self.pg.modifica_prestigio(5)
        resp = self.client.patch(
            f"/api/personaggi/api/staff/personaggi/{self.pg.pk}/",
            {"prestigio": 0},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 0)
