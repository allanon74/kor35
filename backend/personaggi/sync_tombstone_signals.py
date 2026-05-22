from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from kor35.sync_tombstone import (
    clear_tombstone,
    instance_sync_label,
    record_tombstone_for_instance,
)


@receiver(pre_delete)
def sync_tombstone_on_pre_delete(sender, instance, **kwargs):
    record_tombstone_for_instance(instance)


@receiver(post_save)
def sync_tombstone_clear_on_save(sender, instance, **kwargs):
    """Record vivo di nuovo: rimuove tombstone obsoleto."""
    model_label = instance_sync_label(instance)
    if not model_label:
        return
    clear_tombstone(model_label, instance.sync_id)
