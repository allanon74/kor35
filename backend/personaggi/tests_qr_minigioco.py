"""Test logica minigioco QR."""
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from personaggi.models import MinigiocoQrConfig, MinigiocoQrSession, QrCode, TipologiaPersonaggio, Personaggio
from personaggi.qr_minigioco import (
    generate_game_state,
    generate_sliding_state,
    verify_memory,
    verify_rotate,
    verify_sliding,
    verify_solution,
    scegli_tipo_e_difficolta,
    tipi_pool,
    risolvi_difficolta,
    deve_saltare_minigioco,
    minigioco_ha_immagine_disponibile,
    risolvi_immagine_sessione,
    MINIGIOCO_TIPO_MEMORY,
    MINIGIOCO_TIPO_ROTATE,
    MINIGIOCO_TIPO_SIMON,
    MINIGIOCO_TIPO_PATTERN,
    MINIGIOCO_TIPO_PIPE,
    generate_game_state,
    verify_simon,
    verify_pattern_lock,
    verify_pipe_connect,
    tipi_pool_giocabili,
    MINIGIOCO_TIPO_SLIDING,
    ha_sblocco_minigioco,
    session_allows_bypass,
    SESSIONE_COMPLETATO,
    SESSIONE_SCADUTO_ATTIVA,
    BYPASS_TRANSITO_SECONDI,
)


class _Cfg:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _Pg:
    def __init__(self, stats=None, auras=None):
        self._stats = stats or {}
        self._auras = auras or {}

    def get_valore_statistica(self, sigla):
        return int(self._stats.get(str(sigla).upper(), 0))

    def get_valore_aura_effettivo(self, punteggio):
        nome = getattr(punteggio, "nome", punteggio)
        return int(self._auras.get(nome, 0))


