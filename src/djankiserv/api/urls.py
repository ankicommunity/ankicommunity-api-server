# -*- coding: utf-8 -*-

from django.conf import settings
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    # JWT
    path(settings.DJANKISERV_API_URLBASE + "token", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path(settings.DJANKISERV_API_URLBASE + "token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    # api urls
    path(settings.DJANKISERV_API_URLBASE + "addNotes", views.add_notes, name="add_notes"),
    path(settings.DJANKISERV_API_URLBASE + "deleteNotes", views.delete_notes, name="delete_notes"),
    path(settings.DJANKISERV_API_URLBASE + "decks", views.decks, name="decks"),
    path(settings.DJANKISERV_API_URLBASE + "decksConf", views.decks_conf, name="decks_conf"),
    path(settings.DJANKISERV_API_URLBASE + "tags", views.tags, name="tags"),
    path(settings.DJANKISERV_API_URLBASE + "models", views.models, name="models"),
    path(settings.DJANKISERV_API_URLBASE + "notes", views.notes, name="notes"),
]
