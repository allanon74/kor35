from django.db.models.signals import post_save
from django.dispatch import receiver

from .mention_tags import sync_comment_tags, sync_post_tags, sync_story_tags
from .models import SocialComment, SocialPost, SocialStory


@receiver(post_save, sender=SocialPost)
def social_post_sync_mention_tags(sender, instance: SocialPost, **kwargs):
    sync_post_tags(instance)


@receiver(post_save, sender=SocialComment)
def social_comment_sync_mention_tags(sender, instance: SocialComment, **kwargs):
    sync_comment_tags(instance)


@receiver(post_save, sender=SocialStory)
def social_story_sync_mention_tags(sender, instance: SocialStory, **kwargs):
    sync_story_tags(instance)
