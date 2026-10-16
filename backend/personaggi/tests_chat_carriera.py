"""Chat permanenti Korp/Dipartimento, lettura messaggi e personaggio preferito."""

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from personaggi.models import (
    TIER_3,
    Campagna,
    Carriera,
    Gruppo,
    LetturaMessaggio,
    Messaggio,
    Personaggio,
    PersonaggioCarrieraMembership,
    TipoCarriera,
    UserSocialPreference,
)


User = get_user_model()


class ChatCarrieraTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna = Campagna.objects.create(
            slug="chat-carriera-test",
            nome="Chat Carriera Test",
            attiva=True,
        )
        cls.tipo_korp, _ = TipoCarriera.objects.get_or_create(
            codice="korp", defaults={"nome": "KORP"}
        )
        cls.tipo_dip, _ = TipoCarriera.objects.get_or_create(
            codice="dipartimento", defaults={"nome": "Dipartimento"}
        )
        cls.tipo_prof, _ = TipoCarriera.objects.get_or_create(
            codice="professione", defaults={"nome": "Professione"}
        )
        cls.korp = Carriera.objects.create(
            nome="KORP Alba",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=cls.tipo_korp,
        )
        cls.dipartimento = Carriera.objects.create(
            nome="Medicina",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=cls.tipo_dip,
        )
        cls.professione = Carriera.objects.create(
            nome="Mercante",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=cls.tipo_prof,
        )
        cls.player = User.objects.create_user(username="chat_player", password="x")
        cls.peer = User.objects.create_user(username="chat_peer", password="x")
        cls.outsider = User.objects.create_user(username="chat_out", password="x")
        cls.staffer = User.objects.create_user(username="chat_staff", password="x")
        cls.pg = Personaggio.objects.create(
            nome="Ada", proprietario=cls.player, campagna=cls.campagna
        )
        cls.pg_peer = Personaggio.objects.create(
            nome="Bea", proprietario=cls.peer, campagna=cls.campagna
        )
        cls.pg_out = Personaggio.objects.create(
            nome="Ciro", proprietario=cls.outsider, campagna=cls.campagna
        )
        cls.pg_pref = Personaggio.objects.create(
            nome="Dina", proprietario=cls.player, campagna=cls.campagna
        )

    def _auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        return client

    def _conversazioni(self, client, personaggio):
        resp = client.get(
            f"/api/personaggi/api/messaggi/conversazioni/?personaggio_id={personaggio.id}"
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        return resp.json()

    def _chat_gruppo(self, payload, titolo):
        for row in payload:
            if row.get("tipo") == "gruppo" and row.get("titolo") == titolo:
                return row
        return None

    def test_korp_e_dipartimento_aprono_chat_permanenti(self):
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pg, carriera=self.korp, tipo_carriera=self.tipo_korp
        )
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pg, carriera=self.dipartimento, tipo_carriera=self.tipo_dip
        )
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pg, carriera=self.professione, tipo_carriera=self.tipo_prof
        )
        self.assertTrue(Gruppo.objects.filter(carriera=self.korp, chat_permanente=True).exists())
        self.assertTrue(
            Gruppo.objects.filter(carriera=self.dipartimento, chat_permanente=True).exists()
        )
        self.assertFalse(Gruppo.objects.filter(carriera=self.professione).exists())

        data = self._conversazioni(self._auth(self.player), self.pg)
        titoli = [row["titolo"] for row in data if row.get("tipo") == "gruppo"]
        self.assertEqual(titoli, ["KORP Alba", "Medicina"])
        for row in data:
            if row.get("tipo") == "gruppo":
                self.assertTrue(row["permanente"])
                self.assertEqual(row["messaggi"], [])
                self.assertEqual(row["non_letti"], 0)

    def test_membri_scrivono_leggono_pregresso_e_azzerano_i_non_letti(self):
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pg, carriera=self.korp, tipo_carriera=self.tipo_korp
        )
        client_a = self._auth(self.player)
        chat = self._chat_gruppo(self._conversazioni(client_a, self.pg), "KORP Alba")
        self.assertIsNotNone(chat)

        creato = client_a.post(
            "/api/personaggi/api/messaggi/gruppo/send/",
            {
                "personaggio_id": self.pg.id,
                "gruppo_id": chat["gruppo_id"],
                "testo": "Benvenuti a bordo",
            },
            format="json",
        )
        self.assertEqual(creato.status_code, 201, creato.content)

        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pg_peer, carriera=self.korp, tipo_carriera=self.tipo_korp
        )
        client_b = self._auth(self.peer)
        vista_b = self._chat_gruppo(self._conversazioni(client_b, self.pg_peer), "KORP Alba")
        self.assertIsNotNone(vista_b)
        self.assertEqual(len(vista_b["messaggi"]), 1)
        self.assertEqual(vista_b["messaggi"][0]["testo"], "Benvenuti a bordo")
        self.assertEqual(vista_b["non_letti"], 1)
        self.assertFalse(vista_b["messaggi"][0]["letto"])

        fuori = self._auth(self.outsider).post(
            "/api/personaggi/api/messaggi/gruppo/send/",
            {
                "personaggio_id": self.pg_out.id,
                "gruppo_id": chat["gruppo_id"],
                "testo": "Non dovrei",
            },
            format="json",
        )
        self.assertEqual(fuori.status_code, 403)

        letto = client_b.post(
            "/api/personaggi/api/messaggi/conversazioni/leggi/",
            {
                "personaggio_id": self.pg_peer.id,
                "conversazione_id": vista_b["conversazione_id"],
            },
            format="json",
        )
        self.assertEqual(letto.status_code, 200, letto.content)
        dopo = self._chat_gruppo(self._conversazioni(client_b, self.pg_peer), "KORP Alba")
        self.assertEqual(dopo["non_letti"], 0)
        self.assertEqual(len(dopo["messaggi"]), 1)
        self.assertTrue(dopo["messaggi"][0]["letto"])

        risposta = client_b.post(
            "/api/personaggi/api/messaggi/gruppo/send/",
            {
                "personaggio_id": self.pg_peer.id,
                "gruppo_id": vista_b["gruppo_id"],
                "testo": "Ricevuto",
            },
            format="json",
        )
        self.assertEqual(risposta.status_code, 201, risposta.content)
        vista_a = self._chat_gruppo(self._conversazioni(client_a, self.pg), "KORP Alba")
        self.assertEqual(len(vista_a["messaggi"]), 2)
        self.assertEqual(vista_a["non_letti"], 1)

    def test_uscita_dalla_korp_nasconde_la_chat(self):
        membership = PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pg, carriera=self.korp, tipo_carriera=self.tipo_korp
        )
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pg_peer, carriera=self.korp, tipo_carriera=self.tipo_korp
        )
        membership.data_a = timezone.now()
        membership.save()

        data = self._conversazioni(self._auth(self.player), self.pg)
        self.assertIsNone(self._chat_gruppo(data, "KORP Alba"))
        ancora = self._conversazioni(self._auth(self.peer), self.pg_peer)
        self.assertIsNotNone(self._chat_gruppo(ancora, "KORP Alba"))

    def test_messaggio_staff_si_segna_letto_per_il_personaggio(self):
        msg = Messaggio.objects.create(
            mittente=self.staffer,
            destinatario_personaggio=self.pg,
            tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
            is_staff_message=True,
            letto_staff=False,
            titolo="Ordine",
            testo="Presentarsi in plancia",
            campagna=self.campagna,
        )
        client = self._auth(self.player)
        prima = self._conversazioni(client, self.pg)
        staff = next(row for row in prima if row["conversazione_id"] == "staff")
        self.assertEqual(staff["non_letti"], 1)
        self.assertFalse(staff["messaggi"][0]["letto"])

        resp = client.post(
            f"/api/personaggi/api/messaggi/{msg.id}/leggi/",
            {"personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        dopo = self._conversazioni(client, self.pg)
        staff = next(row for row in dopo if row["conversazione_id"] == "staff")
        self.assertEqual(staff["non_letti"], 0)
        self.assertTrue(staff["messaggi"][0]["letto"])
        msg.refresh_from_db()
        self.assertFalse(msg.letto_staff)
        self.assertTrue(
            LetturaMessaggio.objects.filter(
                messaggio=msg, personaggio=self.pg, letto=True
            ).exists()
        )

        lista = client.get(f"/api/personaggi/api/messaggi/?personaggio_id={self.pg.id}")
        self.assertEqual(lista.status_code, 200, lista.content)
        riga = next(row for row in lista.json() if row["id"] == msg.id)
        self.assertTrue(riga["letto"])

    def test_inbox_staff_segna_letto_e_non_letto(self):
        from personaggi.models import CAMPAGNA_ROLE_STAFFER, CampagnaUtente

        CampagnaUtente.objects.update_or_create(
            user=self.staffer,
            campagna=self.campagna,
            defaults={"ruolo": CAMPAGNA_ROLE_STAFFER, "attivo": True},
        )
        msg = Messaggio.objects.create(
            mittente_personaggio=self.pg,
            tipo_messaggio=Messaggio.TIPO_STAFF,
            is_staff_message=True,
            letto_staff=False,
            titolo="Aiuto",
            testo="Serve lo staff",
            campagna=self.campagna,
        )
        client = self._auth(self.staffer)
        inbox = client.get("/api/personaggi/api/staff/messages/")
        self.assertEqual(inbox.status_code, 200, inbox.content)
        riga = next(row for row in inbox.json() if row["id"] == msg.id)
        self.assertFalse(riga["letto"])
        self.assertFalse(riga["letto_staff"])

        marca = client.post(
            f"/api/personaggi/api/staff/messages/{msg.id}/leggi/",
            {"letto": True},
            format="json",
        )
        self.assertEqual(marca.status_code, 200, marca.content)
        msg.refresh_from_db()
        self.assertTrue(msg.letto_staff)

        smarca = client.post(
            f"/api/personaggi/api/staff/messages/{msg.id}/leggi/",
            {"letto": False},
            format="json",
        )
        self.assertEqual(smarca.status_code, 200, smarca.content)
        msg.refresh_from_db()
        self.assertFalse(msg.letto_staff)
        inbox = client.get("/api/personaggi/api/staff/messages/")
        riga = next(row for row in inbox.json() if row["id"] == msg.id)
        self.assertFalse(riga["letto"])
        self.assertFalse(riga["letto_staff"])

    def test_preferito_unico_e_persistente(self):
        client = self._auth(self.player)
        primo = client.post(
            "/api/personaggi/api/personaggi/preferred/",
            {"preferred_personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(primo.status_code, 200, primo.content)
        self.assertEqual(primo.json()["preferred_personaggio_id"], self.pg.id)

        altro_client = self._auth(self.player)
        letto = altro_client.get("/api/personaggi/api/personaggi/preferred/")
        self.assertEqual(letto.status_code, 200)
        self.assertEqual(letto.json()["preferred_personaggio_id"], self.pg.id)
        self.assertEqual(letto.json()["campagna_slug"], self.campagna.slug)

        secondo = client.post(
            "/api/personaggi/api/personaggi/preferred/",
            {"preferred_personaggio_id": self.pg_pref.id},
            format="json",
        )
        self.assertEqual(secondo.status_code, 200, secondo.content)
        self.assertEqual(secondo.json()["preferred_personaggio_id"], self.pg_pref.id)
        prefs = UserSocialPreference.objects.filter(user=self.player)
        self.assertEqual(prefs.count(), 1)
        self.assertEqual(prefs.get().preferred_personaggio_id, self.pg_pref.id)
