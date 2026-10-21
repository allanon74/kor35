"""
Bonus caratteristica contestuali e abilità conferite dagli oggetti attivi.

Il punto contestuale non entra in caratteristiche_base: vale solo per i tetti
di creazione/acquisto e per le formule del tipo (e delle aure) indicati.
L'abilità conferita segue Oggetto.is_active() e non diventa un possesso permanente.
"""

from django.core.exceptions import ValidationError
from django.db.models import Prefetch, Q


TIPI_TECNICA = ("TES", "INF", "CER")

_FLAG_PER_TIPO = {
    "TES": "vale_tessiture",
    "INF": "vale_infusioni",
    "CER": "vale_cerimoniali",
}


def _tipo_normalizzato(tipo):
    tipo = (tipo or "").strip().upper()
    if tipo not in TIPI_TECNICA:
        return ""
    return tipo


def bonus_combacia(bonus, tipo, aure):
    """True se il bonus vale per il tipo tecnica e per almeno un'aura indicata."""
    tipo = _tipo_normalizzato(tipo)
    flag = _FLAG_PER_TIPO.get(tipo)
    if not flag or not getattr(bonus, flag, False):
        return False
    limite = list(bonus.aure.all())
    if not limite:
        return True
    ids = {a.pk for a in limite}
    return any(getattr(aura, "pk", None) in ids for aura in (aure or []) if aura is not None)


def _aure_contesto(*aure):
    return [aura for aura in aure if aura is not None]


def sync_bonus_contestuali(parent, rows, fk_name):
    """Sostituisce i bonus del parent. rows=None lascia invariato."""
    if rows is None:
        return
    from personaggi.models import BonusCaratteristicaContestuale

    parent.bonus_caratteristica_contestuali.all().delete()
    for raw in rows:
        caratteristica = raw.get("caratteristica")
        if not caratteristica:
            continue
        vale_tessiture = bool(raw.get("vale_tessiture"))
        vale_infusioni = bool(raw.get("vale_infusioni"))
        vale_cerimoniali = bool(raw.get("vale_cerimoniali"))
        if not (vale_tessiture or vale_infusioni or vale_cerimoniali):
            raise ValidationError(
                "Ogni bonus caratteristica contestuale deve valere per almeno un ambito "
                "(tessiture, infusioni o cerimoniali)."
            )
        try:
            valore = int(raw.get("valore") or 0)
        except (TypeError, ValueError):
            valore = 0
        if valore < 1:
            raise ValidationError(
                "Il valore del bonus caratteristica contestuale deve essere almeno 1."
            )
        bonus = BonusCaratteristicaContestuale.objects.create(
            **{fk_name: parent},
            caratteristica=caratteristica,
            valore=valore,
            vale_tessiture=vale_tessiture,
            vale_infusioni=vale_infusioni,
            vale_cerimoniali=vale_cerimoniali,
        )
        aure = raw.get("aure") or []
        if aure:
            bonus.aure.set(aure)
            bonus.save(update_fields=["updated_at"])


def sync_abilita_conferite(parent, rows, fk_name):
    """Sostituisce le abilità conferite dal parent. rows=None lascia invariato."""
    if rows is None:
        return
    from personaggi.models import OggettoAbilitaConferita

    parent.abilita_conferite.all().delete()
    visti = set()
    for raw in rows:
        abilita = raw.get("abilita")
        if not abilita or abilita.pk in visti:
            continue
        visti.add(abilita.pk)
        OggettoAbilitaConferita.objects.create(**{fk_name: parent}, abilita=abilita)


def copia_effetti_su_oggetto(sorgente, oggetto):
    """
    Copia bonus contestuali e abilità conferite da un'infusione o da un template
    sull'istanza Oggetto. Le righe già presenti sull'istanza vengono sostituite.
    """
    from personaggi.models import BonusCaratteristicaContestuale, OggettoAbilitaConferita

    oggetto.bonus_caratteristica_contestuali.all().delete()
    oggetto.abilita_conferite.all().delete()
    for row in sorgente.bonus_caratteristica_contestuali.prefetch_related("aure").all():
        nuovo = BonusCaratteristicaContestuale.objects.create(
            oggetto=oggetto,
            caratteristica=row.caratteristica,
            valore=row.valore,
            vale_tessiture=row.vale_tessiture,
            vale_infusioni=row.vale_infusioni,
            vale_cerimoniali=row.vale_cerimoniali,
        )
        aure = list(row.aure.all())
        if aure:
            nuovo.aure.set(aure)
    for link in sorgente.abilita_conferite.all():
        OggettoAbilitaConferita.objects.create(oggetto=oggetto, abilita=link.abilita)


def _prefetch_effetti_oggetto():
    from personaggi.models import BonusCaratteristicaContestuale, Oggetto, OggettoAbilitaConferita

    bonus_qs = BonusCaratteristicaContestuale.objects.select_related("caratteristica").prefetch_related("aure")
    abilita_qs = OggettoAbilitaConferita.objects.select_related("abilita")
    figli = Oggetto.objects.select_related(
        "infusione_generatrice",
        "aura",
        "ospitato_su",
        "ospitato_su__infusione_generatrice",
        "ospitato_su__aura",
    ).prefetch_related(
        Prefetch("bonus_caratteristica_contestuali", queryset=bonus_qs),
        Prefetch("abilita_conferite", queryset=abilita_qs),
    )
    return Prefetch("potenziamenti_installati", queryset=figli), bonus_qs, abilita_qs