class QrMinigiocoLogicTests(SimpleTestCase):
    def test_sliding_solved_state(self):
        tiles = list(range(16))
        self.assertTrue(verify_sliding(tiles, 4))

    def test_sliding_shuffle_is_solvable_path(self):
        tiles = generate_sliding_state(3, 42)
        self.assertEqual(len(tiles), 9)
        self.assertNotEqual(tiles, list(range(9)))

    def test_rotate_solved(self):
        self.assertTrue(verify_rotate([0, 0, 0, 0], 2))

    def test_memory_solved(self):
        self.assertTrue(verify_memory([0, 0, 1, 1], [0, 1, 2, 3], 2, 2))

    def test_verify_solution_integration(self):
        state = generate_game_state(MINIGIOCO_TIPO_ROTATE, 2, 7)
        solved = {"rotations": [0] * (state["size"] ** 2)}
        self.assertTrue(verify_solution(MINIGIOCO_TIPO_ROTATE, 2, solved))

    def test_memory_game_state_even_cells(self):
        state = generate_game_state(MINIGIOCO_TIPO_MEMORY, 2, 99)
        self.assertEqual(len(state["cards"]), 12)

    def test_sliding_full_solution(self):
        size = 3
        solved = {"tiles": list(range(size * size))}
        self.assertTrue(verify_solution(MINIGIOCO_TIPO_SLIDING, 2, solved))

    @patch("personaggi.qr_minigioco.minigioco_ha_immagine_disponibile", return_value=True)
    def test_scegli_tipo_e_difficolta_deterministico(self, _mock_img):
        cfg = _Cfg(
            tipi_abilitati=[MINIGIOCO_TIPO_SLIDING, MINIGIOCO_TIPO_MEMORY, MINIGIOCO_TIPO_ROTATE],
            difficolta=4,
            regole_difficolta=[],
        )
        pg = _Pg(stats={"PV": 1})
        t1, d1 = scegli_tipo_e_difficolta(cfg, 12345, personaggio=pg)
        t2, d2 = scegli_tipo_e_difficolta(cfg, 12345, personaggio=pg)
        self.assertEqual((t1, d1), (t2, d2))
        self.assertIn(t1, (MINIGIOCO_TIPO_SLIDING, MINIGIOCO_TIPO_MEMORY, MINIGIOCO_TIPO_ROTATE))
        self.assertEqual(d1, 4)

    def test_tipi_pool_default_tutti(self):
        cfg = _Cfg(tipi_abilitati=[], tipo=MINIGIOCO_TIPO_SLIDING)
        self.assertEqual(len(tipi_pool(cfg)), 1)
        cfg2 = _Cfg(tipi_abilitati=[MINIGIOCO_TIPO_MEMORY, MINIGIOCO_TIPO_ROTATE])
        self.assertEqual(tipi_pool(cfg2), [MINIGIOCO_TIPO_MEMORY, MINIGIOCO_TIPO_ROTATE])

    def test_risolvi_difficolta_default(self):
        cfg = _Cfg(difficolta=4, regole_difficolta=[])
        self.assertEqual(risolvi_difficolta(_Pg(), cfg), 4)

    @patch("personaggi.models.Punteggio.objects.filter")
    def test_risolvi_difficolta_aura(self, mock_punteggio_filter):
        mock_p = MagicMock()
        mock_p.nome = "Magica"
        mock_punteggio_filter.return_value.first.return_value = mock_p
        cfg = _Cfg(
            difficolta=4,
            regole_difficolta=[
                {
                    "operator": "AND",
                    "requisiti": [{"tipo": "punteggio", "nome": "Magica", "min": 1}],
                    "difficolta": 3,
                },
            ],
        )
        self.assertEqual(risolvi_difficolta(_Pg(auras={"Magica": 2}), cfg), 3)
        self.assertEqual(risolvi_difficolta(_Pg(auras={"Magica": 0}), cfg), 4)

    @patch("personaggi.models.Statistica.objects.filter")
    def test_risolvi_difficolta_regole_min(self, mock_stat):
        mock_stat.return_value.first.return_value = None
        cfg = _Cfg(
            difficolta=4,
            regole_difficolta=[
                {
                    "operator": "AND",
                    "requisiti": [{"tipo": "statistica", "sigla": "PV", "min": 1}],
                    "difficolta": 3,
                },
                {
                    "operator": "AND",
                    "requisiti": [{"tipo": "statistica", "sigla": "PV", "min": 3}],
                    "difficolta": 2,
                },
            ],
        )
        self.assertEqual(risolvi_difficolta(_Pg(stats={"PV": 1}), cfg), 3)
        self.assertEqual(risolvi_difficolta(_Pg(stats={"PV": 5}), cfg), 2)

    @patch("personaggi.models.Statistica.objects.filter")
    def test_deve_saltare_pv_alto(self, mock_stat):
        mock_stat.return_value.first.return_value = None
        cfg = _Cfg(
            esclusioni_minigioco=[
                {
                    "operator": "AND",
                    "requisiti": [{"tipo": "statistica", "sigla": "PV", "min": 6}],
                }
            ]
        )
        self.assertTrue(deve_saltare_minigioco(_Pg(stats={"PV": 6}), cfg))
        self.assertFalse(deve_saltare_minigioco(_Pg(stats={"PV": 5}), cfg))

    def test_minigioco_ha_immagine_custom(self):
        cfg = _Cfg(immagine=True, usa_biblioteca_se_vuota=True)
        self.assertTrue(minigioco_ha_immagine_disponibile(cfg))

    @patch("personaggi.minigioco_biblioteca.biblioteca_immagine_count", return_value=5)
    def test_minigioco_ha_immagine_da_biblioteca(self, _mock_count):
        cfg = _Cfg(immagine=None, usa_biblioteca_se_vuota=True)
        self.assertTrue(minigioco_ha_immagine_disponibile(cfg))

    @patch("personaggi.minigioco_biblioteca.biblioteca_immagine_count", return_value=0)
    def test_minigioco_senza_immagine_né_biblioteca(self, _mock_count):
        cfg = _Cfg(immagine=None, usa_biblioteca_se_vuota=True)
        self.assertFalse(minigioco_ha_immagine_disponibile(cfg))

    def test_risolvi_immagine_custom_prima_di_biblioteca(self):
        img = MagicMock()
        img.url = "/media/custom.jpg"
        cfg = _Cfg(immagine=img)
        url, bib = risolvi_immagine_sessione(cfg, seed=42)
        self.assertEqual(url, "/media/custom.jpg")
        self.assertIsNone(bib)

    @patch("personaggi.minigioco_biblioteca.scegli_immagine_biblioteca")
    @patch("personaggi.minigioco_biblioteca.immagine_biblioteca_url", return_value="/media/bib.jpg")
    def test_risolvi_immagine_da_biblioteca(self, _mock_url, mock_scegli):
        row = MagicMock()
        mock_scegli.return_value = row
        cfg = _Cfg(immagine=None, usa_biblioteca_se_vuota=True)
        url, bib = risolvi_immagine_sessione(cfg, seed=99)
        self.assertEqual(url, "/media/bib.jpg")
        self.assertIs(bib, row)
        mock_scegli.assert_called_once_with(99)


