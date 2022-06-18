# -*- coding: utf-8 -*-

from django.apps import AppConfig


class DjankiservConfig(AppConfig):
    name = "djankiserv"

    def ready(self):
        import djankiserv_api.signals  # noqa # pylint: disable=C0415,W0611