def iter_oggetti_attivi(personaggio):
    """
    Oggetti in inventario con is_active() e, per ciascuno, i potenziamenti attivi.
    Mod e Materia montate non sono in inventario: arrivano solo dal host.
    """
    prefetch_figli, bonus_qs, abilita_qs = _prefetch_effetti_oggetto()
    oggetti = (
        personaggio.get_oggetti()
        .select_related("infusione_generatrice", "aura", "ospitato_su")
        .prefetch_related(
            prefetch_figli,
            Prefetch("bonus_caratteristica_contestuali", queryset=bonus_qs),
            Prefetch("abilita_conferite", queryset=abilita_qs),
        )
    )
    for oggetto in oggetti:
        if not oggetto.is_active():
            continue
        yield oggetto
        for figlio in oggetto.potenziamenti_installati.all():
            if figlio.is_active():
                yield figlio


def abilita_ids_conferite_attive(personaggio):
    cached = getattr(personaggio, "_abilita_conferite_attive_cache", None)
    if cached is not None:
        return cached
    ids = set()
    for oggetto in iter_oggetti_attivi(personaggio):
        for link in oggetto.abilita_conferite.all():
            if link.abilita_id:
                ids.add(link.abilita_id)
    personaggio._abilita_conferite_attive_cache = ids
    return ids


def ids_abilita_meccaniche(personaggio, *, include_camaleonte=True):
    """Possesso reale più abilità conferite da oggetti attivi (e forma camaleonte)."""
    from personaggi.models import PersonaggioAbilita

    ids = set(
        PersonaggioAbilita.objects.filter(personaggio=personaggio).values_list("abilita_id", flat=True)
    )
    ids |= abilita_ids_conferite_attive(personaggio)
    if include_camaleonte:
        forma = personaggio.get_forma_camaleonte_del_giorno()
        if forma is not None:
            ids.add(forma.id)
    return ids


def ha_flag_abilita(personaggio, **flags):
    from personaggi.models import Abilita

    if personaggio.abilita_possedute.filter(**flags).exists():
        return True
    ids = abilita_ids_conferite_attive(personaggio)
    if not ids:
        return False
    return Abilita.objects.filter(id__in=ids, **flags).exists()


def _bonus_candidati(personaggio):
    """Bonus da abilità effettive e da oggetti attivi, senza doppioni."""
    from personaggi.models import BonusCaratteristicaContestuale

    visti = set()
    ids_abilita = ids_abilita_meccaniche(personaggio)
    if ids_abilita:
        qs = (
            BonusCaratteristicaContestuale.objects.filter(abilita_id__in=ids_abilita)
            .select_related("caratteristica")
            .prefetch_related("aure")
        )
        for bonus in qs:
            visti.add(bonus.pk)
            yield bonus
    for oggetto in iter_oggetti_attivi(personaggio):
        for bonus in oggetto.bonus_caratteristica_contestuali.all():
            if bonus.pk in visti:
                continue
            visti.add(bonus.pk)
            yield bonus


def caratteristiche_per_contesto(personaggio, tipo, aura=None, aura_secondaria=None):
    """
    caratteristiche_base più i bonus contestuali che combaciano.
    I derivati (CaratteristicaModificatore) continuano a leggere solo la base.
    """
    tipo = _tipo_normalizzato(tipo)
    result = {k: int(v or 0) for k, v in (personaggio.caratteristiche_base or {}).items()}
    if not tipo:
        return result
    aure = _aure_contesto(aura, aura_secondaria)
    for bonus in _bonus_candidati(personaggio):
        if not bonus_combacia(bonus, tipo, aure):
            continue
        nome = bonus.caratteristica.nome
        result[nome] = int(result.get(nome, 0) or 0) + int(bonus.valore or 0)
    return result


def applica_caratteristiche_contesto(personaggio, eval_context, context):
    """Sovrascrive nel contesto formula i nomi caratteristica col valore contestuale."""
    if not personaggio or not context:
        return
    tipo = context.get("tipo_tecnica")
    if not tipo:
        return
    valori = caratteristiche_per_contesto(
        personaggio,
        tipo,
        context.get("aura"),
        context.get("aura_secondaria"),
    )
    for nome, valore in valori.items():
        eval_context[nome] = valore


def payload_bonus_personaggio(personaggio):
    """Elenco per la scheda e per l'editor proposte. Non è il punteggio globale."""
    righe = []
    for bonus in _bonus_candidati(personaggio):
        righe.append(
            {
                "caratteristica_id": bonus.caratteristica_id,
                "caratteristica_nome": bonus.caratteristica.nome,
                "valore": int(bonus.valore or 0),
                "vale_tessiture": bool(bonus.vale_tessiture),
                "vale_infusioni": bool(bonus.vale_infusioni),
                "vale_cerimoniali": bool(bonus.vale_cerimoniali),
                "aure": [
                    {"id": aura.id, "nome": aura.nome, "sigla": aura.sigla}
                    for aura in bonus.aure.all()
                ],
            }
        )
    return righe


def q_abilita_effettive(personaggio):
    """Filtro Q per effetti meccanici, non per il possesso in acquisto."""
    ids = abilita_ids_conferite_attive(personaggio)
    possesso = Q(abilita__personaggioabilita__personaggio=personaggio)
    if not ids:
        return possesso
    return possesso | Q(abilita_id__in=ids)