class MinigiocoBibliotecaTests(TestCase):
    @patch("personaggi.minigioco_biblioteca._download_image")
    @patch("personaggi.minigioco_biblioteca._fetch_wikimedia_page")
    @patch("personaggi.minigioco_biblioteca._fetch_openverse_page")
    def test_raccogli_fallback_wikimedia_se_openverse_vuoto(self, mock_ov, mock_wm, mock_dl):
        from personaggi.minigioco_biblioteca import _raccogli_immagini

        mock_ov.return_value = ([], "HTTPError: 403 Forbidden")
        mock_wm.return_value = (
            [
                {
                    "url": "https://upload.wikimedia.org/example.jpg",
                    "title": "Esempio",
                    "creator": "Autore",
                    "license": "CC BY 4.0",
                    "id": "123",
                    "foreign_landing_url": "https://commons.wikimedia.org/wiki/File:Esempio.jpg",
                }
            ],
            None,
        )
        mock_dl.return_value = b"x" * 3000

        prepared, _errors, ov_err, wm_err, sources = _raccogli_immagini(target=1)

        self.assertEqual(len(prepared), 1)
        self.assertEqual(prepared[0]["fonte"], "wikimedia")
        self.assertEqual(sources, ["wikimedia"])
        self.assertTrue(ov_err)
        self.assertFalse(wm_err)
        mock_wm.assert_called()

    def test_license_ok_esclude_nc_nd(self):
        from personaggi.minigioco_biblioteca import _license_ok_for_minigioco

        self.assertTrue(_license_ok_for_minigioco("CC BY 4.0"))
        self.assertTrue(_license_ok_for_minigioco("CC0 1.0"))
        self.assertFalse(_license_ok_for_minigioco("CC BY-NC 4.0"))
        self.assertFalse(_license_ok_for_minigioco("CC BY-ND 4.0"))

    def test_simon_verify(self):
        self.assertTrue(verify_simon([0, 2, 1], [0, 2, 1]))
        self.assertFalse(verify_simon([0, 2, 1], [0, 2, 0]))

    def test_pattern_verify(self):
        self.assertTrue(verify_pattern_lock([0, 1, 2, 5], [0, 1, 2, 5]))
        self.assertFalse(verify_pattern_lock([0, 1, 2, 5], [0, 1, 2]))

    def test_pipe_verify(self):
        size = 3
        bases = [2, 10, 8] + [0] * 6
        rots = [0] * 9
        self.assertTrue(verify_pipe_connect(bases, rots, size, 0, 2))

    def test_generate_tier_a_states(self):
        simon = generate_game_state(MINIGIOCO_TIPO_SIMON, 2, 42)
        self.assertEqual(len(simon["sequence"]), 4)
        pattern = generate_game_state(MINIGIOCO_TIPO_PATTERN, 2, 99)
        self.assertEqual(len(pattern["pattern"]), 5)
        pipe = generate_game_state(MINIGIOCO_TIPO_PIPE, 2, 7)
        self.assertEqual(pipe["size"], 4)
        self.assertEqual(len(pipe["bases"]), 16)

    @patch("personaggi.minigioco_biblioteca.biblioteca_immagine_count", return_value=0)
    def test_tipi_pool_senza_immagine(self, _mock):
        cfg = _Cfg(tipi_abilitati=[MINIGIOCO_TIPO_SIMON, MINIGIOCO_TIPO_SLIDING], usa_biblioteca_se_vuota=True)
        pool = tipi_pool_giocabili(cfg)
        self.assertEqual(pool, [MINIGIOCO_TIPO_SIMON])

    @patch("personaggi.minigioco_biblioteca.requests.post")
    def test_registra_openverse_salva_su_db(self, mock_post):
        from personaggi.minigioco_biblioteca import openverse_config_status, registra_openverse_app
        from personaggi.models import MinigiocoOpenverseConfig

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "client_id": "cid-test",
            "client_secret": "secret-test",
            "msg": "Check your email for a verification link.",
        }
        mock_post.return_value = mock_resp

        result = registra_openverse_app(
            name="KOR35 test",
            description="desc",
            email="staff@kor35.it",
        )

        self.assertTrue(result["ok"])
        cfg = MinigiocoOpenverseConfig.get_solo()
        self.assertEqual(cfg.client_id, "cid-test")
        self.assertEqual(cfg.client_secret, "secret-test")
        status = openverse_config_status()
        self.assertTrue(status["configured"])
        self.assertEqual(status["source"], "database")

    @patch("personaggi.minigioco_biblioteca.requests.post")
    def test_registra_openverse_cloudflare_403(self, mock_post):
        from personaggi.minigioco_biblioteca import registra_openverse_app

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "<!DOCTYPE html><html>Just a moment... cloudflare"
        mock_resp.reason = "Forbidden"
        mock_post.return_value = mock_resp

        result = registra_openverse_app(name="KOR35", description="d", email="a@b.it")
        self.assertFalse(result["ok"])
        self.assertTrue(result.get("blocked_by_cloudflare"))

    def test_salva_openverse_credenziali(self):
        from personaggi.minigioco_biblioteca import openverse_config_status, salva_openverse_credenziali

        result = salva_openverse_credenziali(
            client_id="manual-id",
            client_secret="manual-secret",
            name="Manual app",
            email="staff@kor35.it",
        )
        self.assertTrue(result["ok"])
        status = openverse_config_status()
        self.assertTrue(status["configured"])
        self.assertEqual(status["source"], "database")


