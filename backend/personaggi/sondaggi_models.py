"""
Sondaggi giocatore collegati a un Google Form pubblico.

Le domande arrivano dal modulo Google. Le risposte restano nel database
KOR35 (sync edge/master) e, sul nodo online, vengono copiate nel foglio.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from kor35.syncing import SyncableModel


class Sondaggio(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    campagna = models.ForeignKey(
        "personaggi.Campagna",
        on_delete=models.CASCADE,
        related_name="sondaggi",
    )
    titolo = models.CharField(max_length=200)
    descrizione = models.TextField(blank=True, default="")
    google_form_url = models.URLField(max_length=500)
    google_form_id = models.CharField(max_length=128, db_index=True)
    domande = models.JSONField(default=list, blank=True)
    avvisi = models.JSONField(default=list, blank=True)
    attivo = models.BooleanField(
        default=False,
        help_text="Se attivo, i giocatori della campagna vedono il sondaggio nell'app.",
    )
    consenti_modifica = models.BooleanField(
        default=False,
        help_text="Se attivo, il giocatore può aggiornare la propria risposta.",
    )
    inoltra_email = models.BooleanField(
        default=True,
        help_text="Se il modulo Google raccoglie l'email, invia quella dell'account.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Sondaggio"
        verbose_name_plural = "Sondaggi"
        constraints = [
            models.UniqueConstraint(
                fields=["campagna", "google_form_id"],
                name="sondaggio_campagna_form_uniq",
            ),
        ]

    def __str__(self):
        return self.titolo


class RispostaSondaggio(SyncableModel, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sondaggio = models.ForeignKey(
        Sondaggio,
        on_delete=models.CASCADE,
        related_name="risposte",
    )
    personaggio = models.ForeignKey(
        "personaggi.Personaggio",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risposte_sondaggio",
    )
    utente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="risposte_sondaggio",
    )
    risposte = models.JSONField(default=dict, blank=True)
    google_inviato_at = models.DateTimeField(null=True, blank=True)
    google_claim_at = models.DateTimeField(null=True, blank=True)
    google_errore = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Risposta sondaggio"
        verbose_name_plural = "Risposte sondaggio"
        constraints = [
            models.UniqueConstraint(
                fields=["sondaggio", "personaggio"],
                name="risposta_sondaggio_pg_uniq",
            ),
        ]

    def __str__(self):
        nome = getattr(self.personaggio, "nome", None) or "senza personaggio"
        return f"{self.sondaggio_id} · {nome}"
