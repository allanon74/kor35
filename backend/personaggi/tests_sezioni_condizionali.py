"""Sezioni condizionali su Infusione/Oggetto: testo extra e stats se requisito."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from personaggi.models import (
    AURA,
    CARATTERISTICA,
    MODIFICATORE_ADDITIVO,
    Abilita,
    Campagna,
    Infusione,
    InfusioneSezioneCondizionale,
    InfusioneSezioneStatistica,
    InfusioneSezioneStatisticaBase,
    InfusioneStatisticaBase,
    Oggetto,
    OggettoSezioneCondizionale,
    Personaggio,
    PersonaggioAbilita,
    Punteggio,
    Statistica,
    TIPO_OGGETTO_FISICO,
    abilita_punteggio,
)
from personaggi.requisiti_accesso import confronta_valore, personaggio_soddisfa_requisiti
from personaggi.services import GestioneOggettiService


class RequisitiOperatoreTests(TestCase):
    def test_confronta_gt_gte(self):
        self.assertTrue(confronta_valore(3, 2, "gt"))
        self.assertFalse(confronta_valore(2, 2, "gt"))
        self.assertTrue(confronta_valore(2, 2, "gte"))
        self.assertTrue(confronta_valore(5, 4, ">"))


class SezioniCondizionaliTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sez-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Sezioni", proprietario=self.user)
        self.ca = Punteggio.objects.create(nome="Forza Sez", sigla="FSZ", tipo=CARATTERISTICA)
        self.aura_mag = Punteggio.objects.create(nome="Aura Magica Sez", sigla="AMZ", tipo=AURA)
        self.aura_inn = Punteggio.objects.create(nome="Aura Innata Sez", sigla="AIZ", tipo=AURA)
        self.aura_req = Punteggio.objects.create(nome="Aura Craft Sez", sigla="ACZ", tipo=AURA)

        self.stat_pv = Statistica.objects.create(
            nome="Punti Vita Sez", sigla="PVZ", parametro="pvz", valore_base_predefinito=0
        )
        self.stat_rango = Statistica.objects.create(
            nome="Rango Attacco Sez", sigla="RAZ", parametro="rango", valore_base_predefinito=0
        )
        self.stat_danno = Statistica.objects.create(
            nome="Danno Mischia Sez", sigla="DMZ", parametro="dannimis", valore_base_predefinito=0
        )

        grant = Abilita.objects.create(nome="Grant AMZ", caratteristica=self.ca, costo_pc=0, costo_crediti=0)
        abilita_punteggio.objects.create(abilita=grant, punteggio=self.aura_mag, valore=5)
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=grant)

        self.infusione = Infusione.objects.create(
            nome="Spada delle Ere Sez",
            testo="La spada infligge danni.",
            aura_richiesta=self.aura_req,
        )
        InfusioneStatisticaBase.objects.create(
            infusione=self.infusione, statistica=self.stat_danno, valore_base=3
        )
        sez_rango = InfusioneSezioneCondizionale.objects.create(
            infusione=self.infusione,
            ordine=0,
            testo="Il rango degli attacchi con la spada è aumentato di uno.",
            condizioni={
                "operator": "AND",
                "requisiti": [{"tipo": "punteggio", "nome": "Aura Magica Sez", "min": 2, "op": "gt"}],
            },
        )
        InfusioneSezioneStatisticaBase.objects.create(
            sezione=sez_rango, statistica=self.stat_rango, valore_base=2
        )

        sez_pv = InfusioneSezioneCondizionale.objects.create(
            infusione=self.infusione,
            ordine=1,
            testo="Il personaggio aumenta di due i PV.",
            condizioni={
                "operator": "AND",
                "requisiti": [{"tipo": "punteggio", "nome": "Aura Magica Sez", "min": 4, "op": "gt"}],
            },
        )
        InfusioneSezioneStatistica.objects.create(
            sezione=sez_pv,
            statistica=self.stat_pv,
            valore=Decimal("2"),
            tipo_modificatore=MODIFICATORE_ADDITIVO,
        )

        sez_ain = InfusioneSezioneCondizionale.objects.create(
            infusione=self.infusione,
            ordine=2,
            testo="Il rango dei Punti vita aumenta di uno.",
            condizioni={
                "operator": "AND",
                "requisiti": [{"tipo": "punteggio", "sigla": "AIZ", "min": 4, "op": "gt"}],
            },
        )
        InfusioneSezioneStatistica.objects.create(
            sezione=sez_ain,
            statistica=self.stat_pv,
            valore=Decimal("1"),
            tipo_modificatore=MODIFICATORE_ADDITIVO,
        )

    def test_requisito_aura_gt(self):
        ok, _ = personaggio_soddisfa_requisiti(
            self.pg,
            [{"tipo": "punteggio", "nome": "Aura Magica Sez", "min": 2, "op": "gt"}],
        )
        self.assertTrue(ok)
        ok_high, _ = personaggio_soddisfa_requisiti(
            self.pg,
            [{"tipo": "punteggio", "nome": "Aura Magica Sez", "min": 5, "op": "gt"}],
        )
        self.assertFalse(ok_high)

    def test_testo_personaggio_mostra_sezioni_aura_magica(self):
        html = self.pg.get_testo_formattato_per_item(self.infusione)
        self.assertIn("rango degli attacchi", html)
        self.assertIn("aumenta di due i PV", html)
        self.assertNotIn("rango dei Punti vita", html)

    def test_catalogo_senza_pg_etichetta_condizioni(self):
        html = self.infusione.TestoFormattato
        self.assertIn("Aura Magica Sez", html)
        self.assertIn("rango degli attacchi", html)

    def test_forge_copia_sezioni_e_modificatori_attivi(self):
        oggetto = GestioneOggettiService.crea_oggetto_da_infusione(self.infusione, self.pg)
        self.assertEqual(oggetto.sezioni_condizionali.count(), 3)
        oggetto.tipo_oggetto = TIPO_OGGETTO_FISICO
        oggetto.is_equipaggiato = True
        oggetto.save(update_fields=["tipo_oggetto", "is_equipaggiato", "updated_at"])
        if hasattr(self.pg, "_modificatori_calcolati_cache"):
            del self.pg._modificatori_calcolati_cache
        mods = self.pg.modificatori_calcolati
        self.assertEqual(mods.get("pvz", {}).get("add", 0), 2)
        html = self.pg.get_testo_formattato_per_item(oggetto)
        self.assertIn("rango degli attacchi", html)
        self.assertNotIn("rango dei Punti vita", html)


class StaffInfusioneSezioniTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff-sez", password="x", is_staff=True, is_superuser=True)
        self.client.force_authenticate(user=self.staff)
        self.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={"nome": "Kor35", "is_default": True, "is_base": True, "attiva": True},
        )
        self.aura = Punteggio.objects.create(nome="Aura Staff Sez", sigla="ASZ", tipo=AURA)
        self.stat = Statistica.objects.create(
            nome="PV Staff Sez", sigla="PSZ", parametro="pvsz", valore_base_predefinito=0
        )
        self.url = "/api/personaggi/api/staff/infusioni/"
        self.headers = {"HTTP_X_CAMPAGNA": self.campagna.slug}

    def test_create_infusione_con_sezione_condizionale(self):
        payload = {
            "nome": "Inf sezioni nested",
            "testo": "base",
            "aura_richiesta": self.aura.id,
            "sezioni_condizionali": [
                {
                    "ordine": 0,
                    "testo": "Bonus PV se aura alta",
                    "condizioni": {
                        "operator": "AND",
                        "requisiti": [{"tipo": "punteggio", "nome": "Aura Staff Sez", "min": 2, "op": "gt"}],
                    },
                    "statistiche_base": [],
                    "modificatori": [
                        {"statistica": self.stat.id, "valore": 2, "tipo_modificatore": "ADD"},
                    ],
                }
            ],
        }
        r = self.client.post(self.url, payload, format="json", **self.headers)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        infusione = Infusione.objects.get(pk=r.data["id"])
        sezioni = list(infusione.sezioni_condizionali.all())
        self.assertEqual(len(sezioni), 1)
        self.assertEqual(sezioni[0].testo, "Bonus PV se aura alta")
        self.assertEqual(sezioni[0].modificatori.count(), 1)
        self.assertEqual(sezioni[0].modificatori.first().statistica_id, self.stat.id)

    def test_create_oggetto_con_sezione(self):
        payload = {
            "nome": "Spada sez",
            "testo": " lama ",
            "tipo_oggetto": TIPO_OGGETTO_FISICO,
            "sezioni_condizionali": [
                {
                    "testo": "Extra se INT",
                    "condizioni": {
                        "operator": "AND",
                        "requisiti": [{"tipo": "statistica", "sigla": "PSZ", "min": 1, "op": "gte"}],
                    },
                    "modificatori": [{"statistica": self.stat.id, "valore": 1, "tipo_modificatore": "ADD"}],
                }
            ],
        }
        r = self.client.post(
            "/api/personaggi/api/staff/oggetti/",
            payload,
            format="json",
            **self.headers,
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        oggetto = Oggetto.objects.get(pk=r.data["id"])
        self.assertEqual(oggetto.sezioni_condizionali.count(), 1)
        self.assertTrue(OggettoSezioneCondizionale.objects.filter(oggetto=oggetto).exists())
