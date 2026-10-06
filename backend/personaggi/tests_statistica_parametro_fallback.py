"""Regressione: statistica senza parametro deve comunque applicare AbilitaStatistica."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from personaggi.models import (
    CARATTERISTICA,
    MODIFICATORE_ADDITIVO,
    Abilita,
    AbilitaStatistica,
    Personaggio,
    PersonaggioAbilita,
    Punteggio,
    Statistica,
    statistica_chiave_modificatore,
)

User = get_user_model()


class StatisticaParametroFallbackTests(TestCase):
    def setUp(self):
        Punteggio.objects.filter(sigla__in=["ZX1", "ZX2", "ZXC"]).delete()
        self.user = User.objects.create_user(username="pg-p01-fallback", password="x")
        self.pg = Personaggio.objects.create(nome="Carloh Fallback", proprietario=self.user)
        self.caratt = Punteggio.objects.create(
            nome="Caratteristica Fallback ZX",
            sigla="ZXC",
            tipo=CARATTERISTICA,
        )

    def test_save_copia_sigla_in_parametro_se_vuoto(self):
        st = Statistica.objects.create(nome="Uso Specchio Anima Test", sigla="ZX1")
        st.refresh_from_db()
        self.assertEqual(st.parametro, "ZX1")
        self.assertEqual(statistica_chiave_modificatore(st), "ZX1")

    def test_abilita_plus_uno_anche_con_parametro_nullo_in_db(self):
        st = Statistica.objects.create(
            nome="Uso Specchio Anima Test 2",
            sigla="ZX2",
            parametro="ZX2",
            valore_base_predefinito=0,
        )
        Statistica.objects.filter(pk=st.pk).update(parametro=None)
        st.refresh_from_db()
        self.assertFalse((st.parametro or "").strip())
        self.assertEqual(statistica_chiave_modificatore(st), "ZX2")

        ab = Abilita.objects.create(
            nome="Usare specchio dellanima",
            caratteristica=self.caratt,
            costo_pc=0,
            costo_crediti=0,
        )
        AbilitaStatistica.objects.create(
            abilita=ab,
            statistica=st,
            valore=1,
            tipo_modificatore=MODIFICATORE_ADDITIVO,
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=ab)

        self.assertEqual(self.pg.get_valore_statistica("ZX2"), 1)
        self.assertIn("Uso Specchio Anima Test 2", self.pg.punteggi_base)
        self.assertEqual(self.pg.modificatori_calcolati.get("ZX2", {}).get("add"), 1.0)
        dettagli = self.pg.get_modificatori_dettagliati()
        self.assertIn("ZX2", dettagli)
        self.assertEqual(dettagli["ZX2"]["valore_finale"], 1.0)
