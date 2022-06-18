# -*- coding: utf-8 -*-

from django.contrib import admin
from django.urls import path
from django.views.generic.base import RedirectView

from djankiserv_app import views

from djankiserv_api.urls import urlpatterns as api_routes
from djankiserv_sync.urls import urlpatterns as sync_routes


def routes():
    routes = []
    routes.append(path("", RedirectView.as_view(url="/admin/")))
    routes.append(path("admin/", admin.site.urls))
    routes.append(path("health", views.health))

    routes += api_routes
    routes += sync_routes
    return routes


urlpatterns = routes()
