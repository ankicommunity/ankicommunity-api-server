# -*- coding: utf-8 -*-

from django.contrib import admin
from django.urls import path
from django.views.generic.base import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from djankiserv_api import views

from djankiserv_sync.urls import urlpatterns as sync_routes

def routes():
    routes = sync_routes
    routes.append(path("", RedirectView.as_view(url="/admin/")))
    routes.append(path("admin/", admin.site.urls))
    routes.append(path("health", views.health))
    routes.append(path("api/v1/auth/token", TokenObtainPairView.as_view(), name="token_obtain_pair"))
    routes.append(path("api/v1/auth/refresh", TokenRefreshView.as_view(), name="token_refresh"))
    # TODO: api/v1/auth/revoke
    routes.append(path("api/v1/notes/add", views.add_notes, name="add_notes"))
    routes.append(path("api/v1/notes", views.notes, name="notes"))
    routes.append(path("api/v1/notes/delete", views.delete_notes, name="delete_notes"))
    routes.append(path("api/v1/decks", views.decks, name="decks"))
    routes.append(path("api/v1/decks/conf", views.decks_conf, name="decks_conf"))
    routes.append(path("api/v1/tags", views.tags, name="tags"))
    routes.append(path("api/v1/models", views.models, name="models"))
    return routes


urlpatterns = routes()


