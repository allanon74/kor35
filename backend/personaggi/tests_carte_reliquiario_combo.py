"""Test valutazione combo reliquiario staff-defined."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_INNATA,
    CARTA_ENERGIA_MARZIALE,
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_PERSONAGGIO,
    COMBO_TRIGGER_LEGAME,
    CartaCollezionabile,
    CartaPosseduta,
    ComboReliquiario,
    ReliquiarioSlot,
)
from personaggi.carte_reliquiario_combo import calcola_combo_reliquiario_attive, valuta_combo_reliquiario
from personaggi.models import Campagna, Personaggio, TipologiaPersonaggio

User = get_user_model()


class ComboReliquiarioSeedTests(TestCase):
    def test_seed_idempotente(self):
        from personaggi.carte_combo_reliquiario_seed import seed_combo_reliquiario

        campagna = Campagna.objects.create(slug="combo-seed", nome="Seed", attiva=True)
        CartaCollezionabile.objects.create(
            campagna=campagna,
            codice="S1",
            nome="A",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            legame_id="sette-elegie",
        )
        CartaCollezionabile.objects.create(
            campagna=campagna,
            codice="S2",
            nome="B",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_INNATA,
            rarita=CARTA_RARITA_COMUNE,
            legame_id="sette-elegie",
        )

        s1 = seed_combo_reliquiario(campagna=campagna)
        self.assertGreaterEqual(s1["created"], 3)
        self.assertEqual(
            ComboReliquiario.objects.filter(campagna=campagna, codice="triade-naturale").count(),
            1,
        )

        s2 = seed_combo_reliquiario(campagna=campagna)
        self.assertEqual(s2["created"], 0)
        self.assertEqual(s2["skipped"], s1["total"])


class ComboReliquiarioValutaTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(slug="combo-test", nome="Combo", attiva=True)
        self.combo = ComboReliquiario.objects.create(
            campagna=self.campagna,
            codice="legame-x2",
            nome="Legame doppio",
            testo="Due carte dello stesso legame.",
            colore="#ff00aa",
            tipo_trigger=COMBO_TRIGGER_LEGAME,
            param_legame_id="sette-elegie",
            param_min_count=2,
        )
        self.c1 = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="CMB-1",
            nome="Uno",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
            legame_id="sette-elegie",
        )
        self.c2 = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            codice="CMB-2",
            nome="Due",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_INNATA,
            rarita=CARTA_RARITA_COMUNE,
            legame_id="sette-elegie",
        )

    def test_legame_attivo_con_due_carte(self):
        entries = [
            {"slot_index": 0, "carta": self.c1, "codice": "CMB-1", "legame_id": "sette-elegie", "set_collezione": "", "energia": self.c1.energia},
            {"slot_index": 1, "carta": self.c2, "codice": "CMB-2", "legame_id": "sette-elegie", "set_collezione": "", "energia": self.c2.energia},
        ]
        match = valuta_combo_reliquiario(self.combo, entries)
        self.assertIsNotNone(match)
        self.assertEqual(match["slot_indices"], [0, 1])

    def test_calcola_attive_su_personaggio(self):
        user = User.objects.create_user(username="combo_pg", password="x")
        tipo = TipologiaPersonaggio.objects.create(nome="G", giocante=True)
        pg = Personaggio.objects.create(
            nome="PG", proprietario=user, campagna=self.campagna, tipologia=tipo,
        )
        cp1 = CartaPosseduta.objects.create(personaggio=pg, carta=self.c1)
        cp2 = CartaPosseduta.objects.create(personaggio=pg, carta=self.c2)
        ReliquiarioSlot.objects.create(personaggio=pg, slot_index=0, carta_posseduta=cp1)
        ReliquiarioSlot.objects.create(personaggio=pg, slot_index=1, carta_posseduta=cp2)

        attive = calcola_combo_reliquiario_attive(pg)
        self.assertEqual(len(attive), 1)
        self.assertEqual(attive[0]["nome"], "Legame doppio")
        self.assertEqual(attive[0]["colore"], "#ff00aa")
