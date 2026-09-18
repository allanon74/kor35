"""
Test conteggio equip per classi oggetto (Gladiatore 2) e Celebrante 2 flat CCO.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from personaggi.models import (
    CARATTERISTICA,
    MODIFICATORE_ADDITIVO,
    SLOT_EQUIP_CONTEGGIO_OGGETTI_MODIFICATI,
    Abilita,
    AbilitaStatistica,
    ClasseOggetto,
    Personaggio,
    PersonaggioAbilita,
    Punteggio,
    Statistica,
    TIPO_OGGETTO_FISICO,
    TIPO_OGGETTO_MATERIA,
    Oggetto,
    OggettoBase,
    calcola_bonus_abilita_slot_equip,
)


class ContaClassiOggettoModificatiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="glad-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Gladiatore", proprietario=self.user)
        self.ca = Punteggio.objects.create(nome="Car Glad", sigla="CGL", tipo=CARATTERISTICA)
        self.dam = Statistica.objects.create(nome="Danni Mischia", sigla="DaM", parametro="dannimis")
        self.classe_spada = ClasseOggetto.objects.create(nome="Spada")
        self.classe_elmo = ClasseOggetto.objects.create(nome="Elmo")

        self.abilita = Abilita.objects.create(
            nome="Gladiatore 2 test",
            caratteristica=self.ca,
            costo_pc=0,
            costo_crediti=0,
        )
        self.link = AbilitaStatistica.objects.create(
            abilita=self.abilita,
            statistica=self.dam,
            valore=0,
            tipo_modificatore=MODIFICATORE_ADDITIVO,
            usa_bonus_slot_equip=True,
            modalita_conteggio_slot_equip=SLOT_EQUIP_CONTEGGIO_OGGETTI_MODIFICATI,
            valore_per_unita_slot_equip=1,
            slot_equip_ammessi=[],
        )
        self.link.classi_oggetto_conteggio.add(self.classe_spada)
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=self.abilita)

        template = OggettoBase.objects.create(nome="Tpl spada", tipo_oggetto=TIPO_OGGETTO_FISICO)
        self.spada = Oggetto.objects.create(
            nome="Spada test",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            slot_fisici_possibili="melee",
            classe_oggetto=self.classe_spada,
            oggetto_base_generatore=template,
        )
        self.spada.sposta_in_inventario(self.pg)
        self.spada.is_equipaggiato = True
        self.spada.slot_equip = "melee"
        self.spada.save(update_fields=["is_equipaggiato", "slot_equip", "updated_at"])

        self.mat = Oggetto.objects.create(
            nome="Materia test",
            tipo_oggetto=TIPO_OGGETTO_MATERIA,
            ospitato_su=self.spada,
        )

        self.elmo = Oggetto.objects.create(
            nome="Elmo test",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            slot_fisici_possibili="head",
            classe_oggetto=self.classe_elmo,
            oggetto_base_generatore=OggettoBase.objects.create(
                nome="Tpl elmo", tipo_oggetto=TIPO_OGGETTO_FISICO
            ),
        )
        self.elmo.sposta_in_inventario(self.pg)
        self.elmo.is_equipaggiato = True
        self.elmo.slot_equip = "head"
        self.elmo.save(update_fields=["is_equipaggiato", "slot_equip", "updated_at"])
        Oggetto.objects.create(
            nome="Materia elmo",
            tipo_oggetto=TIPO_OGGETTO_MATERIA,
            ospitato_su=self.elmo,
        )

    def test_conta_solo_classi_selezionate(self):
        bonus, detail = calcola_bonus_abilita_slot_equip(self.pg, self.link)
        self.assertEqual(bonus, 1.0)
        self.assertIn("1", detail)

    def test_senza_modifica_zero(self):
        self.mat.delete()
        bonus, _ = calcola_bonus_abilita_slot_equip(self.pg, self.link)
        self.assertEqual(bonus, 0.0)
