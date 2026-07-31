"""Test accesso moduli campagna (OFF / TEST / OPEN)."""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from personaggi.campagna_moduli import (
    CAMPAGNA_MODULI_REGISTRY,
    MODULO_ACCESSO_DEFAULT,
    MODULO_ACCESSO_OFF,
    MODULO_ACCESSO_OPEN,
    MODULO_ACCESSO_TEST,
    MODULO_CARTE,
    MODULO_CREAZIONE_GUIDATA,
    MODULO_NEGOZI,
    MODULO_PILOTAGGIO,
    MODULO_SCOMMESSE,
    MODULO_SOCIAL,
    MODULO_TASKS,
    STAFF_TOOL_TO_MODULO,
    apply_moduli_accesso,
    get_modulo_accesso,
    has_explicit_modulo,
    normalize_moduli_accesso,
    personaggio_puo_accedere_modulo,
    staff_tool_abilitato,
    user_puo_accedere_modulo,
    validate_moduli_accesso_payload,
)
from personaggi.carte_collezionabili_models import (
    CARTE_ACCESSO_OPEN,
    CARTE_ACCESSO_TEST,
    ConfigurazioneCarteCollezionabili,
)
from personaggi.carte_collezionabili_service import get_carte_accesso_modo
from personaggi.models import (
    CAMPAGNA_ROLE_PLAYER,
    CAMPAGNA_ROLE_STAFFER,
    Campagna,
    CampagnaUtente,
    Personaggio,
    TipologiaPersonaggio,
)


class CampagnaModuliAccessoTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(
            slug="test-moduli",
            nome="Test Moduli",
            attiva=True,
        )
        self.player = User.objects.create_user("player_moduli", password="x")
        self.staff_user = User.objects.create_user("staff_moduli", password="x")
        CampagnaUtente.objects.create(
            campagna=self.campagna,
            user=self.player,
            ruolo=CAMPAGNA_ROLE_PLAYER,
            attivo=True,
        )
        CampagnaUtente.objects.create(
            campagna=self.campagna,
            user=self.staff_user,
            ruolo=CAMPAGNA_ROLE_STAFFER,
            attivo=True,
        )
        self.tip_giocante = TipologiaPersonaggio.objects.create(
            nome="Giocante moduli test",
            giocante=True,
        )
        self.tip_png = TipologiaPersonaggio.objects.create(
            nome="PnG moduli test",
            giocante=False,
        )
        self.pg_player = Personaggio.objects.create(
            nome="PG Player",
            proprietario=self.player,
            campagna=self.campagna,
            tipologia=self.tip_giocante,
        )
        self.pg_staff = Personaggio.objects.create(
            nome="PG Staff",
            proprietario=self.staff_user,
            campagna=self.campagna,
            tipologia=self.tip_giocante,
        )
        self.pg_png = Personaggio.objects.create(
            nome="PNG",
            proprietario=self.player,
            campagna=self.campagna,
            tipologia=self.tip_png,
        )

    def test_default_tasks_off(self):
        self.assertEqual(get_modulo_accesso(self.campagna, MODULO_TASKS), MODULO_ACCESSO_OFF)
        self.assertFalse(personaggio_puo_accedere_modulo(self.pg_player, MODULO_TASKS))
        self.assertFalse(staff_tool_abilitato(self.campagna, "tasks"))

    def test_tasks_open(self):
        apply_moduli_accesso(self.campagna, {MODULO_TASKS: MODULO_ACCESSO_OPEN})
        self.campagna.refresh_from_db()
        self.assertTrue(personaggio_puo_accedere_modulo(self.pg_player, MODULO_TASKS))
        self.assertTrue(staff_tool_abilitato(self.campagna, "tasks"))

    def test_tasks_test_solo_staff(self):
        apply_moduli_accesso(self.campagna, {MODULO_TASKS: MODULO_ACCESSO_TEST})
        self.campagna.refresh_from_db()
        self.assertFalse(personaggio_puo_accedere_modulo(self.pg_player, MODULO_TASKS))
        self.assertTrue(personaggio_puo_accedere_modulo(self.pg_staff, MODULO_TASKS))
        self.assertTrue(personaggio_puo_accedere_modulo(self.pg_png, MODULO_TASKS))
        self.assertTrue(staff_tool_abilitato(self.campagna, "tasks"))

    def test_carte_bridge_from_config(self):
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna,
            accesso_modo=CARTE_ACCESSO_TEST,
            abilitata=False,
        )
        self.assertEqual(get_modulo_accesso(self.campagna, MODULO_CARTE), CARTE_ACCESSO_TEST)
        self.assertEqual(get_carte_accesso_modo(self.campagna), CARTE_ACCESSO_TEST)

    def test_carte_sync_from_moduli(self):
        apply_moduli_accesso(self.campagna, {MODULO_CARTE: MODULO_ACCESSO_OPEN})
        self.campagna.refresh_from_db()
        cfg = ConfigurazioneCarteCollezionabili.objects.get(campagna=self.campagna)
        self.assertEqual(cfg.accesso_modo, CARTE_ACCESSO_OPEN)
        self.assertEqual(get_carte_accesso_modo(self.campagna), CARTE_ACCESSO_OPEN)

    def test_reset_default_rimuove_override(self):
        apply_moduli_accesso(self.campagna, {MODULO_SCOMMESSE: MODULO_ACCESSO_OFF})
        self.campagna.refresh_from_db()
        self.assertTrue(has_explicit_modulo(self.campagna, MODULO_SCOMMESSE))

        apply_moduli_accesso(self.campagna, {MODULO_SCOMMESSE: MODULO_ACCESSO_DEFAULT})
        self.campagna.refresh_from_db()
        self.assertFalse(has_explicit_modulo(self.campagna, MODULO_SCOMMESSE))
        self.assertEqual(get_modulo_accesso(self.campagna, MODULO_SCOMMESSE), MODULO_ACCESSO_OPEN)

    def test_reset_default_carte_torna_al_bridge_config(self):
        apply_moduli_accesso(self.campagna, {MODULO_CARTE: MODULO_ACCESSO_OPEN})
        self.campagna.refresh_from_db()
        cfg = ConfigurazioneCarteCollezionabili.objects.get(campagna=self.campagna)
        cfg.accesso_modo = CARTE_ACCESSO_TEST
        cfg.abilitata = True
        cfg.save(update_fields=["accesso_modo", "abilitata", "updated_at"])

        apply_moduli_accesso(self.campagna, {MODULO_CARTE: None})
        self.campagna.refresh_from_db()
        self.assertFalse(has_explicit_modulo(self.campagna, MODULO_CARTE))
        self.assertEqual(get_modulo_accesso(self.campagna, MODULO_CARTE), CARTE_ACCESSO_TEST)

    def test_validate_payload_errori(self):
        with self.assertRaises(ValidationError):
            validate_moduli_accesso_payload({"modulo_inesistente": MODULO_ACCESSO_OPEN})
        with self.assertRaises(ValidationError):
            validate_moduli_accesso_payload({MODULO_TASKS: "FORSE"})
        with self.assertRaises(ValidationError):
            validate_moduli_accesso_payload(["tasks"])
        self.assertEqual(
            validate_moduli_accesso_payload({MODULO_TASKS: "open"}),
            {MODULO_TASKS: MODULO_ACCESSO_OPEN},
        )
        self.assertEqual(validate_moduli_accesso_payload({MODULO_TASKS: ""}), {MODULO_TASKS: None})

    def test_normalize_copre_tutto_il_registry(self):
        mappa = normalize_moduli_accesso(self.campagna)
        self.assertEqual(set(mappa), {row["key"] for row in CAMPAGNA_MODULI_REGISTRY})

    def test_staff_tool_mapping_completo(self):
        """Ogni tool staff mappato risponde al gate del modulo corrispondente."""
        for tool_id, key in STAFF_TOOL_TO_MODULO.items():
            apply_moduli_accesso(self.campagna, {key: MODULO_ACCESSO_OFF})
            self.campagna.refresh_from_db()
            self.assertFalse(staff_tool_abilitato(self.campagna, tool_id), msg=tool_id)

            apply_moduli_accesso(self.campagna, {key: MODULO_ACCESSO_TEST})
            self.campagna.refresh_from_db()
            self.assertTrue(staff_tool_abilitato(self.campagna, tool_id), msg=tool_id)

    def test_staff_tool_non_mappato_sempre_abilitato(self):
        self.assertTrue(staff_tool_abilitato(self.campagna, "campagne"))

    def test_user_puo_accedere_modulo_creazione_guidata(self):
        apply_moduli_accesso(self.campagna, {MODULO_CREAZIONE_GUIDATA: MODULO_ACCESSO_TEST})
        self.campagna.refresh_from_db()
        self.assertFalse(
            user_puo_accedere_modulo(self.player, self.campagna, MODULO_CREAZIONE_GUIDATA)
        )
        self.assertTrue(
            user_puo_accedere_modulo(self.staff_user, self.campagna, MODULO_CREAZIONE_GUIDATA)
        )

        apply_moduli_accesso(self.campagna, {MODULO_CREAZIONE_GUIDATA: MODULO_ACCESSO_OFF})
        self.campagna.refresh_from_db()
        self.assertFalse(
            user_puo_accedere_modulo(self.staff_user, self.campagna, MODULO_CREAZIONE_GUIDATA)
        )


