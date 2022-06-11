# -*- coding: utf-8 -*-

import djankiserv_api.urls
import djankiserv_sync.urls

urlpatterns = djankiserv_sync.urls.urlpatterns + djankiserv_api.urls.urlpatterns
