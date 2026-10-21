"""Bonus caratteristica contestuali e abilità conferite, senza toccare is_active()."""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APITestCase

from personaggi.models import (
    AURA,
    CARATTERISTICA,
    MODIFICATORE_ADDITIVO,
    TIPO_OGGETTO_FISICO,
    TIPO_OGGETTO_MOD,
    Abilita,
    AbilitaStatistica,
    BonusCaratteristicaContestuale,
    Campagna,
    CaratteristicaModificatore,
    Infusione,
    InfusioneCaratteristica,
    InfusioneStatistica,
    InfusioneStatisticaBase,
    Oggetto,
    OggettoAbilitaConferita,
    OggettoStatistica,
    OggettoStatisticaBase,
    Personaggio,
    PersonaggioAbilita,
    Punteggio,
    Statistica,
    Tessitura,
    TessituraCaratteristica,
    abilita_punteggio,
    formatta_testo_generico,
)
from personaggi.services import GestioneCraftingService, GestioneOggettiService


class BonusContestoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bonus-ctx-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Bonus Ctx", proprietario=self.user)
        self.ca = Punteggio.objects.create(nome="ForzaCtx", sigla="FCX", tipo=CARATTERISTICA)
        self.aura = Punteggio.objects.create(nome="Aura Magica Ctx", sigla="AMX", tipo=AURA)
        self.altra = Punteggio.objects.create(nome="Aura Arcana Ctx", sigla="AAX", tipo=AURA)
        self.stat_pv = Statistica.objects.create(
            nome="Punti Vita Ctx", sigla="PVX", parametro="pvctx", valore_base_predefinito=0
        )
        self.stat_bonus = Statistica.objects.create(
            nome="Bonus Oggetto Ctx", sigla="BOX", parametro="boxctx", valore_base_predefinito=0
        )
        grant = Abilita.objects.create(
            nome="Grant base ctx", caratteristica=self.ca, costo_pc=0, costo_crediti=0
        )
        abilita_punteggio.objects.create(abilita=grant, punteggio=self.ca, valore=2)
        abilita_punteggio.objects.create(abilita=grant, punteggio=self.aura, valore=5)
        abilita_punteggio.objects.create(abilita=grant, punteggio=self.altra, valore=5)
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=grant)
        CaratteristicaModificatore.objects.create(
            caratteristica=self.ca,
            statistica_modificata=self.stat_pv,
            modificatore=Decimal("1"),
            ogni_x_punti=1,
        )
        self.abilita_bonus = Abilita.objects.create(
            nome="Sguardo contestuale", caratteristica=self.ca, costo_pc=0, costo_crediti=0
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.abilita_bonus)

    def fresh(self):
        return Personaggio.objects.get(pk=self.pg.pk)

    def _bonus(self, *, parent, fk, aure=(), **flags):
        flags.setdefault("valore", 1)
        bonus = BonusCaratteristicaContestuale.objects.create(
            **{fk: parent},
            caratteristica=self.ca,
            **flags,
        )
        if aure:
            bonus.aure.set(aure)
        return bonus

    def test_abilita_bonus_non_entra_nei_derivati(self):
        self._bonus(parent=self.abilita_bonus, fk="abilita", vale_tessiture=True)
        pg = self.fresh()
        self.assertEqual(pg.caratteristiche_base.get("ForzaCtx"), 2)
        self.assertEqual(pg.caratteristiche_per_contesto("TES", self.aura).get("ForzaCtx"), 3)
        self.assertEqual(pg.caratteristiche_per_contesto("INF", self.aura).get("ForzaCtx"), 2)
        self.assertEqual(pg.get_valore_statistica("PVX"), 2)

    def test_filtro_aura_e_aure_vuote(self):
        self._bonus(parent=self.abilita_bonus, fk="abilita", vale_tessiture=True, aure=[self.aura])
        self._bonus(parent=self.abilita_bonus, fk="abilita", vale_infusioni=True, valore=2)
        pg = self.fresh()
        self.assertEqual(pg.caratteristiche_per_contesto("TES", self.aura).get("ForzaCtx"), 3)
        self.assertEqual(pg.caratteristiche_per_contesto("TES", self.altra).get("ForzaCtx"), 2)
        self.assertEqual(
            pg.caratteristiche_per_contesto("INF", self.altra, self.aura).get("ForzaCtx"),
            4,
        )

    def test_oggetto_equipaggiato_e_mod_montata(self):
        self._bonus(parent=self.abilita_bonus, fk="abilita", vale_tessiture=True)
        fisico = Oggetto.objects.create(
            nome="Spada ctx", tipo_oggetto=TIPO_OGGETTO_FISICO, is_equipaggiato=False, aura=self.aura
        )
        fisico.sposta_in_inventario(self.pg)
        self._bonus(parent=fisico, fk="oggetto", vale_tessiture=True)
        pg = self.fresh()
        self.assertEqual(pg.caratteristiche_per_contesto("TES", self.aura).get("ForzaCtx"), 3)

        fisico.is_equipaggiato = True
        fisico.save(update_fields=["is_equipaggiato", "updated_at"])
        pg = self.fresh()
        self.assertTrue(fisico.is_active())
        self.assertEqual(pg.caratteristiche_per_contesto("TES", self.aura).get("ForzaCtx"), 4)

        mod = Oggetto.objects.create(
            nome="Mod ctx", tipo_oggetto=TIPO_OGGETTO_MOD, aura=self.aura, ospitato_su=fisico
        )
        self._bonus(parent=mod, fk="oggetto", vale_infusioni=True)
        pg = self.fresh()
        self.assertTrue(mod.is_active())
        self.assertEqual(pg.caratteristiche_per_contesto("INF", self.aura).get("ForzaCtx"), 3)

        mod.ospitato_su = None
        mod.save(update_fields=["ospitato_su", "updated_at"])
        pg = self.fresh()
        self.assertFalse(mod.is_active())
        self.assertEqual(pg.caratteristiche_per_contesto("INF", self.aura).get("ForzaCtx"), 2)

    def test_abilita_conferita_non_e_possesso_ma_applica_effetti(self):
        conferita = Abilita.objects.create(
            nome="Vista conferita", caratteristica=self.ca, costo_pc=0, costo_crediti=0
        )
        abilita_punteggio.objects.create(abilita=conferita, punteggio=self.ca, valore=1)
        AbilitaStatistica.objects.create(
            abilita=conferita,
            statistica=self.stat_bonus,
            valore=Decimal("4"),
            tipo_modificatore=MODIFICATORE_ADDITIVO,
        )
        fisico = Oggetto.objects.create(
            nome="Anello ctx", tipo_oggetto=TIPO_OGGETTO_FISICO, is_equipaggiato=True, aura=self.aura
        )
        fisico.sposta_in_inventario(self.pg)
        OggettoAbilitaConferita.objects.create(oggetto=fisico, abilita=conferita)

        pg = self.fresh()
        self.assertFalse(pg.abilita_possedute.filter(pk=conferita.pk).exists())
        self.assertEqual(pg.caratteristiche_base.get("ForzaCtx"), 3)
        self.assertEqual(pg.get_valore_statistica("PVX"), 3)
        self.assertEqual(pg.modificatori_calcolati.get("boxctx", {}).get("add"), 4)

        fisico.is_equipaggiato = False
        fisico.save(update_fields=["is_equipaggiato", "updated_at"])
        pg = self.fresh()
        self.assertEqual(pg.caratteristiche_base.get("ForzaCtx"), 2)
        self.assertEqual(pg.modificatori_calcolati.get("boxctx", {}).get("add", 0), 0)

    def test_valida_acquisto_e_formula_usano_il_contesto(self):
        self._bonus(parent=self.abilita_bonus, fk="abilita", vale_tessiture=True, aure=[self.aura])
        tecnica = Tessitura.objects.create(nome="Tela ctx", aura_richiesta=self.aura, formula="{ForzaCtx}")
        TessituraCaratteristica.objects.create(tessitura=tecnica, caratteristica=self.ca, valore=3)
        pg = self.fresh()
        ok, msg = pg.valida_acquisto_tecnica(tecnica)
        self.assertTrue(ok, msg)

        solo_altrove = BonusCaratteristicaContestuale.objects.get(abilita=self.abilita_bonus)
        solo_altrove.aure.set([self.altra])
        pg = self.fresh()
        ok, msg = pg.valida_acquisto_tecnica(tecnica)
        self.assertFalse(ok, msg)

        solo_altrove.aure.set([self.aura])
        pg = self.fresh()
        html = formatta_testo_generico(
            "{ForzaCtx}",
            personaggio=pg,
            context={"tipo_tecnica": "TES", "aura": self.aura},
        )
        self.assertIn("3", html)
        base_html = formatta_testo_generico("{ForzaCtx}", personaggio=pg, context={})
        self.assertIn("2", base_html)
        self.assertNotIn(">3<", base_html)

    def test_forgiatura_usa_il_bonus_assemblaggio_no(self):
        aura_ams = Punteggio.objects.create(nome="Aura Mondana Ctx", sigla="AMS", tipo=AURA)
        aura_sec = Punteggio.objects.create(nome="Aura Sec Ctx", sigla="ASX", tipo=AURA)
        grant = self.pg.abilita_possedute.get(nome="Grant base ctx")
        abilita_punteggio.objects.create(abilita=grant, punteggio=aura_ams, valore=5)
        abilita_punteggio.objects.create(abilita=grant, punteggio=aura_sec, valore=5)
        self._bonus(parent=self.abilita_bonus, fk="abilita", vale_infusioni=True)
        infusione = Infusione.objects.create(
            nome="Materia ctx",
            aura_richiesta=self.aura,
            aura_infusione=aura_sec,
            tipo_risultato="POT",
        )
        componente = InfusioneCaratteristica.objects.create(
            infusione=infusione, caratteristica=self.ca, valore=3
        )
        pg = self.fresh()
        ok, msg = GestioneCraftingService.verifica_competenza_forgiatura(pg, infusione)
        self.assertTrue(ok, msg)
        ok_asm, msg_asm = GestioneOggettiService._verifica_competenza_base(
            pg, infusione.livello, False, [componente]
        )
        self.assertFalse(ok_asm, msg_asm)
        self.assertIn("ForzaCtx", msg_asm)

    def test_infusione_copia_stats_bonus_e_is_active_invariato(self):
        infusione = Infusione.objects.create(
            nome="Lama ctx",
            testo="taglio",
            aura_richiesta=self.aura,
            durata_attivazione=0,
        )
        InfusioneStatisticaBase.objects.create(
            infusione=infusione, statistica=self.stat_bonus, valore_base=2
        )
        InfusioneStatistica.objects.create(
            infusione=infusione,
            statistica=self.stat_pv,
            valore=Decimal("4"),
            tipo_modificatore=MODIFICATORE_ADDITIVO,
        )
        self._bonus(parent=infusione, fk="infusione", vale_infusioni=True, aure=[self.aura])
        conferita = Abilita.objects.create(
            nome="Lama viva", caratteristica=self.ca, costo_pc=0, costo_crediti=0
        )
        OggettoAbilitaConferita.objects.create(infusione=infusione, abilita=conferita)

        oggetto = GestioneOggettiService.crea_oggetto_da_infusione(infusione, self.pg)
        self.assertEqual(
            OggettoStatisticaBase.objects.get(oggetto=oggetto, statistica=self.stat_bonus).valore_base,
            2,
        )
        self.assertEqual(
            OggettoStatistica.objects.get(oggetto=oggetto, statistica=self.stat_pv).valore,
            Decimal("4"),
        )
        self.assertEqual(oggetto.bonus_caratteristica_contestuali.count(), 1)
        self.assertEqual(oggetto.abilita_conferite.get().abilita_id, conferita.id)

        oggetto.tipo_oggetto = TIPO_OGGETTO_FISICO
        oggetto.is_equipaggiato = True
        oggetto.save(update_fields=["tipo_oggetto", "is_equipaggiato", "updated_at"])
        self.assertTrue(oggetto.is_active())
        pg = self.fresh()
        self.assertEqual(pg.caratteristiche_per_contesto("INF", oggetto.aura, self.aura).get("ForzaCtx"), 3)

        oggetto.is_equipaggiato = False
        oggetto.save(update_fields=["is_equipaggiato", "updated_at"])
        self.assertFalse(oggetto.is_active())

        a_tempo = Infusione.objects.create(
            nome="Lampo ctx",
            aura_richiesta=self.aura,
            durata_attivazione=30,
        )
        temporaneo = GestioneOggettiService.crea_oggetto_da_infusione(a_tempo, self.pg)
        temporaneo.tipo_oggetto = TIPO_OGGETTO_FISICO
        temporaneo.is_equipaggiato = True
        temporaneo.data_fine_attivazione = None
        temporaneo.save(update_fields=["tipo_oggetto", "is_equipaggiato", "data_fine_attivazione", "updated_at"])
        self.assertFalse(temporaneo.is_active())
        temporaneo.data_fine_attivazione = timezone.now() + timedelta(seconds=20)
        temporaneo.save(update_fields=["data_fine_attivazione", "updated_at"])
        self.assertTrue(temporaneo.is_active())


class StaffBonusContestoApiTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff-bonus-ctx", password="x", is_staff=True, is_superuser=True
        )
        self.client.force_authenticate(user=self.staff)
        self.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={"nome": "Kor35", "is_default": True, "is_base": True, "attiva": True},
        )
        self.aura = Punteggio.objects.create(nome="Aura Staff Ctx", sigla="ASC", tipo=AURA)
        self.ca = Punteggio.objects.create(nome="Precisione Ctx", sigla="PCX", tipo=CARATTERISTICA)
        self.abilita = Abilita.objects.create(
            nome="Conferita staff", caratteristica=self.ca, costo_pc=0, costo_crediti=0
        )
        self.headers = {"HTTP_X_CAMPAGNA": self.campagna.slug}

    def test_create_e_patch_parziale_non_cancella(self):
        payload = {
            "nome": "Inf bonus",
            "testo": "base",
            "aura_richiesta": self.aura.id,
            "bonus_caratteristica_contestuali": [
                {
                    "caratteristica": self.ca.id,
                    "valore": 1,
                    "vale_tessiture": False,
                    "vale_infusioni": True,
                    "vale_cerimoniali": False,
                    "aure": [{"id": self.aura.id, "nome": self.aura.nome}],
                }
            ],
            "abilita_conferite": [{"abilita": self.abilita.id}],
        }
        created = self.client.post(
            "/api/personaggi/api/staff/infusioni/",
            payload,
            format="json",
            **self.headers,
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        infusione = Infusione.objects.get(pk=created.data["id"])
        self.assertEqual(infusione.bonus_caratteristica_contestuali.count(), 1)
        self.assertEqual(list(infusione.bonus_caratteristica_contestuali.get().aure.values_list("id", flat=True)), [self.aura.id])
        self.assertEqual(infusione.abilita_conferite.get().abilita_id, self.abilita.id)

        patched = self.client.patch(
            f"/api/personaggi/api/staff/infusioni/{infusione.id}/",
            {"nome": "Inf bonus rinominata"},
            format="json",
            **self.headers,
        )
        self.assertEqual(patched.status_code, status.HTTP_200_OK, patched.data)
        infusione.refresh_from_db()
        self.assertEqual(infusione.nome, "Inf bonus rinominata")
        self.assertEqual(infusione.bonus_caratteristica_contestuali.count(), 1)
        self.assertEqual(infusione.abilita_conferite.count(), 1)

        cleared = self.client.patch(
            f"/api/personaggi/api/staff/infusioni/{infusione.id}/",
            {"bonus_caratteristica_contestuali": [], "abilita_conferite": []},
            format="json",
            **self.headers,
        )
        self.assertEqual(cleared.status_code, status.HTTP_200_OK, cleared.data)
        self.assertEqual(infusione.bonus_caratteristica_contestuali.count(), 0)
        self.assertEqual(infusione.abilita_conferite.count(), 0)
