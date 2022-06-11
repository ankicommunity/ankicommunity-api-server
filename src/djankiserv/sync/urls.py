# -*- coding: utf-8 -*-

from django.urls import path

from . import views

urlpatterns = [
    # /sync
    path("sync/start", views.base_start, name="sync_start"),
    path("sync/applyChanges", views.base_applyChanges, name="sync_applyChanges"),
    path("sync/applyGraves", views.base_applyGraves, name="sync_applyGraves"),
    path("sync/chunk", views.base_chunk, name="sync_chunk"),
    path("sync/applyChunk", views.base_applyChunk, name="sync_applyChunk"),
    path("sync/sanityCheck2", views.base_sanityCheck2, name="sync_sanityCheck2"),
    path("sync/finish", views.base_finish, name="sync_finish"),
    path("sync/meta", views.base_meta, name="meta"),
    path("sync/hostKey", views.base_hostKey, name="hostKey"),
    path("sync/upload", views.base_upload, name="upload"),
    path("sync/download", views.base_download, name="download"),
    # /msync
    path("msync/begin", views.media_begin, name="media_begin"),
    path("msync/mediaChanges", views.media_mediaChanges, name="media_mediaChanges"),
    path("msync/mediaSanity", views.media_mediaSanity, name="media_mediaSanity"),
    path("msync/uploadChanges", views.media_uploadChanges, name="media_uploadChanges"),
    path("msync/downloadFiles", views.media_downloadFiles, name="media_downloadFiles"),
]