class CampagnaModuliStaffApiTests(TestCase):
    """API staff campagne: lettura registry/raw e scrittura con reset ai default."""

    def setUp(self):
        self.campagna = Campagna.objects.create(
            slug="test-moduli-staff",
            nome="Test Moduli Staff",
            attiva=True,
        )
        self.admin = User.objects.create_superuser("admin_moduli", "a@test.local", "x")
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)
        self.url = f"/api/personaggi/api/staff/campagne/{self.campagna.id}/"

    def test_get_espone_effettivi_raw_e_registry(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["moduli_accesso_raw"], {})
        self.assertEqual(res.data["moduli_accesso"][MODULO_TASKS], MODULO_ACCESSO_OFF)
        keys = {row["key"] for row in res.data["moduli_accesso_registry"]}
        self.assertEqual(keys, {row["key"] for row in CAMPAGNA_MODULI_REGISTRY})

    def test_patch_merge_e_reset_default(self):
        res = self.client.patch(
            self.url,
            {"moduli_accesso": {MODULO_TASKS: MODULO_ACCESSO_TEST}},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["moduli_accesso_raw"], {MODULO_TASKS: MODULO_ACCESSO_TEST})

        reset = self.client.patch(
            self.url,
            {"moduli_accesso": {MODULO_TASKS: MODULO_ACCESSO_DEFAULT}},
            format="json",
        )
        self.assertEqual(reset.status_code, 200, reset.data)
        self.assertEqual(reset.data["moduli_accesso_raw"], {})
        self.assertEqual(reset.data["moduli_accesso"][MODULO_TASKS], MODULO_ACCESSO_OFF)

    def test_patch_valore_non_valido_400(self):
        res = self.client.patch(
            self.url,
            {"moduli_accesso": {MODULO_TASKS: "FORSE"}},
            format="json",
        )
        self.assertEqual(res.status_code, 400)


class CampagnaModuliApiGateTests(TestCase):
    """Gate lato API: con modulo OFF gli endpoint giocatore rispondono 403."""

    def setUp(self):
        self.campagna = Campagna.objects.create(
            slug="test-moduli-api",
            nome="Test Moduli API",
            attiva=True,
        )
        self.user = User.objects.create_user("player_moduli_api", password="x")
        CampagnaUtente.objects.create(
            campagna=self.campagna,
            user=self.user,
            ruolo=CAMPAGNA_ROLE_PLAYER,
            attivo=True,
        )
        self.tipologia = TipologiaPersonaggio.objects.create(
            nome="Giocante moduli api",
            giocante=True,
        )
        self.pg = Personaggio.objects.create(
            nome="PG Api",
            proprietario=self.user,
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _off(self, key):
        apply_moduli_accesso(self.campagna, {key: MODULO_ACCESSO_OFF})
        self.campagna.refresh_from_db()

    def test_scommesse_off_blocca_mie_puntate(self):
        url = f"/api/personaggi/api/scommesse/mie-puntate/?personaggio_id={self.pg.id}"
        self.assertEqual(self.client.get(url).status_code, 200)
        self._off(MODULO_SCOMMESSE)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_negozi_off_blocca_corporativi(self):
        url = f"/api/personaggi/api/negozi-mercante/corporativi/?char_id={self.pg.id}"
        self.assertEqual(self.client.get(url).status_code, 200)
        self._off(MODULO_NEGOZI)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_social_off_blocca_feed(self):
        url = f"/api/social/posts/?personaggio_id={self.pg.id}"
        self.assertEqual(self.client.get(url).status_code, 200)
        self._off(MODULO_SOCIAL)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_pilotaggio_off_blocca_stiva(self):
        url = f"/api/pilot/stiva/?personaggio_id={self.pg.id}"
        self._off(MODULO_PILOTAGGIO)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_tasks_off_blocca_missioni_mie(self):
        url = f"/api/plot/api/missioni/mie/?personaggio={self.pg.id}"
        res = self.client.get(url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(res.status_code, 403)

        apply_moduli_accesso(self.campagna, {MODULO_TASKS: MODULO_ACCESSO_OPEN})
        self.campagna.refresh_from_db()
        res_ok = self.client.get(url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(res_ok.status_code, 200)
