"""Test accesso moduli campagna (OFF / TEST / OPEN)."""
from django.contrib.auth.models import User
from django.test import TestCase

from personaggi.campagna_moduli import (
    MODULO_ACCESSO_OFF,
    MODULO_ACCESSO_OPEN,
    MODULO_ACCESSO_TEST,
    MODULO_CARTE,
    MODULO_TASKS,
    apply_moduli_accesso,
    get_modulo_accesso,
    personaggio_puo_accedere_modulo,
    staff_tool_abilitato,
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
