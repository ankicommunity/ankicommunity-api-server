# -*- coding: utf-8 -*-

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from djankiserv_api import views

urlpatterns = [
    path("api/v1/auth/token", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    # TODO: api/v1/auth/revoke
    path("api/v1/notes/add", views.add_notes, name="add_notes"),
    path("api/v1/notes", views.notes, name="notes"),
    path("api/v1/notes/delete", views.delete_notes, name="delete_notes"),
    path("api/v1/decks", views.decks, name="decks"),
    path("api/v1/decks/conf", views.decks_conf, name="decks_conf"),
    path("api/v1/tags", views.tags, name="tags"),
    path("api/v1/models", views.models, name="models")
]
