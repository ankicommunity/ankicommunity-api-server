# -*- coding: utf-8 -*-

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .unki.collection import Collection


@receiver(post_save, sender=User)  # pylint: disable=W0613
def update_profile_signal(sender, instance, created, **kwargs):  # pylint: disable=W0613
    if created:
        # Creates on first loading if it doesn't exist
        # FIXME: so do I still need to do this here?
        Collection(instance.username, settings.DJANKISERV_DATA_ROOT)


@receiver(post_delete, sender=User)
def delete_user_signal(sender, instance, **kwargs):  # pylint: disable=W0613
    Collection.delete(instance.username, settings.DJANKISERV_DATA_ROOT)  # pylint: disable=W0613
