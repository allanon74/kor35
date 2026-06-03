from django.contrib.auth.models import User
from django.test import TestCase
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
    Oggetto,
    OggettoBase,
    OggettoInInventario,
    Personaggio,
    PersonaggioAbilita,
    Punteggio,
    Statistica,
    Tessitura,
    TessituraEffettoRuntime,
    TipologiaPersonaggio,
    TIPO_OGGETTO_FISICO,
    abilita_punteggio,
    CARATTERISTICA,
)
from .serializers import PersonaggioDetailSerializer
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
