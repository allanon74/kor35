"""Regressioni sul costo della scheda personaggio (N+1 e scrittura a ogni GET)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from personaggi.models import (
    CARATTERISTICA,
    ELEMENTO,
    Abilita,
    AbilitaStatistica,
    Personaggio,
    PersonaggioAbilita,
    Punteggio,
    Statistica,
)
from personaggi.views import _sync_coma_state


class SyncComaReadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="coma-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Coma", proprietario=self.user)

    def test_senza_coma_non_aggiorna_updated_at(self):
        stamp = Personaggio.objects.get(pk=self.pg.pk).updated_at
        _sync_coma_state(self.pg)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.updated_at, stamp)

    def test_countdown_non_viene_persisto(self):
        end = timezone.now() + timedelta(minutes=10)
        self.pg.impostazioni_ui = {
            "coma_state": {
                "status": "counting",
                "end_at": end.isoformat(),
                "remaining_seconds": 99999,
                "is_paused": False,
                "death_mode": "none",
            }
        }
        self.pg.save(update_fields=["impostazioni_ui", "updated_at"])
        stamp = Personaggio.objects.get(pk=self.pg.pk).updated_at
        result = _sync_coma_state(self.pg)
        self.assertLess(result["coma_state"]["remaining_seconds"], 99999)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.updated_at, stamp)
        self.assertEqual(self.pg.impostazioni_ui["coma_state"]["remaining_seconds"], 99999)

    def test_fine_coma_avvia_rianimazione_e_salva(self):
        end = timezone.now() - timedelta(seconds=5)
        self.pg.impostazioni_ui = {
            "coma_state": {
                "status": "counting",
                "end_at": end.isoformat(),
                "remaining_seconds": 5,
                "is_paused": False,
                "death_mode": "none",
            }
        }
        self.pg.save(update_fields=["impostazioni_ui", "updated_at"])
        stamp = Personaggio.objects.get(pk=self.pg.pk).updated_at
        _sync_coma_state(self.pg)
        self.pg.refresh_from_db()
        self.assertGreater(self.pg.updated_at, stamp)
        self.assertNotIn("coma_state", self.pg.impostazioni_ui or {})
        self.assertEqual(self.pg.impostazioni_ui["rianimazione_state"]["status"], "counting")


class SchedaQueryTests(TestCase):
    def test_caratteristiche_base_una_query_poi_cache(self):
        user = User.objects.create_user(username="scheda-q", password="x")
        pg = Personaggio.objects.create(nome="PG Query", proprietario=user)
        for i in range(8):
            Punteggio.objects.create(nome=f"CarQ{i}", sigla=f"C{i:02d}", tipo=CARATTERISTICA)
            Statistica.objects.create(nome=f"CarQ{i}", sigla=f"S{i:02d}", parametro=f"pq{i}")

        pg.punteggi_base
        with self.assertNumQueries(1):
            first = pg.caratteristiche_base
        with self.assertNumQueries(0):
            second = pg.caratteristiche_base
        self.assertEqual(first, second)
        self.assertIn("CarQ0", first)

    def test_modificatori_contestuali_non_ripetono_query(self):
        user = User.objects.create_user(username="scheda-mod", password="x")
        pg = Personaggio.objects.create(nome="PG Mod", proprietario=user)
        caratt = Punteggio.objects.create(nome="Mente Q", sigla="MEQ", tipo=CARATTERISTICA)
        abilita = Abilita.objects.create(
            nome="Abilita Q", costo_pc=0, costo_crediti=0, caratteristica=caratt
        )
        PersonaggioAbilita.objects.create(personaggio=pg, abilita=abilita)
        stat = Statistica.objects.create(nome="Stat Q", sigla="STQ", parametro="stq")
        elemento = Punteggio.objects.create(nome="Fuoco Q", sigla="FUQ", tipo=ELEMENTO)
        link = AbilitaStatistica.objects.create(
            abilita=abilita,
            statistica=stat,
            valore=2,
            usa_limitazione_elemento=True,
        )
        link.limit_a_elementi.add(elemento)
        ctx = {"elemento": elemento, "livello": 1}

        first = pg.get_modificatori_extra_da_contesto(ctx)
        with self.assertNumQueries(0):
            second = pg.get_modificatori_extra_da_contesto(ctx)
        self.assertEqual(first, second)
        self.assertEqual(first.get("stq", {}).get("add"), 2.0)
