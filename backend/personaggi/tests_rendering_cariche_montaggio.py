"""
Rendering testo formattato: dicitura cariche e Classi Oggetto montabili su Mod/Materia.
"""
from django.test import TestCase

from personaggi.models import (
    AURA,
    CARATTERISTICA,
    ClasseOggetto,
    ClasseOggettoLimiteMod,
    Infusione,
    InfusioneCaratteristica,
    InfusioneStatisticaBase,
    Oggetto,
    OggettoCaratteristica,
    Punteggio,
    SCELTA_RISULTATO_AUMENTO,
    SCELTA_RISULTATO_POTENZIAMENTO,
    Statistica,
    TIPO_OGGETTO_INNESTO,
    TIPO_OGGETTO_MATERIA,
    TIPO_OGGETTO_MOD,
    classi_oggetto_compatibili_montaggio,
    genera_html_cariche,
    genera_html_montaggio_classi_oggetto,
)


class GeneraHtmlCaricheLabelTests(TestCase):
    def setUp(self):
        self.aura = Punteggio.objects.create(nome="Aura Tech", sigla="ATE", tipo=AURA)
        self.stat = Statistica.objects.create(
            nome="Cariche tecnologiche",
            sigla="CTK",
            parametro="cariche",
            valore_base_predefinito=5,
        )
        self.infusione = Infusione.objects.create(
            nome="Scan",
            aura_richiesta=self.aura,
            testo="desc",
            statistica_cariche=self.stat,
            tipo_risultato=SCELTA_RISULTATO_POTENZIAMENTO,
        )
        InfusioneStatisticaBase.objects.create(
            infusione=self.infusione,
            statistica=self.stat,
            valore_base=7,
        )

    def test_header_totale_nome_statistica(self):
        html = genera_html_cariche(self.infusione, None)
        self.assertIn("Totale Cariche tecnologiche: 7", html)
        self.assertNotIn("Tot:", html)
        self.assertNotIn("⚡", html)

    def test_senza_statistica_cariche_vuoto(self):
        self.infusione.statistica_cariche = None
        self.infusione.save(update_fields=["statistica_cariche"])
        self.assertEqual(genera_html_cariche(self.infusione, None), "")

    def test_oggetto_con_infusione(self):
        oggetto = Oggetto.objects.create(
            nome="Mod di Scan",
            tipo_oggetto=TIPO_OGGETTO_MOD,
            infusione_generatrice=self.infusione,
            aura=self.aura,
            is_tecnologico=True,
        )
        html = genera_html_cariche(oggetto, None)
        self.assertIn("Totale Cariche tecnologiche: 7", html)


class MontaggioClassiOggettoTests(TestCase):
    def setUp(self):
        self.aura_tech = Punteggio.objects.create(nome="Aura Tecnologica", sigla="ATE", tipo=AURA)
        self.aura_mond = Punteggio.objects.create(nome="Aura Mondana", sigla="AMS", tipo=AURA)
        self.car_nodo = Punteggio.objects.create(nome="Nodo", sigla="NOD", tipo=CARATTERISTICA)
        self.car_castone = Punteggio.objects.create(nome="Castone", sigla="CAS", tipo=CARATTERISTICA)

        self.classe_spada = ClasseOggetto.objects.create(nome="Spada", max_mod_totali=2)
        self.classe_fucile = ClasseOggetto.objects.create(nome="Fucile", max_mod_totali=3)
        self.classe_elmo = ClasseOggetto.objects.create(nome="Elmo", max_mod_totali=1)

        ClasseOggettoLimiteMod.objects.create(
            classe_oggetto=self.classe_spada,
            caratteristica=self.car_nodo,
            max_installabili=2,
        )
        ClasseOggettoLimiteMod.objects.create(
            classe_oggetto=self.classe_fucile,
            caratteristica=self.car_nodo,
            max_installabili=1,
        )
        self.classe_spada.mattoni_materia_permessi.add(self.car_castone)
        self.classe_elmo.mattoni_materia_permessi.add(self.car_castone)

    def test_mod_lista_classi_da_limitazioni(self):
        oggetto = Oggetto.objects.create(
            nome="Mod Nodo",
            tipo_oggetto=TIPO_OGGETTO_MOD,
            is_tecnologico=True,
        )
        OggettoCaratteristica.objects.create(
            oggetto=oggetto, caratteristica=self.car_nodo, valore=1
        )
        nomi = classi_oggetto_compatibili_montaggio(oggetto)
        self.assertEqual(nomi, ["Fucile", "Spada"])
        html = genera_html_montaggio_classi_oggetto(oggetto)
        self.assertIn("Montabile su:", html)
        self.assertIn("Fucile", html)
        self.assertIn("Spada", html)
        self.assertNotIn("Elmo", html)

    def test_materia_lista_classi_da_mattoni_permessi(self):
        oggetto = Oggetto.objects.create(
            nome="Materia Castone",
            tipo_oggetto=TIPO_OGGETTO_MATERIA,
            is_tecnologico=False,
        )
        OggettoCaratteristica.objects.create(
            oggetto=oggetto, caratteristica=self.car_castone, valore=1
        )
        nomi = classi_oggetto_compatibili_montaggio(oggetto)
        self.assertEqual(nomi, ["Elmo", "Spada"])
        html = genera_html_montaggio_classi_oggetto(oggetto)
        self.assertIn("Elmo", html)
        self.assertIn("Spada", html)
        self.assertNotIn("Fucile", html)

    def test_infusione_mod_nel_testo_formattato(self):
        inf = Infusione.objects.create(
            nome="Inf Mod",
            aura_richiesta=self.aura_tech,
            testo="<p>x</p>",
            tipo_risultato=SCELTA_RISULTATO_POTENZIAMENTO,
        )
        InfusioneCaratteristica.objects.create(
            infusione=inf, caratteristica=self.car_nodo, valore=1
        )
        html = inf.TestoFormattato
        self.assertIn("Montabile su:", html)
        self.assertIn("Spada", html)
        self.assertIn("Fucile", html)

    def test_innesto_nessun_blocco_montaggio(self):
        oggetto = Oggetto.objects.create(
            nome="Innesto",
            tipo_oggetto=TIPO_OGGETTO_INNESTO,
            is_tecnologico=True,
        )
        OggettoCaratteristica.objects.create(
            oggetto=oggetto, caratteristica=self.car_nodo, valore=1
        )
        self.assertEqual(genera_html_montaggio_classi_oggetto(oggetto), "")

    def test_infusione_aum_nessun_blocco_montaggio(self):
        inf = Infusione.objects.create(
            nome="Inf Aum",
            aura_richiesta=self.aura_tech,
            testo="x",
            tipo_risultato=SCELTA_RISULTATO_AUMENTO,
        )
        InfusioneCaratteristica.objects.create(
            infusione=inf, caratteristica=self.car_nodo, valore=1
        )
        self.assertEqual(genera_html_montaggio_classi_oggetto(inf), "")

    def test_senza_caratteristiche_vuoto(self):
        oggetto = Oggetto.objects.create(
            nome="Mod vuota",
            tipo_oggetto=TIPO_OGGETTO_MOD,
            is_tecnologico=True,
        )
        self.assertEqual(genera_html_montaggio_classi_oggetto(oggetto), "")
