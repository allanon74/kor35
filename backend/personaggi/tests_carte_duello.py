"""Test duello carte live."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_INNATA,
    CARTA_ENERGIA_MAGICA,
    CARTA_ENERGIA_MARZIALE,
    CARTA_ENERGIA_PSIONICA,
    CARTA_ENERGIA_SACRA,
    CARTA_ENERGIA_TECNOLOGICA,
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_PERSONAGGIO,
    CartaCollezionabile,
    CartaPosseduta,
    ConfigurazioneCarteCollezionabili,
    CARTE_ACCESSO_OPEN,
    CARTE_ACCESSO_TEST,
    DUELLO_STATO_IN_CORSO,
    DUELLO_STATO_PREMATCH,
)
from personaggi.carte_duello_service import (
    accetta_duello,
    accetta_duello_per_codice,
    crea_invito_duello,
    esegui_azione_duello,
    get_duello_per_giocatore,
    lista_avversari_duello,
)
from personaggi.carte_lobby_service import (
    apri_scontro_lobby,
    azione_prematch,
    unisciti_scontro_lobby,
)
from personaggi.models import Campagna, Personaggio, QrCode, TipologiaPersonaggio

User = get_user_model()
MAZZO_SIZE = 15


def _mazzo_valido_helper(campagna, pg):
    ids = []
    energie = [
        CARTA_ENERGIA_MARZIALE,
        CARTA_ENERGIA_SACRA,
        CARTA_ENERGIA_TECNOLOGICA,
        CARTA_ENERGIA_INNATA,
        CARTA_ENERGIA_MAGICA,
        CARTA_ENERGIA_PSIONICA,
    ]
    for i in range(MAZZO_SIZE):
        c = CartaCollezionabile.objects.create(
            campagna=campagna,
            codice=f"D-{pg.nome}-{i}",
            nome=f"Card {i}",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=energie[i % len(energie)],
            rarita=CARTA_RARITA_COMUNE,
            attacco=2,
            salute=3,
            costo_gioco=1,
        )
        cp = CartaPosseduta.objects.create(personaggio=pg, carta=c)
        ids.append(str(cp.id))
    return ids


class CarteDuelloLiveTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="duellante_a", password="x")
        self.user_b = User.objects.create_user(username="duellante_b", password="x")
        self.campagna = Campagna.objects.create(slug="duel-camp", nome="Duel", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna,
            accesso_modo=CARTE_ACCESSO_OPEN,
            abilitata=True,
        )
        tipo = TipologiaPersonaggio.objects.create(nome="Umano")
        self.pg_a = Personaggio.objects.create(
            nome="Alpha", proprietario=self.user_a, campagna=self.campagna, tipologia=tipo,
        )
        self.pg_b = Personaggio.objects.create(
            nome="Beta", proprietario=self.user_b, campagna=self.campagna, tipologia=tipo,
        )

    def _mazzo_valido(self, pg):
        return _mazzo_valido_helper(self.campagna, pg)

    def _qr_per_personaggio(self, pg):
        qr = QrCode.objects.create()
        qr.vista = pg
        qr.save()
        return qr

    def test_duello_live_turni(self):
        ConfigurazioneCarteCollezionabili.objects.filter(campagna=self.campagna).update(
            accesso_modo=CARTE_ACCESSO_TEST,
        )
        tipo_png = TipologiaPersonaggio.objects.create(nome="PNG Staff", giocante=False)
        self.pg_a.tipologia = tipo_png
        self.pg_a.save(update_fields=["tipologia"])
        self.pg_b.tipologia = tipo_png
        self.pg_b.save(update_fields=["tipologia"])
        mazzo_a = self._mazzo_valido(self.pg_a)
        mazzo_b = self._mazzo_valido(self.pg_b)
        invito = crea_invito_duello(self.pg_a, mazzo_a, sfidato_id=self.pg_b.id)
        duello_id = invito["id"]
        partita = accetta_duello(duello_id, self.pg_b, mazzo_b)
        self.assertEqual(partita["stato"], DUELLO_STATO_IN_CORSO)

        turno_id = partita["turno_personaggio_id"]
        pg_turno = self.pg_a if turno_id == self.pg_a.id else self.pg_b
        vista_turno = get_duello_per_giocatore(duello_id, pg_turno)
        mano = vista_turno["stato_gioco"]["mani"][str(pg_turno.id)]
        self.assertTrue(len(mano) >= 1)

        cp_id = mano[0]
        dopo = esegui_azione_duello(
            duello_id,
            pg_turno,
            "gioca_carta",
            {"carta_posseduta_id": cp_id, "slot_eroe": 0},
        )
        self.assertNotEqual(dopo["turno_personaggio_id"], turno_id)


class CarteDuelloModalitaAvvioTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="duel_a", password="x")
        self.user_b = User.objects.create_user(username="duel_b", password="x")
        self.campagna = Campagna.objects.create(slug="duel-mod", nome="Duel Mod", attiva=True)
        tipo = TipologiaPersonaggio.objects.create(nome="Umano", giocante=True)
        self.pg_a = Personaggio.objects.create(
            nome="Alpha", proprietario=self.user_a, campagna=self.campagna, tipologia=tipo,
        )
        self.pg_b = Personaggio.objects.create(
            nome="Beta", proprietario=self.user_b, campagna=self.campagna, tipologia=tipo,
        )

    def _mazzo_valido(self, pg):
        return _mazzo_valido_helper(self.campagna, pg)

    def test_open_usa_lobby(self):
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna, accesso_modo=CARTE_ACCESSO_OPEN, abilitata=True,
        )
        with self.assertRaises(ValidationError):
            crea_invito_duello(self.pg_a, ["x"] * 15, sfidato_id=self.pg_b.id)

    def test_lobby_prematch_avvio(self):
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna, accesso_modo=CARTE_ACCESSO_OPEN, abilitata=True,
        )
        mazzo_a = self._mazzo_valido(self.pg_a)
        mazzo_b = self._mazzo_valido(self.pg_b)
        lobby = apri_scontro_lobby(self.pg_a)
        self.assertEqual(lobby["stato"], "LOB")
        self.assertTrue(lobby.get("qrcode_id"))
        pre = unisciti_scontro_lobby(self.pg_b, qrcode_id=lobby["qrcode_id"])
        self.assertEqual(pre["stato"], DUELLO_STATO_PREMATCH)
        azione_prematch(pre["id"], self.pg_a, "proponi_posta", {"posta_cr": 0})
        azione_prematch(pre["id"], self.pg_a, "imposta_mazzo", {"mazzo_ids": mazzo_a})
        azione_prematch(pre["id"], self.pg_b, "imposta_mazzo", {"mazzo_ids": mazzo_b})
        azione_prematch(pre["id"], self.pg_a, "segna_pronto", {"pronto": True})
        partita = azione_prematch(pre["id"], self.pg_b, "segna_pronto", {"pronto": True})
        self.assertEqual(partita["stato"], DUELLO_STATO_IN_CORSO)

    def test_test_lista_avversari(self):
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna, accesso_modo=CARTE_ACCESSO_TEST, abilitata=True,
        )
        tipo_png = TipologiaPersonaggio.objects.create(nome="PNG Staff", giocante=False)
        self.pg_a.tipologia = tipo_png
        self.pg_a.save(update_fields=["tipologia"])
        self.pg_b.tipologia = tipo_png
        self.pg_b.save(update_fields=["tipologia"])
        avv = lista_avversari_duello(self.pg_a)
        self.assertEqual(len(avv), 1)
        self.assertEqual(avv[0]["id"], self.pg_b.id)

    def test_codice_bloccato_in_open(self):
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna, accesso_modo=CARTE_ACCESSO_OPEN, abilitata=True,
        )
        with self.assertRaises(ValidationError):
            accetta_duello_per_codice(self.pg_b, "ABCDEF", ["x"] * 15)