User = get_user_model()


class MinigiocoModalitaSbloccoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mg_sblocco", password="x")
        self.tipo_pg = TipologiaPersonaggio.objects.create(nome="Std mg sblocco")
        self.pg = Personaggio.objects.create(
            nome="PG mg",
            proprietario=self.user,
            tipologia=self.tipo_pg,
        )
        self.qr = QrCode.objects.create(testo="QR modalità sblocco")
        self.config = MinigiocoQrConfig.objects.create(
            qr_code=self.qr,
            sezione_attiva=True,
            attivo=True,
            tipi_abilitati=[MINIGIOCO_TIPO_SIMON],
        )

    def _session_completata(self, *, quando=None):
        return MinigiocoQrSession.objects.create(
            personaggio=self.pg,
            qr_code=self.qr,
            user=self.user,
            tipo=MINIGIOCO_TIPO_SIMON,
            difficolta=2,
            stato=SESSIONE_COMPLETATO,
            completato_at=quando or timezone.now(),
        )

    def test_permanente_sblocca_dopo_vittoria(self):
        self.config.modalita_sblocco = MinigiocoQrConfig.SBLOCCO_PERMANENTE
        self.config.save()
        self._session_completata()
        self.assertTrue(ha_sblocco_minigioco(self.pg, self.qr, self.config))

    def test_ogni_scansione_non_sblocca(self):
        self.config.modalita_sblocco = MinigiocoQrConfig.SBLOCCO_OGNI_SCANSIONE
        self.config.save()
        self._session_completata()
        self.assertFalse(ha_sblocco_minigioco(self.pg, self.qr, self.config))

    def test_temporaneo_scade(self):
        self.config.modalita_sblocco = MinigiocoQrConfig.SBLOCCO_TEMPORANEO
        self.config.sblocco_secondi = 60
        self.config.save()
        self._session_completata(quando=timezone.now() - timezone.timedelta(seconds=120))
        self.assertFalse(ha_sblocco_minigioco(self.pg, self.qr, self.config))

    def test_temporaneo_ancora_valido(self):
        self.config.modalita_sblocco = MinigiocoQrConfig.SBLOCCO_TEMPORANEO
        self.config.sblocco_secondi = 300
        self.config.save()
        self._session_completata(quando=timezone.now() - timezone.timedelta(seconds=30))
        self.assertTrue(ha_sblocco_minigioco(self.pg, self.qr, self.config))

    def test_bypass_ogni_scansione_solo_transito_immediato(self):
        self.config.modalita_sblocco = MinigiocoQrConfig.SBLOCCO_OGNI_SCANSIONE
        self.config.save()
        recente = self._session_completata()
        self.assertTrue(session_allows_bypass(str(recente.id), self.pg, self.qr))
        MinigiocoQrSession.objects.filter(pk=recente.pk).update(
            completato_at=timezone.now() - timezone.timedelta(seconds=BYPASS_TRANSITO_SECONDI + 5)
        )
        recente.refresh_from_db()
        self.assertFalse(session_allows_bypass(str(recente.id), self.pg, self.qr))

    def test_scaduto_attiva_conta_come_sblocco_temporaneo(self):
        self.config.modalita_sblocco = MinigiocoQrConfig.SBLOCCO_TEMPORANEO
        self.config.sblocco_secondi = 600
        self.config.save()
        MinigiocoQrSession.objects.create(
            personaggio=self.pg,
            qr_code=self.qr,
            user=self.user,
            tipo=MINIGIOCO_TIPO_SIMON,
            difficolta=2,
            stato=SESSIONE_SCADUTO_ATTIVA,
            completato_at=timezone.now(),
        )
        self.assertTrue(ha_sblocco_minigioco(self.pg, self.qr, self.config))


