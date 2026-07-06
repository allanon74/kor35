"""Test duello carte live."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_ARCANA,
    CARTA_ENERGIA_INNATA,
    CARTA_ENERGIA_MAGICA,
    CARTA_ENERGIA_MARZIALE,
    CARTA_ENERGIA_PSIONICA,
    CARTA_ENERGIA_SACRA,
    CARTA_ENERGIA_TECNOLOGICA,
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_EVENTO,
    CARTA_TIPO_LUOGO,
    CARTA_TIPO_OGGETTO,
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
    MANA_MASSIMO_ARCANA,
    MANA_MASSIMO_BASE,
    accetta_duello,
    accetta_duello_per_codice,
    crea_invito_duello,
    esegui_azione_duello,
    get_duello_per_giocatore,
    lista_avversari_duello,
    mana_disponibile_per_turno,
    mana_massimo_giocatore,
    _inizializza_stato_gioco,
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
    """15 carte valide + Leader PG separato."""
    ids = []
    specs = (
        [(CARTA_TIPO_PERSONAGGIO, CARTA_ENERGIA_MARZIALE)] * 4
        + [(CARTA_TIPO_PERSONAGGIO, CARTA_ENERGIA_SACRA)] * 4
        + [(CARTA_TIPO_LUOGO, CARTA_ENERGIA_SACRA)] * 2
        + [(CARTA_TIPO_EVENTO, CARTA_ENERGIA_SACRA)] * 3
        + [(CARTA_TIPO_OGGETTO, CARTA_ENERGIA_MARZIALE)] * 2
    )
    for i, (tipo, energia) in enumerate(specs):
        c = CartaCollezionabile.objects.create(
            campagna=campagna,
            codice=f"D-{pg.nome}-{i}",
            nome=f"Card {i}",
            tipo=tipo,
            energia=energia,
            rarita=CARTA_RARITA_COMUNE,
            attacco=2 if tipo == CARTA_TIPO_PERSONAGGIO else None,
            salute=3 if tipo == CARTA_TIPO_PERSONAGGIO else None,
            costo_gioco=1,
        )
        cp = CartaPosseduta.objects.create(personaggio=pg, carta=c)
        ids.append(str(cp.id))
    return ids


def _leader_helper(campagna, pg, energia=CARTA_ENERGIA_MARZIALE):
    c = CartaCollezionabile.objects.create(
        campagna=campagna,
        codice=f"D-{pg.nome}-LEADER-{energia}",
        nome="Leader",
        tipo=CARTA_TIPO_PERSONAGGIO,
        energia=energia,
        rarita=CARTA_RARITA_COMUNE,
        attacco=3,
        salute=4,
        costo_gioco=2,
    )
    return str(CartaPosseduta.objects.create(personaggio=pg, carta=c).id)


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
        leader_a = _leader_helper(self.campagna, self.pg_a)
        leader_b = _leader_helper(self.campagna, self.pg_b)
        invito = crea_invito_duello(
            self.pg_a, mazzo_a, leader_id=leader_a, sfidato_id=self.pg_b.id,
        )
        duello_id = invito["id"]
        partita = accetta_duello(duello_id, self.pg_b, mazzo_b, leader_id=leader_b)
        self.assertEqual(partita["stato"], DUELLO_STATO_IN_CORSO)
        campo_a = partita["stato_gioco"]["campo"][str(self.pg_a.id)]
        self.assertEqual(campo_a.get("leader_slot"), 0)
        self.assertEqual(campo_a.get("eroi")[0], leader_a)
        self.assertTrue(campo_a.get("eroi_is_leader")[0])

        turno_id = partita["turno_personaggio_id"]
        pg_turno = self.pg_a if turno_id == self.pg_a.id else self.pg_b
        vista_turno = get_duello_per_giocatore(duello_id, pg_turno)
        mano = vista_turno["stato_gioco"]["mani"][str(pg_turno.id)]
        self.assertTrue(len(mano) >= 1)

        carte = vista_turno["carte"]
        cp_id = next(
            (cid for cid in mano if carte.get(cid, {}).get("tipo") == CARTA_TIPO_PERSONAGGIO),
            None,
        )
        self.assertIsNotNone(cp_id, "La mano iniziale dovrebbe contenere almeno un PG.")
        dopo = esegui_azione_duello(
            duello_id,
            pg_turno,
            "gioca_carta",
            {"carta_posseduta_id": cp_id, "slot_eroe": 1},
        )
        self.assertEqual(dopo["turno_personaggio_id"], turno_id)
        dopo_pass = esegui_azione_duello(duello_id, pg_turno, "passa", {})
        self.assertNotEqual(dopo_pass["turno_personaggio_id"], turno_id)


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
        leader_a = _leader_helper(self.campagna, self.pg_a)
        leader_b = _leader_helper(self.campagna, self.pg_b)
        lobby = apri_scontro_lobby(self.pg_a)
        self.assertEqual(lobby["stato"], "LOB")
        self.assertTrue(lobby.get("qrcode_id"))
        pre = unisciti_scontro_lobby(self.pg_b, qrcode_id=lobby["qrcode_id"])
        self.assertEqual(pre["stato"], DUELLO_STATO_PREMATCH)
        azione_prematch(pre["id"], self.pg_a, "proponi_posta", {"posta_cr": 0})
        azione_prematch(
            pre["id"], self.pg_a, "imposta_mazzo",
            {"mazzo_ids": mazzo_a, "leader_id": leader_a},
        )
        azione_prematch(
            pre["id"], self.pg_b, "imposta_mazzo",
            {"mazzo_ids": mazzo_b, "leader_id": leader_b},
        )
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


class CarteDuelloManaTests(TestCase):
    def test_mana_disponibile_curva(self):
        self.assertEqual(mana_disponibile_per_turno(1, MANA_MASSIMO_BASE), 1)
        self.assertEqual(mana_disponibile_per_turno(2, MANA_MASSIMO_BASE), 2)
        self.assertEqual(mana_disponibile_per_turno(3, MANA_MASSIMO_BASE), 3)
        self.assertEqual(mana_disponibile_per_turno(9, MANA_MASSIMO_BASE), 3)
        self.assertEqual(mana_disponibile_per_turno(3, MANA_MASSIMO_ARCANA), 4)

    def setUp(self):
        self.user_a = User.objects.create_user(username="mana_a", password="x")
        self.user_b = User.objects.create_user(username="mana_b", password="x")
        self.campagna = Campagna.objects.create(slug="mana-test", nome="Mana Test", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna, accesso_modo=CARTE_ACCESSO_TEST, abilitata=True,
        )
        tipo = TipologiaPersonaggio.objects.create(nome="PNG", giocante=False)
        self.pg_a = Personaggio.objects.create(
            nome="Arcana", proprietario=self.user_a, campagna=self.campagna, tipologia=tipo,
        )
        self.pg_b = Personaggio.objects.create(
            nome="Marziale", proprietario=self.user_b, campagna=self.campagna, tipologia=tipo,
        )

    def _avvia_partita(self, energia_leader_a, energia_leader_b):
        mazzo_a = _mazzo_valido_helper(self.campagna, self.pg_a)
        mazzo_b = _mazzo_valido_helper(self.campagna, self.pg_b)
        leader_a = _leader_helper(self.campagna, self.pg_a, energia_leader_a)
        leader_b = _leader_helper(self.campagna, self.pg_b, energia_leader_b)
        invito = crea_invito_duello(
            self.pg_a, mazzo_a, leader_id=leader_a, sfidato_id=self.pg_b.id,
        )
        return accetta_duello(invito["id"], self.pg_b, mazzo_b, leader_id=leader_b)

    def test_mana_massimo_da_leader(self):
        from personaggi.carte_collezionabili_models import DuelloCarte

        partita = self._avvia_partita(CARTA_ENERGIA_ARCANA, CARTA_ENERGIA_MARZIALE)
        duello = DuelloCarte.objects.get(pk=partita["id"])
        self.assertEqual(mana_massimo_giocatore(duello, self.pg_a), MANA_MASSIMO_ARCANA)
        self.assertEqual(mana_massimo_giocatore(duello, self.pg_b), MANA_MASSIMO_BASE)

    def test_mana_rinnovo_turno_3_arcana(self):
        partita = self._avvia_partita(CARTA_ENERGIA_ARCANA, CARTA_ENERGIA_MARZIALE)
        duello_id = partita["id"]
        primo_id = partita["turno_personaggio_id"]
        primo = self.pg_a if primo_id == self.pg_a.id else self.pg_b
        secondo = self.pg_b if primo.id == self.pg_a.id else self.pg_a

        vista1 = get_duello_per_giocatore(duello_id, primo)
        self.assertEqual(vista1["stato_gioco"]["campo"][str(primo.id)]["energia"], 1)

        esegui_azione_duello(duello_id, primo, "passa", {})
        esegui_azione_duello(duello_id, secondo, "passa", {})
        vista3 = get_duello_per_giocatore(duello_id, primo)
        campo = vista3["stato_gioco"]["campo"][str(primo.id)]
        self.assertEqual(campo["turno_numero"], 2)
        self.assertEqual(campo["energia"], 2)

        esegui_azione_duello(duello_id, primo, "passa", {})
        esegui_azione_duello(duello_id, secondo, "passa", {})
        vista5 = get_duello_per_giocatore(duello_id, primo)
        campo = vista5["stato_gioco"]["campo"][str(primo.id)]
        self.assertEqual(campo["turno_numero"], 3)
        mana_max_atteso = (
            MANA_MASSIMO_ARCANA if primo.id == self.pg_a.id else MANA_MASSIMO_BASE
        )
        self.assertEqual(campo["mana_massimo"], mana_max_atteso)
        self.assertEqual(campo["energia"], mana_max_atteso)

    def test_limite_permanente_ed_effetto_per_turno(self):
        from personaggi.carte_collezionabili_models import DuelloCarte

        partita = self._avvia_partita(CARTA_ENERGIA_MARZIALE, CARTA_ENERGIA_MARZIALE)
        duello_id = partita["id"]
        pg_turno = (
            self.pg_a if partita["turno_personaggio_id"] == self.pg_a.id else self.pg_b
        )
        duello = DuelloCarte.objects.get(pk=duello_id)
        key = str(pg_turno.id)
        duello.stato_gioco[key]["energia"] = 10
        duello.save(update_fields=["stato_gioco", "updated_at"])
        vista = get_duello_per_giocatore(duello_id, pg_turno)
        mano = vista["stato_gioco"]["mani"][str(pg_turno.id)]
        carte = vista["carte"]
        cp_pg = next(cid for cid in mano if carte[cid]["tipo"] == CARTA_TIPO_PERSONAGGIO)
        esegui_azione_duello(
            duello_id, pg_turno, "gioca_carta",
            {"carta_posseduta_id": cp_pg, "slot_eroe": 1},
        )
        vista2 = get_duello_per_giocatore(duello_id, pg_turno)
        mano2 = vista2["stato_gioco"]["mani"][str(pg_turno.id)]
        cp_luo = next((cid for cid in mano2 if carte[cid]["tipo"] == CARTA_TIPO_LUOGO), None)
        if cp_luo:
            with self.assertRaises(ValidationError):
                esegui_azione_duello(
                    duello_id, pg_turno, "gioca_carta",
                    {"carta_posseduta_id": cp_luo},
                )
        cp_evt = next((cid for cid in mano2 if carte[cid]["tipo"] == CARTA_TIPO_EVENTO), None)
        if cp_evt:
            esegui_azione_duello(
                duello_id, pg_turno, "gioca_carta",
                {"carta_posseduta_id": cp_evt},
            )
            vista3 = get_duello_per_giocatore(duello_id, pg_turno)
            mano3 = vista3["stato_gioco"]["mani"][str(pg_turno.id)]
            cp_evt2 = next(
                (cid for cid in mano3 if carte[cid]["tipo"] == CARTA_TIPO_EVENTO),
                None,
            )
            if cp_evt2:
                with self.assertRaises(ValidationError):
                    esegui_azione_duello(
                        duello_id, pg_turno, "gioca_carta",
                        {"carta_posseduta_id": cp_evt2},
                    )


class CarteDuelloCombattimentoTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="comb_a", password="x")
        self.user_b = User.objects.create_user(username="comb_b", password="x")
        self.campagna = Campagna.objects.create(slug="comb-test", nome="Comb Test", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna, accesso_modo=CARTE_ACCESSO_TEST, abilitata=True,
        )
        tipo = TipologiaPersonaggio.objects.create(nome="PNG", giocante=False)
        self.pg_a = Personaggio.objects.create(
            nome="Att", proprietario=self.user_a, campagna=self.campagna, tipologia=tipo,
        )
        self.pg_b = Personaggio.objects.create(
            nome="Dif", proprietario=self.user_b, campagna=self.campagna, tipologia=tipo,
        )

    def _avvia_partita(self):
        mazzo_a = _mazzo_valido_helper(self.campagna, self.pg_a)
        mazzo_b = _mazzo_valido_helper(self.campagna, self.pg_b)
        leader_a = _leader_helper(self.campagna, self.pg_a)
        leader_b = _leader_helper(self.campagna, self.pg_b)
        invito = crea_invito_duello(
            self.pg_a, mazzo_a, leader_id=leader_a, sfidato_id=self.pg_b.id,
        )
        return accetta_duello(invito["id"], self.pg_b, mazzo_b, leader_id=leader_b)

    def _gioca_primo_pg_in_campo(self, duello_id, pg, slot=1):
        vista = get_duello_per_giocatore(duello_id, pg)
        mano = vista["stato_gioco"]["mani"][str(pg.id)]
        carte = vista["carte"]
        cp_pg = next(cid for cid in mano if carte[cid]["tipo"] == CARTA_TIPO_PERSONAGGIO)
        return esegui_azione_duello(
            duello_id, pg, "gioca_carta",
            {"carta_posseduta_id": cp_pg, "slot_eroe": slot},
        )

    def test_attacco_esaurisce_eroe(self):
        partita = self._avvia_partita()
        duello_id = partita["id"]
        pg_turno = (
            self.pg_a if partita["turno_personaggio_id"] == self.pg_a.id else self.pg_b
        )
        esegui_azione_duello(duello_id, pg_turno, "attacca", {"slot_eroe": 0})
        vista = get_duello_per_giocatore(duello_id, pg_turno)
        campo = vista["stato_gioco"]["campo"][str(pg_turno.id)]
        self.assertTrue(campo["eroi_esauriti"][0])
        with self.assertRaises(ValidationError):
            esegui_azione_duello(duello_id, pg_turno, "attacca", {"slot_eroe": 0})

    def test_iniziativa_colpisce_per_primo(self):
        from personaggi.carte_collezionabili_models import DuelloCarte

        rapido = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="COMB-RAP",
            nome="Rapido",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=3,
            salute=2,
            iniziativa=3,
        )
        cp_rap = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=rapido)
        lento = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="COMB-LEN",
            nome="Lento",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=2,
            salute=2,
            iniziativa=0,
        )
        cp_len = CartaPosseduta.objects.create(personaggio=self.pg_b, carta=lento)
        mazzo_ids = [str(cp_rap.id)] + [
            str(self._extra_mazzo(self.pg_a, i).id) for i in range(14)
        ]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a, key_b = str(self.pg_a.id), str(self.pg_b.id)
        duello.stato_gioco[key_a]["eroi"][0] = str(cp_rap.id)
        duello.stato_gioco[key_a]["salute_eroi"] = [2, None]
        duello.stato_gioco[key_b]["eroi"][0] = str(cp_len.id)
        duello.stato_gioco[key_b]["salute_eroi"] = [2, None]
        duello.save()

        esegui_azione_duello(
            duello.id, self.pg_a, "attacca",
            {"slot_eroe": 0, "bersaglio_eroe_slot": 0},
        )
        duello.refresh_from_db()
        self.assertIsNone(duello.stato_gioco[key_b]["eroi"][0])
        self.assertEqual(duello.stato_gioco[key_a]["salute_eroi"][0], 2)

    def _extra_mazzo(self, pg, i):
        c = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice=f"COMB-X-{pg.nome}-{i}",
            nome=f"Extra {i}",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            costo_gioco=1,
            attacco=1,
            salute=1,
        )
        return CartaPosseduta.objects.create(personaggio=pg, carta=c)

    def test_difensore_obbliga_bersaglio(self):
        from personaggi.carte_collezionabili_models import DuelloCarte
        from personaggi.carte_duello_service import _pg_key

        att = CartaPosseduta.objects.create(
            personaggio=self.pg_a,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="COMB-ATK", nome="Att",
                tipo=CARTA_TIPO_PERSONAGGIO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1, attacco=2, salute=2,
            ),
        )
        tank = CartaPosseduta.objects.create(
            personaggio=self.pg_b,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="COMB-TNK", nome="Tank",
                tipo=CARTA_TIPO_PERSONAGGIO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1, attacco=1, salute=4,
                testo_gioco="Difensore.",
            ),
        )
        altro = CartaPosseduta.objects.create(
            personaggio=self.pg_b,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="COMB-ALT", nome="Altro",
                tipo=CARTA_TIPO_PERSONAGGIO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1, attacco=1, salute=2,
            ),
        )
        mazzo_ids = [str(att.id)] + [str(self._extra_mazzo(self.pg_a, i).id) for i in range(14)]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a, key_b = _pg_key(self.pg_a), _pg_key(self.pg_b)
        duello.stato_gioco[key_a]["eroi"][0] = str(att.id)
        duello.stato_gioco[key_b]["eroi"][0] = str(altro.id)
        duello.stato_gioco[key_b]["eroi"][1] = str(tank.id)
        duello.stato_gioco[key_b]["salute_eroi"] = [2, 4]
        duello.save()

        with self.assertRaises(ValidationError):
            esegui_azione_duello(
                duello.id, self.pg_a, "attacca",
                {"slot_eroe": 0, "bersaglio_eroe_slot": 0},
            )
        with self.assertRaises(ValidationError):
            esegui_azione_duello(duello.id, self.pg_a, "attacca", {"slot_eroe": 0})

    def test_cura_fine_turno(self):
        from personaggi.carte_collezionabili_models import DuelloCarte
        from personaggi.carte_duello_service import _pg_key

        att = CartaPosseduta.objects.create(
            personaggio=self.pg_a,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="COMB-CUR-A", nome="Curatore",
                tipo=CARTA_TIPO_PERSONAGGIO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1, attacco=1, salute=4,
            ),
        )
        bers = CartaPosseduta.objects.create(
            personaggio=self.pg_b,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="COMB-CUR-B", nome="Bers",
                tipo=CARTA_TIPO_PERSONAGGIO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1, attacco=1, salute=4,
            ),
        )
        mazzo_ids = [str(att.id)] + [str(self._extra_mazzo(self.pg_a, i).id) for i in range(14)]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a, key_b = _pg_key(self.pg_a), _pg_key(self.pg_b)
        duello.stato_gioco[key_a]["eroi"][0] = str(att.id)
        duello.stato_gioco[key_a]["salute_eroi"] = [4, None]
        duello.stato_gioco[key_b]["eroi"][0] = str(bers.id)
        duello.stato_gioco[key_b]["salute_eroi"] = [4, None]
        duello.save()

        esegui_azione_duello(
            duello.id, self.pg_a, "attacca",
            {"slot_eroe": 0, "bersaglio_eroe_slot": 0},
        )
        duello.refresh_from_db()
        self.assertEqual(duello.stato_gioco[key_b]["salute_eroi"][0], 3)

        esegui_azione_duello(duello.id, self.pg_a, "passa", {})
        duello.refresh_from_db()
        self.assertEqual(duello.stato_gioco[key_b]["salute_eroi"][0], 4)

    def test_ristappo_inizio_turno(self):
        partita = self._avvia_partita()
        duello_id = partita["id"]
        pg_turno = (
            self.pg_a if partita["turno_personaggio_id"] == self.pg_a.id else self.pg_b
        )
        altro = self.pg_b if pg_turno.id == self.pg_a.id else self.pg_a
        esegui_azione_duello(duello_id, pg_turno, "attacca", {"slot_eroe": 0})
        esegui_azione_duello(duello_id, pg_turno, "passa", {})
        esegui_azione_duello(duello_id, altro, "passa", {})
        vista = get_duello_per_giocatore(duello_id, pg_turno)
        campo = vista["stato_gioco"]["campo"][str(pg_turno.id)]
        self.assertEqual(campo["eroi_esauriti"], [False, False])

    def test_leader_attacco_esaurisce(self):
        partita = self._avvia_partita()
        duello_id = partita["id"]
        pg_turno = (
            self.pg_a if partita["turno_personaggio_id"] == self.pg_a.id else self.pg_b
        )
        campo = get_duello_per_giocatore(duello_id, pg_turno)["stato_gioco"]["campo"][str(pg_turno.id)]
        slot_leader = campo.get("leader_slot")
        self.assertEqual(slot_leader, 0)
        esegui_azione_duello(duello_id, pg_turno, "attacca", {"slot_eroe": slot_leader})
        vista = get_duello_per_giocatore(duello_id, pg_turno)
        campo = vista["stato_gioco"]["campo"][str(pg_turno.id)]
        self.assertTrue(campo["eroi_esauriti"][slot_leader])
        with self.assertRaises(ValidationError):
            esegui_azione_duello(duello_id, pg_turno, "attacca", {"slot_eroe": slot_leader})

    def test_leader_muore_torna_mano(self):
        from personaggi.carte_collezionabili_models import DuelloCarte
        from personaggi.carte_duello_service import _pg_key

        leader_b = CartaPosseduta.objects.create(
            personaggio=self.pg_b,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="COMB-LDR-B", nome="Leader B",
                tipo=CARTA_TIPO_PERSONAGGIO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=2, attacco=1, salute=2,
            ),
        )
        att = CartaPosseduta.objects.create(
            personaggio=self.pg_a,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="COMB-LDR-ATK", nome="Killer",
                tipo=CARTA_TIPO_PERSONAGGIO, energia=CARTA_ENERGIA_MARZIALE,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1, attacco=3, salute=2, iniziativa=5,
            ),
        )
        mazzo_ids = [str(att.id)] + [str(self._extra_mazzo(self.pg_a, i).id) for i in range(14)]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            leader_sfidante_id=str(_leader_helper(self.campagna, self.pg_a)),
            leader_sfidato_id=str(leader_b.id),
            mazzo_sfidante_ids=mazzo_ids,
            mazzo_sfidato_ids=mazzo_ids,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a, key_b = _pg_key(self.pg_a), _pg_key(self.pg_b)
        duello.stato_gioco[key_a]["eroi"][1] = str(att.id)
        duello.stato_gioco[key_a]["salute_eroi"] = [duello.stato_gioco[key_a]["salute_eroi"][0], 2]
        duello.save()

        esegui_azione_duello(
            duello.id, self.pg_a, "attacca",
            {"slot_eroe": 1, "bersaglio_eroe_slot": 0},
        )
        duello.refresh_from_db()
        lato_b = duello.stato_gioco[key_b]
        self.assertIsNone(lato_b["eroi"][0])
        self.assertIn(str(leader_b.id), lato_b.get("mano") or [])
        scarto = lato_b.get("scarto") or []
        self.assertNotIn(str(leader_b.id), scarto)

    def test_terra_condivisa_sostituisce(self):
        from personaggi.carte_collezionabili_models import DuelloCarte
        from personaggi.carte_duello_service import _pg_key

        terra_a = CartaPosseduta.objects.create(
            personaggio=self.pg_a,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="TERRA-A", nome="Foresta A",
                tipo=CARTA_TIPO_LUOGO, energia=CARTA_ENERGIA_SACRA,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1,
            ),
        )
        terra_b = CartaPosseduta.objects.create(
            personaggio=self.pg_b,
            carta=CartaCollezionabile.objects.create(
                campagna=self.campagna, codice="TERRA-B", nome="Foresta B",
                tipo=CARTA_TIPO_LUOGO, energia=CARTA_ENERGIA_SACRA,
                rarita=CARTA_RARITA_COMUNE, costo_gioco=1,
            ),
        )
        mazzo_a = [str(terra_a.id)] + [str(self._extra_mazzo(self.pg_a, i).id) for i in range(14)]
        mazzo_b = [str(terra_b.id)] + [str(self._extra_mazzo(self.pg_b, i).id) for i in range(14)]
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            leader_sfidante_id=str(_leader_helper(self.campagna, self.pg_a)),
            leader_sfidato_id=str(_leader_helper(self.campagna, self.pg_b)),
            mazzo_sfidante_ids=mazzo_a,
            mazzo_sfidato_ids=mazzo_b,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        key_a, key_b = _pg_key(self.pg_a), _pg_key(self.pg_b)
        duello.stato_gioco[key_a]["mano"] = [str(terra_a.id)]
        duello.stato_gioco[key_a]["energia"] = 5
        duello.stato_gioco[key_b]["mano"] = [str(terra_b.id)]
        duello.stato_gioco[key_b]["energia"] = 5
        duello.save()

        esegui_azione_duello(
            duello.id, self.pg_a, "gioca_carta", {"carta_posseduta_id": str(terra_a.id)},
        )
        duello.refresh_from_db()
        self.assertEqual(duello.stato_gioco["terra"]["carta_posseduta_id"], str(terra_a.id))

        esegui_azione_duello(duello.id, self.pg_a, "passa", {})
        esegui_azione_duello(
            duello.id, self.pg_b, "gioca_carta", {"carta_posseduta_id": str(terra_b.id)},
        )
        duello.refresh_from_db()
        self.assertEqual(duello.stato_gioco["terra"]["carta_posseduta_id"], str(terra_b.id))
        self.assertIn(str(terra_a.id), duello.stato_gioco[key_a].get("scarto") or [])


class CarteDuelloFaseTurnoTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="fase_a", password="x")
        self.user_b = User.objects.create_user(username="fase_b", password="x")
        self.campagna = Campagna.objects.create(slug="fase-camp", nome="Fase", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna, accesso_modo=CARTE_ACCESSO_OPEN, abilitata=True,
        )
        tipo = TipologiaPersonaggio.objects.create(nome="Umano")
        self.pg_a = Personaggio.objects.create(
            nome="Alpha", proprietario=self.user_a, campagna=self.campagna, tipologia=tipo,
        )
        self.pg_b = Personaggio.objects.create(
            nome="Beta", proprietario=self.user_b, campagna=self.campagna, tipologia=tipo,
        )

    def _duello_base(self):
        from personaggi.carte_collezionabili_models import DuelloCarte

        mazzo_a = _mazzo_valido_helper(self.campagna, self.pg_a)
        mazzo_b = _mazzo_valido_helper(self.campagna, self.pg_b)
        duello = DuelloCarte.objects.create(
            campagna=self.campagna,
            sfidante=self.pg_a,
            sfidato=self.pg_b,
            stato=DUELLO_STATO_IN_CORSO,
            turno_personaggio=self.pg_a,
            leader_sfidante_id=_leader_helper(self.campagna, self.pg_a),
            leader_sfidato_id=_leader_helper(self.campagna, self.pg_b),
            mazzo_sfidante_ids=mazzo_a,
            mazzo_sfidato_ids=mazzo_b,
        )
        duello.stato_gioco = _inizializza_stato_gioco(duello)
        duello.save()
        return duello

    def test_passa_avanza_fasi_turno(self):
        from personaggi.carte_duello_service import FASE_TURNO_APERTURA, FASE_TURNO_CHIUSURA, FASE_TURNO_COMBATTIMENTO, _pg_key

        duello = self._duello_base()
        key_a = _pg_key(self.pg_a)
        self.assertEqual(duello.stato_gioco[key_a]["fase_turno"], FASE_TURNO_APERTURA)

        esegui_azione_duello(duello.id, self.pg_a, "passa", {})
        duello.refresh_from_db()
        self.assertEqual(duello.stato_gioco[key_a]["fase_turno"], FASE_TURNO_COMBATTIMENTO)

        esegui_azione_duello(duello.id, self.pg_a, "passa", {})
        duello.refresh_from_db()
        self.assertEqual(duello.stato_gioco[key_a]["fase_turno"], FASE_TURNO_CHIUSURA)

    def test_gioca_carta_bloccato_in_combattimento(self):
        from personaggi.carte_duello_service import FASE_TURNO_COMBATTIMENTO, _pg_key

        duello = self._duello_base()
        key_a = _pg_key(self.pg_a)
        duello.stato_gioco[key_a]["fase_turno"] = FASE_TURNO_COMBATTIMENTO
        cp_id = duello.stato_gioco[key_a]["mano"][0]
        duello.stato_gioco[key_a]["energia"] = 10
        duello.save()

        with self.assertRaises(ValidationError):
            esegui_azione_duello(
                duello.id,
                self.pg_a,
                "gioca_carta",
                {"carta_posseduta_id": cp_id, "slot_eroe": 1},
            )

    def test_guscio_assorbe_danno_letale(self):
        from personaggi.carte_duello_service import _applica_danno_eroe, _pg_key

        duello = self._duello_base()
        key_b = _pg_key(self.pg_b)
        cp_id = duello.stato_gioco[key_b]["eroi"][0]
        duello.stato_gioco[key_b]["salute_eroi"] = [1, None]
        duello.stato_gioco[key_b]["guscio_eroi"] = [1, 0]
        duello.save()

        esaurito = _applica_danno_eroe(duello, self.pg_b, 0, 1)
        lato = duello.stato_gioco[key_b]
        self.assertFalse(esaurito)
        self.assertEqual(lato["salute_eroi"][0], 1)
        self.assertEqual(lato["guscio_eroi"][0], 0)
        self.assertEqual(lato["eroi"][0], cp_id)

    def test_bonus_leader_in_vista_campo(self):
        from personaggi.carte_duello_service import _pg_key

        duello = self._duello_base()
        vista = get_duello_per_giocatore(duello.id, self.pg_a)
        campo = vista["stato_gioco"]["campo"][str(self.pg_a.id)]
        self.assertIn("bonus_leader", campo)
        self.assertTrue(len(campo["bonus_leader"]) >= 1)
        self.assertEqual(campo.get("fase_turno_label"), "Apertura")
