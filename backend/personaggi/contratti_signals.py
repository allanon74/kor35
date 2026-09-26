"""Alla morte del cliente apre le penali dei contratti ancora stipulati."""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from personaggi.models import Personaggio


@receiver(pre_save, sender=Personaggio)
def contratti_ricorda_morte(sender, instance, **kwargs):
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and "data_morte" not in update_fields:
        instance._contratti_morte_prima = "skip"
        return
    if not instance.pk:
        instance._contratti_morte_prima = None
        return
    instance._contratti_morte_prima = (
        sender.objects.filter(pk=instance.pk).values_list("data_morte", flat=True).first()
    )


@receiver(post_save, sender=Personaggio)
def contratti_su_morte(sender, instance, **kwargs):
    prima = getattr(instance, "_contratti_morte_prima", "skip")
    if prima == "skip":
        return
    if instance.data_morte and not prima:
        from personaggi.contratti_service import on_personaggio_morto

        on_personaggio_morto(instance)
