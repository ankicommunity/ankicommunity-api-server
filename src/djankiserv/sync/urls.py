# -*- coding: utf-8 -*-

from django.conf import settings
from django.urls import path

from . import views

urlpatterns = [
    # sync urls
    path(settings.DJANKISERV_SYNC_URLBASE + "start", views.base_start, name="sync_start"),
    path(settings.DJANKISERV_SYNC_URLBASE + "applyChanges", views.base_applyChanges, name="sync_applyChanges"),
    path(settings.DJANKISERV_SYNC_URLBASE + "applyGraves", views.base_applyGraves, name="sync_applyGraves"),
    path(settings.DJANKISERV_SYNC_URLBASE + "chunk", views.base_chunk, name="sync_chunk"),
    path(settings.DJANKISERV_SYNC_URLBASE + "applyChunk", views.base_applyChunk, name="sync_applyChunk"),
    path(settings.DJANKISERV_SYNC_URLBASE + "sanityCheck2", views.base_sanityCheck2, name="sync_sanityCheck2"),
    path(settings.DJANKISERV_SYNC_URLBASE + "finish", views.base_finish, name="sync_finish"),
    path(settings.DJANKISERV_SYNC_URLBASE + "meta", views.base_meta, name="meta"),
    path(settings.DJANKISERV_SYNC_URLBASE + "hostKey", views.base_hostKey, name="hostKey"),
    path(settings.DJANKISERV_SYNC_URLBASE + "upload", views.base_upload, name="upload"),
    path(settings.DJANKISERV_SYNC_URLBASE + "download", views.base_download, name="download"),
    path(settings.DJANKISERV_SYNC_MEDIA_URLBASE + "begin", views.media_begin, name="media_begin"),
    path(settings.DJANKISERV_SYNC_MEDIA_URLBASE + "mediaChanges", views.media_mediaChanges, name="media_mediaChanges"),
    path(settings.DJANKISERV_SYNC_MEDIA_URLBASE + "mediaSanity", views.media_mediaSanity, name="media_mediaSanity"),
    path(
        settings.DJANKISERV_SYNC_MEDIA_URLBASE + "uploadChanges", views.media_uploadChanges, name="media_uploadChanges"
    ),
    path(
        settings.DJANKISERV_SYNC_MEDIA_URLBASE + "downloadFiles", views.media_downloadFiles, name="media_downloadFiles"
    ),
]
