"""
Revisione temporale (max updated_at) per cache condizionale lato client.

Usata da GET /api/personaggi/api/cache-revision/ per evitare di riscaricare
payload pesanti quando i dati sul server non sono cambiati.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.db.models import Max, Q
from django.utils import timezone


def format_revision_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt.isoformat()


def _max_dt(*candidates: Optional[datetime]) -> Optional[datetime]:
    vals = [v for v in candidates if v is not None]
    return max(vals) if vals else None


def revision_punteggi_all():
    from .models import Punteggio

    return Punteggio.objects.aggregate(m=Max("updated_at"))["m"]


def revision_negozio_listino():
    from .models import OggettoBase

    return OggettoBase.objects.filter(in_vendita=True).aggregate(m=Max("updated_at"))["m"]


def revision_personaggi_list(user, view_all: bool):
    from .models import (
        CreditoMovimento,
        Personaggio,
        PuntiCaratteristicaMovimento,
        UserSocialPreference,
    )

    base = Personaggio.objects.filter(proprietario=user)
    if (user.is_staff or user.is_superuser) and view_all:
        base = Personaggio.objects.all()

    m1 = base.aggregate(m=Max("updated_at"))["m"]
    ids = list(base.values_list("pk", flat=True))

    pref = UserSocialPreference.objects.filter(user=user).first()
    pref_ts = pref.updated_at if pref else None

    if not ids:
        return _max_dt(m1, pref_ts)

    m2 = CreditoMovimento.objects.filter(personaggio_id__in=ids).aggregate(m=Max("updated_at"))["m"]
    m3 = PuntiCaratteristicaMovimento.objects.filter(personaggio_id__in=ids).aggregate(
        m=Max("updated_at")
    )["m"]
    return _max_dt(m1, m2, m3, pref_ts)


def revision_personaggio_detail(personaggio_pk: int) -> Optional[datetime]:
    from .models import (
        Abilita,
        Attivata,
        Cerimoniale,
        ConsumabilePersonaggio,
        CreditoMovimento,
        CreazioneConsumabileInCorso,
        EffettoRisorsaTemporaneo,
        Infusione,
        LetturaMessaggio,
        Messaggio,
        ModelloAura,
        Oggetto,
        OggettoInInventario,
        Personaggio,
        PersonaggioAbilita,
        PersonaggioAttivata,
        PersonaggioCerimoniale,
        PersonaggioInfusione,
        PersonaggioModelloAura,
        PersonaggioStatisticaBase,
        PersonaggioTessitura,
        PuntiCaratteristicaMovimento,
        RecuperoRisorsaAttivo,
        TimerRuntime,
        RichiestaAssemblaggio,
        RisorsaStatisticaMovimento,
        Statistica,
        Tessitura,
    )

    if not Personaggio.objects.filter(pk=personaggio_pk).exists():
        return None

    pg_ts = Personaggio.objects.filter(pk=personaggio_pk).aggregate(m=Max("updated_at"))["m"]

    inv_q = {
        "tracciamento_inventario__inventario_id": personaggio_pk,
        "tracciamento_inventario__data_fine__isnull": True,
    }
    o_ts = Oggetto.objects.filter(**inv_q).aggregate(m=Max("updated_at"))["m"]
    t_ts = OggettoInInventario.objects.filter(inventario_id=personaggio_pk).aggregate(
        m=Max("updated_at")
    )["m"]

    def pivot_max(model, fk="personaggio_id"):
        return model.objects.filter(**{fk: personaggio_pk}).aggregate(m=Max("updated_at"))["m"]

    pa = pivot_max(PersonaggioAbilita)
    pat = pivot_max(PersonaggioAttivata)
    pi = pivot_max(PersonaggioInfusione)
    pt = pivot_max(PersonaggioTessitura)
    pcer = pivot_max(PersonaggioCerimoniale)
    pm = pivot_max(PersonaggioModelloAura)
    psb = pivot_max(PersonaggioStatisticaBase)
    cred = pivot_max(CreditoMovimento)
    pcm = pivot_max(PuntiCaratteristicaMovimento)
    rsm = pivot_max(RisorsaStatisticaMovimento)
    rra = pivot_max(RecuperoRisorsaAttivo)
    trt = pivot_max(TimerRuntime)
    ert = pivot_max(EffettoRisorsaTemporaneo)
    cc = pivot_max(CreazioneConsumabileInCorso)
    cons = pivot_max(ConsumabilePersonaggio)
    lm = pivot_max(LetturaMessaggio)

    ra = RichiestaAssemblaggio.objects.filter(
        Q(committente_id=personaggio_pk) | Q(artigiano_id=personaggio_pk)
    ).aggregate(m=Max("updated_at"))["m"]

    try:
        pg = Personaggio.objects.only("id").get(pk=personaggio_pk)
        gruppi_id = list(pg.gruppi_appartenenza.values_list("id", flat=True))
    except Personaggio.DoesNotExist:
        gruppi_id = []

    mq = Q(tipo_messaggio=Messaggio.TIPO_BROADCAST) | Q(destinatario_personaggio_id=personaggio_pk)
    if gruppi_id:
        mq |= Q(tipo_messaggio=Messaggio.TIPO_GRUPPO, destinatario_gruppo_id__in=gruppi_id)
    msg_ts = Messaggio.objects.filter(mq).aggregate(m=Max("updated_at"))["m"]

    st_ts = Statistica.objects.filter(is_primaria=True).aggregate(m=Max("updated_at"))["m"]

    cat_ts = _max_dt(
        Abilita.objects.aggregate(m=Max("updated_at"))["m"],
        Infusione.objects.aggregate(m=Max("updated_at"))["m"],
        Tessitura.objects.aggregate(m=Max("updated_at"))["m"],
        Cerimoniale.objects.aggregate(m=Max("updated_at"))["m"],
        Attivata.objects.aggregate(m=Max("updated_at"))["m"],
        ModelloAura.objects.aggregate(m=Max("updated_at"))["m"],
    )

    return _max_dt(
        pg_ts,
        o_ts,
        t_ts,
        pa,
        pat,
        pi,
        pt,
        pcer,
        pm,
        psb,
        cred,
        pcm,
        rsm,
        rra,
        trt,
        ert,
        cc,
        cons,
        ra,
        lm,
        msg_ts,
        st_ts,
        cat_ts,
    )
