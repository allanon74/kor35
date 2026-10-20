"""Staff: istanza da infusione, slot corporei, montaggio d'ufficio."""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from personaggi.models import (
    AURA,
    SCELTA_RISULTATO_AUMENTO,
    Campagna,
    Infusione,
    Oggetto,
    Personaggio,
    Punteggio,
    TIPO_OGGETTO_FISICO,
    TIPO_OGGETTO_INNESTO,
    TIPO_OGGETTO_MATERIA,
    TIPO_OGGETTO_MOD,
    TIPO_OGGETTO_MUTAZIONE,
    TipologiaPersonaggio,
)


class StaffIstanzeInfusioneTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff-istanze", password="x", is_staff=True, is_superuser=True
        )
        self.client.force_authenticate(user=self.staff)
        self.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={
                "nome": "Kor35",
                "is_default": True,
                "is_base": True,
                "attiva": True,
            },
        )
        self.headers = {"HTTP_X_CAMPAGNA": self.campagna.slug}
        self.aura = Punteggio.objects.create(nome="Aura Mondana Staff", sigla="AMS", tipo=AURA)
        self.aura_ate = Punteggio.objects.create(nome="Aura Tecnologica", sigla="ATE", tipo=AURA)
        self.tipo = TipologiaPersonaggio.objects.create(nome="PG istanze", giocante=True)
        self.pg = Personaggio.objects.create(
            nome="Ada Staff", tipologia=self.tipo, campagna=self.campagna
        )
        self.altro = Personaggio.objects.create(
            nome="Altro PG", tipologia=self.tipo, campagna=self.campagna
        )
        self.inf_materia = Infusione.objects.create(
            nome="Scheggia di vetro",
            testo="materia",
            aura_richiesta=self.aura,
            campagna=self.campagna,
        )
        self.inf_mut = Infusione.objects.create(
            nome="Pelle di pietra",
            testo="mutazione",
            aura_richiesta=self.aura,
            tipo_risultato=SCELTA_RISULTATO_AUMENTO,
            slot_corpo_permessi="HD1,TR1",
            campagna=self.campagna,
        )
        self.inf_inn = Infusione.objects.create(
            nome="Occhio sintetico",
            testo="innesto",
            aura_richiesta=self.aura_ate,
            tipo_risultato=SCELTA_RISULTATO_AUMENTO,
            slot_corpo_permessi="HD2",
            campagna=self.campagna,
        )
        self.inf_mod = Infusione.objects.create(
            nome="Circuito",
            testo="mod",
            aura_richiesta=self.aura_ate,
            campagna=self.campagna,
        )

    def _post_infusione(self, infusione, **payload):
        return self.client.post(
            f"/api/personaggi/api/staff/infusioni/{infusione.id}/crea-istanza/",
            payload,
            format="json",
            **self.headers,
        )

    def _post_pg(self, path, **payload):
        return self.client.post(
            f"/api/personaggi/api/staff/personaggi/{self.pg.id}/{path}/",
            payload,
            format="json",
            **self.headers,
        )

    def test_crea_istanza_senza_personaggio(self):
        r = self._post_infusione(self.inf_materia)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        oggetto = Oggetto.objects.get(pk=r.data["id"])
        self.assertEqual(oggetto.tipo_oggetto, TIPO_OGGETTO_MATERIA)
        self.assertIsNone(oggetto.inventario_corrente)
        self.assertIsNone(oggetto.ospitato_su_id)

    def test_crea_istanza_e_associa_personaggio(self):
        r = self._post_infusione(self.inf_materia, personaggio_id=self.pg.id)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        oggetto = Oggetto.objects.get(pk=r.data["id"])
        self.assertEqual(oggetto.inventario_corrente.pk, self.pg.pk)
        self.assertIn(self.pg.nome, r.data["detail"])

    def test_mutazione_senza_slot_non_crea_oggetto(self):
        prima = Oggetto.objects.count()
        r = self._post_pg("crea-oggetto-da-infusione", infusione_id=self.inf_mut.id)
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        self.assertIn("slot", r.data["detail"].lower())
        self.assertEqual(Oggetto.objects.count(), prima)

    def test_mutazione_slot_non_consentito(self):
        r = self._post_pg(
            "crea-oggetto-da-infusione",
            infusione_id=self.inf_mut.id,
            slot_corpo="HD2",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)

    def test_mutazione_slot_occupato(self):
        occupante = Oggetto.objects.create(
            nome="Mutazione già montata",
            tipo_oggetto=TIPO_OGGETTO_MUTAZIONE,
            slot_corpo="HD1",
            is_equipaggiato=True,
        )
        occupante.sposta_in_inventario(self.pg)
        r = self._post_pg(
            "crea-oggetto-da-infusione",
            infusione_id=self.inf_mut.id,
            slot_corpo="HD1",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        self.assertIn("occupato", r.data["detail"].lower())

    def test_mutazione_su_slot_libero(self):
        r = self._post_pg(
            "crea-oggetto-da-infusione",
            infusione_id=self.inf_mut.id,
            slot_corpo="HD1",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        oggetto = Oggetto.objects.get(pk=r.data["id"])
        self.assertEqual(oggetto.tipo_oggetto, TIPO_OGGETTO_MUTAZIONE)
        self.assertEqual(oggetto.slot_corpo, "HD1")
        self.assertTrue(oggetto.is_equipaggiato)
        self.assertEqual(oggetto.inventario_corrente.pk, self.pg.pk)

    def test_innesto_su_slot_libero(self):
        r = self._post_infusione(
            self.inf_inn, personaggio_id=self.pg.id, slot_corpo="HD2"
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        oggetto = Oggetto.objects.get(pk=r.data["id"])
        self.assertEqual(oggetto.tipo_oggetto, TIPO_OGGETTO_INNESTO)
        self.assertEqual(oggetto.slot_corpo, "HD2")

    def test_materia_installata_su_oggetto_del_personaggio(self):
        host = Oggetto.objects.create(nome="Lama", tipo_oggetto=TIPO_OGGETTO_FISICO)
        host.sposta_in_inventario(self.pg)
        r = self._post_pg(
            "crea-oggetto-da-infusione",
            infusione_id=self.inf_materia.id,
            oggetto_ospite_id=host.id,
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        oggetto = Oggetto.objects.get(pk=r.data["id"])
        self.assertEqual(oggetto.tipo_oggetto, TIPO_OGGETTO_MATERIA)
        self.assertEqual(oggetto.ospitato_su_id, host.id)
        self.assertIsNone(oggetto.inventario_corrente)

    def test_mod_installata_su_oggetto_del_personaggio(self):
        host = Oggetto.objects.create(nome="Pistola", tipo_oggetto=TIPO_OGGETTO_FISICO)
        host.sposta_in_inventario(self.pg)
        r = self._post_infusione(
            self.inf_mod,
            personaggio_id=self.pg.id,
            oggetto_ospite_id=host.id,
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        oggetto = Oggetto.objects.get(pk=r.data["id"])
        self.assertEqual(oggetto.tipo_oggetto, TIPO_OGGETTO_MOD)
        self.assertEqual(oggetto.ospitato_su_id, host.id)

    def test_rifiuta_oggetto_di_un_altro_personaggio(self):
        host = Oggetto.objects.create(nome="Lama altrui", tipo_oggetto=TIPO_OGGETTO_FISICO)
        host.sposta_in_inventario(self.altro)
        prima = Oggetto.objects.filter(infusione_generatrice=self.inf_materia).count()
        r = self._post_pg(
            "crea-oggetto-da-infusione",
            infusione_id=self.inf_materia.id,
            oggetto_ospite_id=host.id,
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        self.assertEqual(
            Oggetto.objects.filter(infusione_generatrice=self.inf_materia).count(),
            prima,
        )

    def test_monta_e_smonta_materia_d_ufficio(self):
        host = Oggetto.objects.create(nome="Armatura", tipo_oggetto=TIPO_OGGETTO_FISICO)
        materia = Oggetto.objects.create(nome="Materia sciolta", tipo_oggetto=TIPO_OGGETTO_MATERIA)
        host.sposta_in_inventario(self.pg)
        materia.sposta_in_inventario(self.pg)

        monta = self._post_pg(
            "monta-potenziamento",
            componente_id=materia.id,
            oggetto_ospite_id=host.id,
        )
        self.assertEqual(monta.status_code, status.HTTP_200_OK, monta.data)
        materia.refresh_from_db()
        self.assertEqual(materia.ospitato_su_id, host.id)

        detail = self.client.get(
            f"/api/personaggi/api/staff/personaggi/{self.pg.id}/",
            **self.headers,
        )
        self.assertEqual(detail.status_code, status.HTTP_200_OK, detail.content)
        righe = detail.json()["oggetti_inventario"]
        host_row = next(row for row in righe if row["id"] == host.id)
        self.assertEqual(host_row["potenziamenti"][0]["id"], materia.id)
        self.assertFalse(any(row["id"] == materia.id for row in righe))

        smonta = self._post_pg("smonta-potenziamento", componente_id=materia.id)
        self.assertEqual(smonta.status_code, status.HTTP_200_OK, smonta.data)
        materia.refresh_from_db()
        self.assertIsNone(materia.ospitato_su_id)
        self.assertEqual(materia.inventario_corrente.pk, self.pg.pk)

    def test_monta_rifiuta_inventari_diversi(self):
        host = Oggetto.objects.create(nome="Scudo", tipo_oggetto=TIPO_OGGETTO_FISICO)
        materia = Oggetto.objects.create(nome="Materia altrove", tipo_oggetto=TIPO_OGGETTO_MATERIA)
        host.sposta_in_inventario(self.pg)
        materia.sposta_in_inventario(self.altro)
        r = self._post_pg(
            "monta-potenziamento",
            componente_id=materia.id,
            oggetto_ospite_id=host.id,
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        materia.refresh_from_db()
        self.assertIsNone(materia.ospitato_su_id)

    def test_non_staff_non_puo_creare(self):
        utente = User.objects.create_user(username="giocatore-istanze", password="x")
        self.client.force_authenticate(user=utente)
        r = self._post_infusione(self.inf_materia)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        r2 = self._post_pg("monta-potenziamento", componente_id=1, oggetto_ospite_id=2)
        self.assertEqual(r2.status_code, status.HTTP_403_FORBIDDEN)