class MinigiocoUsaDefaultPaginaTests(TestCase):
    def test_default_false_e_toggle_su_config(self):
        qr = QrCode.objects.create(testo="QR default flag")
        cfg = MinigiocoQrConfig.objects.create(qr_code=qr, attivo=False)
        self.assertFalse(cfg.usa_default_pagina)
        cfg.usa_default_pagina = True
        cfg.save(update_fields=["usa_default_pagina", "updated_at"])
        cfg.refresh_from_db()
        self.assertTrue(cfg.usa_default_pagina)


class MinigiocoSezioneAccessoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mg_accesso", password="x")
        self.tipo_pg = TipologiaPersonaggio.objects.create(nome="Std mg accesso")
        self.pg = Personaggio.objects.create(
            nome="PG accesso",
            proprietario=self.user,
            tipologia=self.tipo_pg,
        )
        self.qr = QrCode.objects.create(testo="QR accesso gate")
        self.config = MinigiocoQrConfig.objects.create(
            qr_code=self.qr,
            sezione_attiva=True,
            attivo=False,
            requisiti_attivazione=[{"tipo": "statistica", "sigla": "PV", "min": 99}],
            messaggio_accesso_negato="Pannello bloccato.",
        )

    def test_sezione_disattiva_ignora_gate(self):
        from personaggi.qr_minigioco import check_gate_minigioco

        self.config.sezione_attiva = False
        self.config.attivo = True
        self.config.tipi_abilitati = [MINIGIOCO_TIPO_SIMON]
        self.config.save()
        self.assertIsNone(check_gate_minigioco(qr_code=self.qr, personaggio=self.pg))

    @patch("personaggi.models.Statistica.objects.filter")
    def test_requisiti_non_soddisfatti_blocca_qr(self, mock_stat):
        from personaggi.qr_minigioco import check_gate_minigioco

        mock_stat.return_value.first.return_value = None
        gate = check_gate_minigioco(qr_code=self.qr, personaggio=self.pg)
        self.assertEqual(gate["tipo_modello"], "minigioco_bloccato")
        self.assertEqual(gate["messaggio"], "Pannello bloccato.")

    @patch("personaggi.models.Statistica.objects.filter")
    def test_requisiti_ok_senza_minigioco_prosegue(self, mock_stat):
        from personaggi.qr_minigioco import check_gate_minigioco

        mock_stat.return_value.first.return_value = None
        self.config.requisiti_attivazione = [{"tipo": "statistica", "sigla": "PV", "min": 1}]
        self.config.save()
        with patch.object(self.pg, "get_valore_statistica", return_value=5):
            gate = check_gate_minigioco(qr_code=self.qr, personaggio=self.pg)
        self.assertIsNone(gate)

    @patch("personaggi.qr_minigioco.minigioco_ha_immagine_disponibile", return_value=True)
    @patch("personaggi.models.Statistica.objects.filter")
    def test_requisiti_ok_con_minigioco_attivo(self, mock_stat, _mock_img):
        from personaggi.qr_minigioco import check_gate_minigioco

        mock_stat.return_value.first.return_value = None
        self.config.requisiti_attivazione = []
        self.config.attivo = True
        self.config.tipi_abilitati = [MINIGIOCO_TIPO_SIMON]
        self.config.save()
        gate = check_gate_minigioco(qr_code=self.qr, personaggio=self.pg)
        self.assertEqual(gate["tipo_modello"], "minigioco_richiesto")

