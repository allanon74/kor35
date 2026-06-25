from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from .models import (
    Abilita,
    AbilitaStatistica,
    AURA,
    Campagna,
    CampagnaUtente,
    MODIFICATORE_ADDITIVO,
    MODIFICATORE_MOLTIPLICATIVO,
    Oggetto,
    OggettoBase,
    OggettoBaseStatisticaBase,
    OggettoInInventario,
    OggettoStatistica,
    OggettoStatisticaBase,
    Personaggio,
    Infusione,
    InfusioneCostoAttivazione,
    PersonaggioStatisticaBase,
    Punteggio,
    SLOT_EQUIP_CONTEGGIO_OGGETTI_MODIFICATI,
    SLOT_EQUIP_CONTEGGIO_OGNI_POTENZIAMENTO,
    SLOT_EQUIP_CONTEGGIO_TUTTI_OGGETTI,
    Statistica,
    Tessitura,
    TessituraCostoAttivazione,
    TessituraEffettoRuntime,
    TipologiaPersonaggio,
    TIPO_OGGETTO_FISICO,
    TIPO_OGGETTO_MOD,
    TIPO_OGGETTO_MATERIA,
    abilita_punteggio,
    CARATTERISTICA,
    formatta_testo_generico,
    raccogli_modificatori_solo_oggetto,
)
from .serializers import OggettoSerializer, PersonaggioDetailSerializer
from .services import GestioneOggettiService
from .sso import _upsert_local_user


class CampagnaAdminApiTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff", password="x", is_staff=True)
        self.client.force_authenticate(user=self.staff)

        self.kor35 = Campagna.objects.create(
            slug="kor35",
            nome="Kor35",
            is_default=True,
            is_base=True,
            attiva=True,
        )

    def test_create_new_default_unsets_previous_default(self):
        response = self.client.post(
            "/api/personaggi/api/staff/campagne/",
            {
                "slug": "campagna-b",
                "nome": "Campagna B",
                "is_default": True,
                "is_base": False,
                "attiva": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.kor35.refresh_from_db()
        self.assertFalse(self.kor35.is_default)

    def test_update_last_default_to_false_is_blocked(self):
        response = self.client.patch(
            f"/api/personaggi/api/staff/campagne/{self.kor35.id}/",
            {"is_default": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_default", response.data)

    def test_create_new_base_unsets_previous_base(self):
        response = self.client.post(
            "/api/personaggi/api/staff/campagne/",
            {
                "slug": "campagna-c",
                "nome": "Campagna C",
                "is_default": False,
                "is_base": True,
                "attiva": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.kor35.refresh_from_db()
        self.assertFalse(self.kor35.is_base)


class ActiveCampaignValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="player", password="x")
        self.client.force_authenticate(user=self.user)
        self.kor35 = Campagna.objects.create(
            slug="kor35",
            nome="Kor35",
            is_default=True,
            is_base=True,
            attiva=True,
        )
        self.alt = Campagna.objects.create(
            slug="alt-camp",
            nome="Alt Camp",
            is_default=False,
            is_base=False,
            attiva=True,
        )

    def test_validate_non_member_campaign_returns_403(self):
        response = self.client.post(
            "/api/personaggi/api/campagne/active/",
            {"slug": "alt-camp"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_validate_member_campaign_returns_200(self):
        CampagnaUtente.objects.create(
            campagna=self.alt,
            user=self.user,
            ruolo="PLAYER",
            attivo=True,
        )
        response = self.client.post(
            "/api/personaggi/api/campagne/active/",
            {"slug": "alt-camp"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("slug"), "alt-camp")


class UserDefaultCampaignMembershipTests(APITestCase):
    def setUp(self):
        self.kor35 = Campagna.objects.create(
            slug="kor35",
            nome="Kor35",
            is_default=True,
            is_base=True,
            attiva=True,
        )

    def test_new_user_is_auto_assigned_to_base_campaign(self):
        user = User.objects.create_user(username="newbie", password="x")
        memberships = CampagnaUtente.objects.filter(user=user)
        self.assertEqual(memberships.count(), 1)
        self.assertEqual(memberships.first().campagna_id, self.kor35.id)
        self.assertEqual(memberships.first().ruolo, "PLAYER")

    def test_new_user_does_not_get_other_campaigns_by_default(self):
        Campagna.objects.create(
            slug="side-quest",
            nome="Side Quest",
            is_default=False,
            is_base=False,
            attiva=True,
        )
        user = User.objects.create_user(username="newbie2", password="x")
        campaign_slugs = set(
            CampagnaUtente.objects.filter(user=user).select_related("campagna").values_list("campagna__slug", flat=True)
        )
        self.assertEqual(campaign_slugs, {"kor35"})


class ArcanaSSONewUserCampaignAssignmentTests(APITestCase):
    def setUp(self):
        self.kor35 = Campagna.objects.create(
            slug="kor35",
            nome="Kor35",
            is_default=True,
            is_base=True,
            attiva=True,
        )
        Campagna.objects.create(
            slug="alt-camp",
            nome="Alt Camp",
            is_default=False,
            is_base=False,
            attiva=True,
        )

    def test_arcana_new_user_is_auto_assigned_to_base_campaign(self):
        profile = {
            "sub": "arcana-sub-999",
            "email": "arcana-new-user@example.com",
            "username": "arcana.new.user",
            "nome": "Arcana",
            "cognome": "Player",
        }
        user = _upsert_local_user(profile)
        memberships = CampagnaUtente.objects.filter(user=user).select_related("campagna")
        self.assertEqual(memberships.count(), 1)
        self.assertEqual(memberships.first().campagna_id, self.kor35.id)
        self.assertEqual(memberships.first().ruolo, "PLAYER")

    def test_arcana_existing_user_without_membership_is_repaired(self):
        existing = User.objects.create_user(
            username="legacy-user",
            email="legacy-user@example.com",
            password="legacy-pass",
        )
        self.assertFalse(CampagnaUtente.objects.filter(user=existing).exists())

        profile = {
            "sub": "arcana-sub-legacy-001",
            "email": "legacy-user@example.com",
            "username": "legacy.user",
            "nome": "Legacy",
            "cognome": "Player",
        }
        user = _upsert_local_user(profile)
        memberships = CampagnaUtente.objects.filter(user=user).select_related("campagna")
        self.assertEqual(user.id, existing.id)
        self.assertEqual(memberships.count(), 1)
        self.assertEqual(memberships.first().campagna_id, self.kor35.id)


class LocalLoginCampaignRepairTests(APITestCase):
    def setUp(self):
        self.kor35 = Campagna.objects.create(
            slug="kor35",
            nome="Kor35",
            is_default=True,
            is_base=True,
            attiva=True,
        )

    def test_local_login_repairs_missing_active_membership_for_player(self):
        user = User.objects.create_user(
            username="player-no-campaign",
            email="player-no-campaign@example.com",
            password="pw-test-123",
        )
        CampagnaUtente.objects.filter(user=user).delete()
        self.assertFalse(CampagnaUtente.objects.filter(user=user, attivo=True).exists())

        response = self.client.post(
            "/api/auth/",
            {"username": "player-no-campaign", "password": "pw-test-123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CampagnaUtente.objects.filter(user=user, campagna=self.kor35, attivo=True).exists())

    def test_local_login_does_not_auto_assign_staff_or_superuser(self):
        staff = User.objects.create_user(
            username="staff-no-campaign",
            email="staff-no-campaign@example.com",
            password="pw-test-123",
            is_staff=True,
        )
        superuser = User.objects.create_user(
            username="super-no-campaign",
            email="super-no-campaign@example.com",
            password="pw-test-123",
            is_superuser=True,
        )
        CampagnaUtente.objects.filter(user__in=[staff, superuser]).delete()

        r_staff = self.client.post(
            "/api/auth/",
            {"username": "staff-no-campaign", "password": "pw-test-123"},
            format="json",
        )
        r_super = self.client.post(
            "/api/auth/",
            {"username": "super-no-campaign", "password": "pw-test-123"},
            format="json",
        )
        self.assertEqual(r_staff.status_code, status.HTTP_200_OK)
        self.assertEqual(r_super.status_code, status.HTTP_200_OK)
        self.assertFalse(CampagnaUtente.objects.filter(user=staff).exists())
        self.assertFalse(CampagnaUtente.objects.filter(user=superuser).exists())


class AINTraitPcDeltaTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ain-player", password="x")
        self.client.force_authenticate(user=self.user)

        self.campagna = Campagna.objects.create(
            slug="kor35-ain",
            nome="Kor35 AIN",
            is_default=True,
            is_base=True,
            attiva=True,
        )
        self.tipologia = TipologiaPersonaggio.objects.create(
            nome="Giocante AIN Test",
            caratteristiche_iniziali=8,
            crediti_iniziali=0,
            giocante=True,
        )
        self.caratteristica = Punteggio.objects.create(
            nome="Caratteristica Test AIN",
            sigla="CAT",
            tipo="CA",
        )
        self.aura_innata = Punteggio.objects.create(
            nome="Aura Innata Test",
            sigla="AIN",
            tipo="AU",
        )
        self.personaggio = Personaggio.objects.create(
            nome="PG AIN",
            proprietario=self.user,
            tipologia=self.tipologia,
            campagna=self.campagna,
        )
        self.tratto_negativo = Abilita.objects.create(
            nome="Archetipo - Negativo",
            caratteristica=self.caratteristica,
            costo_pc=-1,
            costo_crediti=0,
            is_tratto_aura=True,
            aura_riferimento=self.aura_innata,
            livello_riferimento=1,
            campagna=self.campagna,
        )
        self.tratto_umano = Abilita.objects.create(
            nome="Archetipo - Umano",
            caratteristica=self.caratteristica,
            costo_pc=0,
            costo_crediti=0,
            is_tratto_aura=True,
            aura_riferimento=self.aura_innata,
            livello_riferimento=0,
            campagna=self.campagna,
        )

    @patch("personaggi.models.Personaggio.valida_acquisizione_abilita", return_value=(True, ""))
    def test_ain_trait_swap_applies_pc_delta_for_negative_and_zero_cost(self, _mock_valida):
        self.assertEqual(self.personaggio.punti_caratteristica, 8)

        r1 = self.client.post(
            "/api/personaggi/api/personaggio/me/acquisisci_abilita/",
            {"personaggio_id": self.personaggio.id, "abilita_id": self.tratto_negativo.id},
            format="json",
        )
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.personaggio.refresh_from_db()
        self.assertEqual(self.personaggio.punti_caratteristica, 9)

        r2 = self.client.post(
            "/api/personaggi/api/personaggio/me/acquisisci_abilita/",
            {"personaggio_id": self.personaggio.id, "abilita_id": self.tratto_umano.id},
            format="json",
        )
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.personaggio.refresh_from_db()
        self.assertEqual(self.personaggio.punti_caratteristica, 8)


class TessituraRuntimeTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="runtime-user", password="x")
        self.client.force_authenticate(user=self.user)
        self.pg = Personaggio.objects.create(nome="PG Runtime", proprietario=self.user)
        self.stat_rpg = Statistica.objects.create(nome="Rango Guscio Runtime", sigla="RGR", parametro="RGR")
        self.caratt = Punteggio.objects.create(nome="Forza Runtime", sigla="FRT", tipo=CARATTERISTICA)
        self.aura_runtime = Punteggio.objects.create(nome="Aura Runtime", sigla="ART", tipo="AU")

    def test_attiva_runtime_abilita_applica_modificatore_finche_attivo(self):
        abilita = Abilita.objects.create(
            nome="Aura Guard Runtime",
            caratteristica=self.caratt,
            costo_pc=0,
            costo_crediti=0,
        )
        AbilitaStatistica.objects.create(
            abilita=abilita,
            statistica=self.stat_rpg,
            tipo_modificatore=MODIFICATORE_ADDITIVO,
            valore=2,
        )
        tessitura = Tessitura.objects.create(
            nome="Tessitura Guard Runtime",
            aura_richiesta=self.aura_runtime,
            usa_effetto_temporaneo=True,
            abilita_temporanea=abilita,
            durata_effetto_secondi=120,
            formula="1d10",
        )
        self.pg.tessiture_possedute.add(tessitura)

        r = self.client.post(
            "/api/personaggi/api/game/attiva_tessitura_runtime/",
            {"char_id": self.pg.id, "tessitura_id": tessitura.id},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.pg.refresh_from_db()
        mods = self.pg.modificatori_calcolati
        self.assertIn("RGR", mods)
        self.assertGreaterEqual(mods["RGR"]["add"], 2.0)

    def test_runtime_esporta_descrizione_abilita_temporanea_senza_possesso(self):
        """L'abilita temporanea puo non essere in abilita_possedute: la descrizione va nel payload runtime."""
        from datetime import timedelta

        from django.utils import timezone

        abilita = Abilita.objects.create(
            nome="Potenziare descrizione runtime",
            descrizione="<p>Effetto temporaneo da tessitura</p>",
            caratteristica=self.caratt,
            costo_pc=0,
            costo_crediti=0,
        )
        tessitura = Tessitura.objects.create(
            nome="Tessitura descr runtime",
            aura_richiesta=self.aura_runtime,
            usa_effetto_temporaneo=True,
            abilita_temporanea=abilita,
            durata_effetto_secondi=60,
            formula="1d10",
        )
        self.assertFalse(self.pg.abilita_possedute.filter(pk=abilita.pk).exists())

        now = timezone.now()
        TessituraEffettoRuntime.objects.create(
            personaggio=self.pg,
            tessitura=tessitura,
            abilita_temporanea=abilita,
            inizio=now,
            fine=now + timedelta(seconds=60),
            is_attivo=True,
        )
        ser = PersonaggioDetailSerializer(self.pg)
        runtime_rows = ser.data.get("tessiture_attive_runtime") or []
        self.assertEqual(len(runtime_rows), 1)
        html = runtime_rows[0].get("abilita_temporanea_descrizione_html") or ""
        self.assertIn("Effetto temporaneo da tessitura", html)

    def test_attiva_runtime_slot_disequippa_oggetto_reale_stesso_slot(self):
        obj = Oggetto.objects.create(
            nome="Spada Runtime",
            tipo_oggetto="FIS",
            is_equipaggiato=True,
            slot_equip="melee",
        )
        OggettoInInventario.objects.create(oggetto=obj, inventario=self.pg.inventario_ptr)
        tessitura = Tessitura.objects.create(
            nome="Arma Arcana Runtime",
            aura_richiesta=self.aura_runtime,
            usa_effetto_temporaneo=True,
            durata_effetto_secondi=120,
            oggetto_runtime_config={
                "nome": "Lama Arcana Runtime",
                "slot_key": "melee",
                "modificatori": [{"stat_sigla": "RGR", "valore": 1, "tipo_modificatore": "ADD"}],
            },
            formula="1d10",
        )
        self.pg.tessiture_possedute.add(tessitura)
        r = self.client.post(
            "/api/personaggi/api/game/attiva_tessitura_runtime/",
            {"char_id": self.pg.id, "tessitura_id": tessitura.id},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        obj.refresh_from_db()
        self.assertFalse(obj.is_equipaggiato)
        self.assertIsNone(obj.slot_equip)
        runtime = TessituraEffettoRuntime.objects.filter(personaggio=self.pg, tessitura=tessitura, is_attivo=True).first()
        self.assertIsNotNone(runtime)
        self.assertTrue(runtime.oggetto_runtime.equipaggiato)

    def test_disequip_runtime_object_termina_effetto(self):
        tessitura = Tessitura.objects.create(
            nome="Arma Arcana Runtime",
            aura_richiesta=self.aura_runtime,
            usa_effetto_temporaneo=True,
            durata_effetto_secondi=120,
            oggetto_runtime_config={"nome": "Lama Arcana Runtime", "slot_key": "melee", "modificatori": []},
            formula="1d10",
        )
        self.pg.tessiture_possedute.add(tessitura)
        act = self.client.post(
            "/api/personaggi/api/game/attiva_tessitura_runtime/",
            {"char_id": self.pg.id, "tessitura_id": tessitura.id},
            format="json",
        )
        self.assertEqual(act.status_code, status.HTTP_200_OK)
        runtime_id = act.data["runtime"]["id"]
        runtime_obj_id = act.data["runtime"]["oggetto_runtime"]["id"]
        stop = self.client.post(
            "/api/personaggi/api/game/disequip_tessitura_runtime_object/",
            {"char_id": self.pg.id, "runtime_object_id": runtime_obj_id},
            format="json",
        )
        self.assertEqual(stop.status_code, status.HTTP_200_OK)
        rt = TessituraEffettoRuntime.objects.get(id=runtime_id)
        self.assertFalse(rt.is_attivo)
        self.assertEqual(rt.motivo_fine, "manual_disequip")

    @patch("personaggi.services.GestioneOggettiService.calcola_cog_utilizzata", return_value=1)
    @patch("personaggi.models.Personaggio.get_valore_statistica", return_value=1)
    def test_attiva_runtime_bloccata_se_cog_pieno(self, _mock_cog_max, _mock_cog_used):
        tessitura = Tessitura.objects.create(
            nome="Runtime COG Block",
            aura_richiesta=self.aura_runtime,
            usa_effetto_temporaneo=True,
            durata_effetto_secondi=60,
            formula="1d10",
        )
        self.pg.tessiture_possedute.add(tessitura)
        r = self.client.post(
            "/api/personaggi/api/game/attiva_tessitura_runtime/",
            {"char_id": self.pg.id, "tessitura_id": tessitura.id},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("COG", str(r.data))


class PersonaggioGameStateApiTests(APITestCase):
    """GET /api/personaggi/<pk>/game_state/ — snapshot per cache offline client."""

    def setUp(self):
        self.user = User.objects.create_user(username="gs-player", password="x")
        self.client.force_authenticate(user=self.user)
        self.kor35 = Campagna.objects.create(
            slug="kor35-gamestate-test",
            nome="Kor35 GameState Test",
            is_default=False,
            is_base=False,
            attiva=True,
        )
        CampagnaUtente.objects.create(campagna=self.kor35, user=self.user, ruolo="PLAYER", attivo=True)
        self.tipologia = TipologiaPersonaggio.objects.create(
            nome="Tipo GS",
            caratteristiche_iniziali=8,
            crediti_iniziali=0,
            giocante=True,
        )
        self.pg = Personaggio.objects.create(
            nome="PG GS",
            proprietario=self.user,
            tipologia=self.tipologia,
            campagna=self.kor35,
        )

    def test_game_state_owner_get_200_and_has_core_keys(self):
        url = f"/api/personaggi/api/personaggi/{self.pg.id}/game_state/"
        r = self.client.get(url, HTTP_X_CAMPAGNA=self.kor35.slug)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("snapshot_server_at", r.data)
        self.assertIn("statistiche_primarie", r.data)
        self.assertIn("oggetti", r.data)
        self.assertEqual(r.data.get("id"), self.pg.id)
        self.assertEqual(r.data.get("nome"), "PG GS")

    def test_game_state_forbidden_for_other_user(self):
        other = User.objects.create_user(username="other-gs", password="x")
        pg2 = Personaggio.objects.create(
            nome="PG Altro",
            proprietario=other,
            tipologia=self.tipologia,
            campagna=self.kor35,
        )
        url = f"/api/personaggi/api/personaggi/{pg2.id}/game_state/"
        r = self.client.get(url, HTTP_X_CAMPAGNA=self.kor35.slug)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class RisorsePoolUiVisibilityTests(APITestCase):
    """risorse_pool_ui: solo statistiche pool con massimo di scheda > 0."""

    def setUp(self):
        self.user = User.objects.create_user(username="pool-vis", password="x")
        self.pg = Personaggio.objects.create(nome="PG Pool", proprietario=self.user)
        self.stat_frt = Statistica.objects.create(
            nome="Fortuna Test",
            sigla="FRT",
            parametro="FRT",
            is_risorsa_pool=True,
        )
        self.stat_teo = Statistica.objects.create(
            nome="Teoforia Test",
            sigla="TEO",
            parametro="TEO",
            is_risorsa_pool=True,
            pool_corrente_default_pieno_se_assente=False,
        )
        self.stat_cap = Statistica.objects.create(
            nome="Cap Pool Test",
            sigla="CAP",
            parametro="CAP",
            is_risorsa_pool=True,
            massimo_pool_sigla="FRT",
        )
        pb = dict(self.pg.punteggi_base or {})
        pb[self.stat_frt.nome] = 2
        pb[self.stat_teo.nome] = 0
        pb[self.stat_cap.nome] = 0
        self.pg.punteggi_base = pb
        self.pg.save(update_fields=["punteggi_base", "updated_at"])

    def test_risorse_pool_ui_solo_massimo_scheda_positivo(self):
        ser = PersonaggioDetailSerializer()
        rows = ser.get_risorse_pool_ui(self.pg)
        sigle = {r["sigla"] for r in rows}
        self.assertIn("FRT", sigle)
        self.assertNotIn("TEO", sigle)
        self.assertNotIn("CAP", sigle)
        frt = next(r for r in rows if r["sigla"] == "FRT")
        self.assertEqual(frt["valore_max"], 2)


class EquipOggettoTecnologicoAteTests(TestCase):
    """ATE è un'aura (tipo AU), non una statistica ST: va letta con get_valore_aura_per_sigla."""

    def setUp(self):
        self.user = User.objects.create_user(username="equip-ate-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG ATE Equip", proprietario=self.user)
        self.aura_ate = Punteggio.objects.create(
            nome="Aura Tecnologica Equip Test",
            sigla="ATE",
            tipo=AURA,
        )
        self.caratt = Punteggio.objects.create(
            nome="Car Equip Test",
            sigla="CEQ",
            tipo=CARATTERISTICA,
        )
        self.abilita_ate = Abilita.objects.create(
            nome="Abilita ATE Equip",
            caratteristica=self.caratt,
            costo_pc=0,
            costo_crediti=0,
        )
        abilita_punteggio.objects.create(
            abilita=self.abilita_ate,
            punteggio=self.aura_ate,
            valore=1,
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.abilita_ate)
        self.template = OggettoBase.objects.create(
            nome="Template gadget",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            is_tecnologico=True,
        )
        self.oggetto = Oggetto.objects.create(
            nome="Gadget tecnologico",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            is_tecnologico=True,
            slot_fisici_possibili="melee",
            oggetto_base_generatore=self.template,
        )
        self.oggetto.sposta_in_inventario(self.pg)

    def test_ate_in_punteggi_base_non_usa_get_valore_statistica(self):
        self.assertGreaterEqual(self.pg.get_valore_aura_per_sigla("ATE"), 1)
        self.assertEqual(self.pg.get_valore_statistica("ATE"), 0)

    def test_equip_tecnologico_con_ate_uno(self):
        stato = GestioneOggettiService.equipaggia_oggetto(
            self.pg, self.oggetto, slot_key="melee"
        )
        self.assertEqual(stato, "Equipaggiato")
        self.oggetto.refresh_from_db()
        self.assertTrue(self.oggetto.is_equipaggiato)


class AbilitaBonusSlotEquipTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="slot-bonus-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Slot Bonus", proprietario=self.user)
        self.caratt = Punteggio.objects.create(nome="Car Slot", sigla="CSR", tipo=CARATTERISTICA)
        self.stat = Statistica.objects.create(nome="Difesa Slot", sigla="DFS", parametro="DFS")
        self.abilita = Abilita.objects.create(
            nome="Maestro equip",
            caratteristica=self.caratt,
            costo_pc=0,
            costo_crediti=0,
        )
        self.stat_link = AbilitaStatistica.objects.create(
            abilita=self.abilita,
            statistica=self.stat,
            tipo_modificatore=MODIFICATORE_ADDITIVO,
            valore=0,
            usa_bonus_slot_equip=True,
            slot_equip_ammessi=["melee", "fingers"],
            modalita_conteggio_slot_equip=SLOT_EQUIP_CONTEGGIO_OGNI_POTENZIAMENTO,
            valore_per_unita_slot_equip=1,
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.abilita)

        self.oggetto_melee = Oggetto.objects.create(
            nome="Spada test",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            slot_fisici_possibili="melee",
            oggetto_base_generatore=OggettoBase.objects.create(
                nome="Template spada",
                tipo_oggetto=TIPO_OGGETTO_FISICO,
            ),
        )
        self.oggetto_melee.sposta_in_inventario(self.pg)
        self.oggetto_melee.is_equipaggiato = True
        self.oggetto_melee.slot_equip = "melee"
        self.oggetto_melee.save(update_fields=["is_equipaggiato", "slot_equip", "updated_at"])

        self.oggetto_ring = Oggetto.objects.create(
            nome="Anello test",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            slot_fisici_possibili="fingers",
            oggetto_base_generatore=OggettoBase.objects.create(
                nome="Template anello",
                tipo_oggetto=TIPO_OGGETTO_FISICO,
            ),
        )
        self.oggetto_ring.sposta_in_inventario(self.pg)
        self.oggetto_ring.is_equipaggiato = True
        self.oggetto_ring.slot_equip = "fingers"
        self.oggetto_ring.save(update_fields=["is_equipaggiato", "slot_equip", "updated_at"])

        self.mod = Oggetto.objects.create(
            nome="Mod test",
            tipo_oggetto=TIPO_OGGETTO_MOD,
            cariche_attuali=3,
            ospitato_su=self.oggetto_melee,
        )

    def _set_modalita(self, modalita):
        self.stat_link.modalita_conteggio_slot_equip = modalita
        self.stat_link.save(update_fields=["modalita_conteggio_slot_equip", "updated_at"])

    def _bonus(self):
        if hasattr(self.pg, "_modificatori_calcolati_cache"):
            del self.pg._modificatori_calcolati_cache
        return self.pg.modificatori_calcolati.get("DFS", {}).get("add", 0)

    def test_senza_abilita_nessun_bonus(self):
        alt_pg = Personaggio.objects.create(nome="Alt PG", proprietario=self.user)
        oggetto = Oggetto.objects.create(
            nome="Spada alt",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            slot_fisici_possibili="melee",
            is_equipaggiato=True,
            slot_equip="melee",
        )
        oggetto.sposta_in_inventario(alt_pg)
        self.assertEqual(alt_pg.modificatori_calcolati.get("DFS", {}).get("add", 0), 0)

    def test_modalita_ogni_potenziamento(self):
        # 1 mod su melee
        self.assertEqual(self._bonus(), 1.0)

    def test_modalita_tutti_oggetti(self):
        self._set_modalita(SLOT_EQUIP_CONTEGGIO_TUTTI_OGGETTI)
        # 2 oggetti equip (melee + fingers), mod irrilevante
        self.assertEqual(self._bonus(), 2.0)

    def test_modalita_oggetti_modificati_un_solo_bonus_per_host(self):
        self._set_modalita(SLOT_EQUIP_CONTEGGIO_OGGETTI_MODIFICATI)
        Oggetto.objects.create(
            nome="Mod extra",
            tipo_oggetto=TIPO_OGGETTO_MOD,
            cariche_attuali=1,
            ospitato_su=self.oggetto_melee,
        )
        # solo spada modificata conta, non l'anello nudo
        self.assertEqual(self._bonus(), 1.0)

    def test_modalita_ogni_potenziamento_con_due_mod_sullo_stesso_host(self):
        Oggetto.objects.create(
            nome="Mod extra",
            tipo_oggetto=TIPO_OGGETTO_MOD,
            cariche_attuali=1,
            ospitato_su=self.oggetto_melee,
        )
        # 2 mod su melee
        self.assertEqual(self._bonus(), 2.0)

    def test_slot_non_selezionato_non_conta(self):
        self._set_modalita(SLOT_EQUIP_CONTEGGIO_TUTTI_OGGETTI)
        oggetto_vest = Oggetto.objects.create(
            nome="Veste test",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            slot_fisici_possibili="vest",
            is_equipaggiato=True,
            slot_equip="vest",
        )
        oggetto_vest.sposta_in_inventario(self.pg)
        self.assertEqual(self._bonus(), 2.0)

    def test_materia_conta_come_potenziamento(self):
        Oggetto.objects.create(
            nome="Materia test",
            tipo_oggetto=TIPO_OGGETTO_MATERIA,
            ospitato_su=self.oggetto_ring,
        )
        # 1 mod melee + 1 materia ring
        self.assertEqual(self._bonus(), 2.0)


class PersonaggioSoftDeleteTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="pg-owner", password="x")
        self.other = User.objects.create_user(username="pg-other", password="x")
        self.master = User.objects.create_user(username="pg-master", password="x")
        self.campagna = Campagna.objects.create(
            slug="kor35-softdel",
            nome="Kor35 SoftDel",
            is_default=False,
            is_base=False,
            attiva=True,
        )
        CampagnaUtente.objects.create(campagna=self.campagna, user=self.owner, ruolo="PLAYER", attivo=True)
        CampagnaUtente.objects.create(campagna=self.campagna, user=self.other, ruolo="PLAYER", attivo=True)
        CampagnaUtente.objects.create(campagna=self.campagna, user=self.master, ruolo="MASTER", attivo=True)
        self.tipologia = TipologiaPersonaggio.objects.create(nome="Tipo SoftDel", giocante=True)
        self.pg = Personaggio.objects.create(
            nome="PG SoftDel",
            proprietario=self.owner,
            tipologia=self.tipologia,
            campagna=self.campagna,
        )

    def test_owner_soft_delete_hides_from_list(self):
        self.client.force_authenticate(user=self.owner)
        url = f"/api/personaggi/api/gestione-personaggi/{self.pg.id}/"
        r = self.client.delete(url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT)
        self.pg.refresh_from_db()
        self.assertIsNotNone(self.pg.eliminato_at)
        self.assertFalse(Personaggio.objects.filter(pk=self.pg.pk).exists())
        self.assertTrue(Personaggio.all_objects.filter(pk=self.pg.pk, eliminato_at__isnull=False).exists())
        list_r = self.client.get("/api/personaggi/api/personaggi/", HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(list_r.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_r.data), 0)

    def test_other_player_cannot_delete(self):
        self.client.force_authenticate(user=self.other)
        url = f"/api/personaggi/api/gestione-personaggi/{self.pg.id}/"
        r = self.client.delete(url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertIn(r.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_master_can_restore_deleted(self):
        self.pg.eliminato_at = timezone.now()
        self.pg.save(update_fields=["eliminato_at", "updated_at"])
        self.client.force_authenticate(user=self.master)
        url = f"/api/personaggi/api/staff/personaggi-eliminati/{self.pg.id}/restore/"
        r = self.client.post(url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.pg.refresh_from_db()
        self.assertIsNone(self.pg.eliminato_at)
        self.assertTrue(Personaggio.objects.filter(pk=self.pg.pk).exists())

    def _archive_pg(self):
        self.pg.eliminato_at = timezone.now()
        self.pg.save(update_fields=["eliminato_at", "updated_at"])

    def _ids_from_list_response(self, data):
        if isinstance(data, list):
            return {row.get("id") for row in data}
        if isinstance(data, dict) and "results" in data:
            return {row.get("id") for row in data["results"]}
        return set()

    def test_archived_hidden_from_player_facing_lists(self):
        """Regressione: PG archiviato assente da tutte le liste giocatore, visibile solo in staff eliminati."""
        self._archive_pg()
        h = {"HTTP_X_CAMPAGNA": self.campagna.slug}

        self.client.force_authenticate(user=self.owner)
        endpoints = [
            "/api/personaggi/api/personaggi/",
            "/api/personaggi/api/gestione-personaggi/",
            f"/api/personaggi/api/personaggi/search/?q=SoftDel&current_char_id=",
        ]
        for path in endpoints:
            r = self.client.get(path, **h)
            self.assertEqual(r.status_code, status.HTTP_200_OK, msg=path)
            self.assertNotIn(
                self.pg.id,
                self._ids_from_list_response(r.data),
                msg=f"PG archiviato ancora in {path}",
            )

        detail = self.client.get(f"/api/personaggi/api/personaggi/{self.pg.id}/", **h)
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)

        self.client.force_authenticate(user=self.master)
        master_list = self.client.get("/api/personaggi/api/personaggi/?view_all=true", **h)
        self.assertEqual(master_list.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.pg.id, self._ids_from_list_response(master_list.data))

        staff_deleted = self.client.get("/api/personaggi/api/staff/personaggi-eliminati/", **h)
        self.assertEqual(staff_deleted.status_code, status.HTTP_200_OK)
        self.assertIn(self.pg.id, self._ids_from_list_response(staff_deleted.data))


class CostiAttivazioneTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="costi-user", password="x")
        self.client.force_authenticate(user=self.user)
        self.pg = Personaggio.objects.create(nome="PG Costi", proprietario=self.user)
        self.aura = Punteggio.objects.create(nome="Aura Costi", sigla="ACO", tipo=AURA)
        self.stat_cha = Statistica.objects.create(
            nome="Chakra test", sigla="CHA", parametro="CHA", is_risorsa_pool=True,
            valore_base_predefinito=5,
        )
        PersonaggioStatisticaBase.objects.create(
            personaggio=self.pg, statistica=self.stat_cha, valore_base=5,
        )
        self.stat_cog = Statistica.objects.create(
            nome="Cog test", sigla="COG", parametro="COG", valore_base_predefinito=3,
        )
        PersonaggioStatisticaBase.objects.create(
            personaggio=self.pg, statistica=self.stat_cog, valore_base=3,
        )
        self.pg.imposta_risorsa_pool_tattica("CHA", 5)
        self.pg.save(update_fields=["risorse_consumabili", "statistiche_temporanee", "updated_at"])

    def test_usa_oggetto_consuma_costo_attivazione(self):
        infusione = Infusione.objects.create(nome="Inf costi", aura_richiesta=self.aura, testo="x")
        InfusioneCostoAttivazione.objects.create(infusione=infusione, statistica=self.stat_cha, costo=2)
        oggetto = GestioneOggettiService.crea_oggetto_da_infusione(infusione, self.pg)
        oggetto.cariche_attuali = 3
        oggetto.save(update_fields=["cariche_attuali"])

        r = self.client.post(
            "/api/personaggi/api/game/usa_oggetto/",
            {"oggetto_id": oggetto.id, "char_id": self.pg.id},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.pg.refresh_from_db()
        oggetto.refresh_from_db()
        self.assertEqual(oggetto.cariche_attuali, 2)
        self.assertEqual(self.pg.get_risorsa_corrente("CHA"), 3)

    def test_attiva_tessitura_runtime_consuma_costo(self):
        tessitura = Tessitura.objects.create(
            nome="Tess costi",
            aura_richiesta=self.aura,
            usa_effetto_temporaneo=True,
            durata_effetto_secondi=60,
            formula="1",
        )
        TessituraCostoAttivazione.objects.create(tessitura=tessitura, statistica=self.stat_cha, costo=1)
        self.pg.tessiture_possedute.add(tessitura)

        r = self.client.post(
            "/api/personaggi/api/game/attiva_tessitura_runtime/",
            {"char_id": self.pg.id, "tessitura_id": tessitura.id},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.get_risorsa_corrente("CHA"), 4)


class OggettoBasePropagaIstanzeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="propaga-base-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Propaga", proprietario=self.user)
        self.stat_for = Statistica.objects.create(nome="Forza Prop", sigla="FPR", parametro="for_pr")
        self.template = OggettoBase.objects.create(
            nome="Spada listino",
            descrizione="Vecchia descrizione",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            attacco_base="Chop!",
            is_pesante=False,
        )
        OggettoBaseStatisticaBase.objects.create(
            oggetto_base=self.template,
            statistica=self.stat_for,
            valore_base=2,
        )
        self.istanza = Oggetto.objects.create(
            nome="Spada vecchia",
            testo="Testo obsoleto",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            attacco_base="Pierce!",
            costo_acquisto=99,
            is_equipaggiato=True,
            slot_equip="melee",
            cariche_attuali=3,
            oggetto_base_generatore=self.template,
        )
        self.istanza.sposta_in_inventario(self.pg)
        self.istanza_non_collegata = Oggetto.objects.create(
            nome="Oggetto custom",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
        )

    def test_applica_template_aggiorna_solo_istanze_collegate(self):
        from personaggi.services import GestioneCraftingService

        self.template.nome = "Spada listino v2"
        self.template.descrizione = "Nuova descrizione"
        self.template.attacco_base = "{formula_source}{danni_mischia}"
        self.template.is_pesante = True
        self.template.save()

        result = GestioneCraftingService.applica_template_a_istanze(self.template)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["updated"], 1)

        self.istanza.refresh_from_db()
        self.assertEqual(self.istanza.nome, "Spada listino v2")
        self.assertEqual(self.istanza.testo, "Nuova descrizione")
        self.assertEqual(self.istanza.attacco_base, "{formula_source}{danni_mischia}")
        self.assertTrue(self.istanza.is_pesante)
        self.assertEqual(self.istanza.costo_acquisto, 99)
        self.assertTrue(self.istanza.is_equipaggiato)
        self.assertEqual(self.istanza.slot_equip, "melee")
        self.assertEqual(self.istanza.cariche_attuali, 3)
        self.assertEqual(self.istanza.oggettostatisticabase_set.count(), 1)
        self.assertEqual(self.istanza.oggettostatisticabase_set.first().valore_base, 2)

        self.istanza_non_collegata.refresh_from_db()
        self.assertEqual(self.istanza_non_collegata.nome, "Oggetto custom")

    def test_staff_endpoint_propaga_istanze(self):
        from rest_framework.test import APIClient

        staff = User.objects.create_user(
            username="staff-propaga",
            password="x",
            is_staff=True,
            is_superuser=True,
        )
        client = APIClient()
        client.force_authenticate(user=staff)

        self.template.descrizione = "Via API"
        self.template.save()

        res = client.post(
            f"/api/personaggi/api/staff/oggetti-base/{self.template.id}/propaga-istanze/",
            {"dry_run": False},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data.get("updated"), 1)
        self.istanza.refresh_from_db()
        self.assertEqual(self.istanza.testo, "Via API")


class SoloOggettoOspitanteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="solo-obj-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Solo Obj", proprietario=self.user)
        self.stat_rango = Statistica.objects.create(
            nome="Rango Solo Oggetto",
            sigla="RGO",
            parametro="RGO",
        )
        self.spada = Oggetto.objects.create(
            nome="Spada solo-obj",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            attacco_base="{RGO|:RGO}",
            is_equipaggiato=True,
            slot_equip="melee",
            slot_fisici_possibili="melee",
        )
        self.spada.sposta_in_inventario(self.pg)
        OggettoStatisticaBase.objects.create(
            oggetto=self.spada,
            statistica=self.stat_rango,
            valore_base=1,
        )
        self.mod = Oggetto.objects.create(
            nome="Mod solo-obj",
            tipo_oggetto=TIPO_OGGETTO_MOD,
            cariche_attuali=1,
            ospitato_su=self.spada,
        )

    def _clear_mods_cache(self):
        if hasattr(self.pg, "_modificatori_calcolati_cache"):
            del self.pg._modificatori_calcolati_cache

    def test_mod_solo_oggetto_escluso_da_modificatori_globali(self):
        OggettoStatistica.objects.create(
            oggetto=self.mod,
            statistica=self.stat_rango,
            valore=2,
            tipo_modificatore=MODIFICATORE_ADDITIVO,
            solo_oggetto_ospitante=True,
        )
        self._clear_mods_cache()
        mods = self.pg.modificatori_calcolati
        self.assertEqual(mods.get("RGO", {}).get("add", 0), 0)

    def test_mod_globale_incluso_nei_modificatori_pg(self):
        OggettoStatistica.objects.create(
            oggetto=self.mod,
            statistica=self.stat_rango,
            valore=2,
            tipo_modificatore=MODIFICATORE_ADDITIVO,
            solo_oggetto_ospitante=False,
        )
        self._clear_mods_cache()
        mods = self.pg.modificatori_calcolati
        self.assertEqual(mods.get("RGO", {}).get("add", 0), 2.0)

    def test_mod_solo_oggetto_applicato_in_formula_attacco_host(self):
        OggettoStatistica.objects.create(
            oggetto=self.mod,
            statistica=self.stat_rango,
            valore=2,
            tipo_modificatore=MODIFICATORE_ADDITIVO,
            solo_oggetto_ospitante=True,
        )
        item_mods = raccogli_modificatori_solo_oggetto(self.spada)
        self.assertEqual(len(item_mods), 1)

        formula = formatta_testo_generico(
            None,
            formula=self.spada.attacco_base,
            statistiche_base=self.spada.oggettostatisticabase_set.select_related("statistica").all(),
            personaggio=self.pg,
            context={
                "item_modifiers": item_mods,
                "formula_kind": "ATT",
                "attack_formula_template": self.spada.attacco_base,
            },
            solo_formula=True,
        )
        self.assertIn("3", formula)

        ser = OggettoSerializer(self.spada, context={"personaggio": self.pg})
        attacco = ser.get_attacco_formattato(self.spada)
        self.assertIn("3", attacco)


class PersonaggioStaffRetrieveTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff_pg_hub", password="x", is_staff=True, is_superuser=True
        )
        self.client.force_authenticate(user=self.staff)
        self.tipo = TipologiaPersonaggio.objects.create(nome="PG", giocante=True)
        self.pg = Personaggio.objects.create(nome="PG Eventi", tipologia=self.tipo)

    def test_retrieve_con_eventi_partecipati(self):
        from gestione_plot.models import Evento

        now = timezone.now()
        ev = Evento.objects.create(
            titolo="Raduno bosco",
            data_inizio=now,
            data_fine=now + timezone.timedelta(hours=8),
        )
        ev.partecipanti.add(self.pg)

        url = f"/api/personaggi/api/staff/personaggi/{self.pg.id}/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        eventi = res.json().get("eventi_partecipati") or []
        self.assertEqual(len(eventi), 1)
        self.assertEqual(eventi[0]["titolo"], "Raduno bosco")

    def test_patch_foto_costume_staff(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        url = f"/api/personaggi/api/staff/personaggi/{self.pg.id}/"
        buf = BytesIO()
        Image.new("RGB", (32, 48), color=(180, 120, 90)).save(buf, format="JPEG")
        upload = SimpleUploadedFile("trucco.jpg", buf.getvalue(), content_type="image/jpeg")
        res = self.client.patch(url, {"foto_trucco": upload}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        self.assertTrue(res.json().get("foto_trucco_url"))

        res_clear = self.client.patch(
            url,
            {"clear_foto_trucco": "1"},
            format="multipart",
        )
        self.assertEqual(res_clear.status_code, status.HTTP_200_OK, res_clear.content)
        self.assertFalse(res_clear.json().get("foto_trucco_url"))


class MetatalentiDecimalValoreTests(TestCase):
    """Regression: MattoneStatistica.valore è Decimal dopo migrazione 0220."""

    def test_tessitura_con_metatalento_decimal_non_esplode_in_detail_serializer(self):
        from decimal import Decimal

        from .models import (
            META_VALORE_PUNTEGGIO,
            Mattone,
            MattoneStatistica,
            ModelloAura,
            PersonaggioModelloAura,
        )

        user = User.objects.create_user(username="meta-dec-user", password="x")
        pg = Personaggio.objects.create(nome="PG Meta Dec", proprietario=user)

        aura = Punteggio.objects.create(nome="Aura Meta Test", sigla="AMT", tipo=AURA)
        caratt = Punteggio.objects.create(nome="Car Meta", sigla="CMT", tipo=CARATTERISTICA)
        stat = Statistica.objects.create(nome="Stat Meta", sigla="SMT", parametro="smt_meta")

        abilita = Abilita.objects.create(
            nome="Ab Meta",
            caratteristica=caratt,
            costo_pc=0,
            costo_crediti=0,
        )
        abilita_punteggio.objects.create(abilita=abilita, punteggio=caratt, valore=3)
        pg.abilita_possedute.add(abilita)

        mattone = Mattone.objects.create(
            nome="Mattone Meta Dec",
            aura=aura,
            caratteristica_associata=caratt,
            funzionamento_metatalento=META_VALORE_PUNTEGGIO,
        )
        MattoneStatistica.objects.create(
            mattone=mattone,
            statistica=stat,
            valore=Decimal("1.50"),
            tipo_modificatore=MODIFICATORE_ADDITIVO,
        )

        modello = ModelloAura.objects.create(aura=aura, nome="Modello Meta Dec")
        modello.mattoni_proibiti.add(mattone)
        PersonaggioModelloAura.objects.create(personaggio=pg, modello_aura=modello)

        tessitura = Tessitura.objects.create(
            nome="Tess Meta Dec",
            aura_richiesta=aura,
            testo="Testo metatalento",
            formula="1",
        )
        pg.tessiture_possedute.add(tessitura)

        rows = PersonaggioDetailSerializer(pg).get_tessiture_possedute(pg)
        self.assertEqual(len(rows), 1)
        self.assertIn("testo_formattato_personaggio", rows[0])


class PhysicalSlotCapacityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="slot-cap-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Slot Cap", proprietario=self.user)
        self.caratt = Punteggio.objects.create(nome="Car Slot Cap", sigla="CSC", tipo=CARATTERISTICA)
        self.stat_slm = Statistica.objects.create(
            nome="Slot Armi Mischia",
            sigla="SLM",
            parametro="slot_mel",
            is_primaria=False,
        )
        self.abilita = Abilita.objects.create(
            nome="Dual wield",
            caratteristica=self.caratt,
            costo_pc=0,
            costo_crediti=0,
        )
        AbilitaStatistica.objects.create(
            abilita=self.abilita,
            statistica=self.stat_slm,
            tipo_modificatore=MODIFICATORE_ADDITIVO,
            valore=2,
        )
        from .models import PersonaggioAbilita

        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.abilita)

    def test_slot_capacity_uses_non_primary_stat(self):
        caps = GestioneOggettiService.build_physical_slot_capacities(self.pg)
        self.assertEqual(caps["melee"], 2)
        self.assertEqual(caps["fingers"], 2)

    def test_detail_serializer_exposes_slot_capacities(self):
        data = PersonaggioDetailSerializer(self.pg).data
        self.assertEqual(data["slot_capacities"]["melee"], 2)
