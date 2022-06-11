# -*- coding: utf-8 -*-

import djankiserv.api.urls
import djankiserv_sync.urls

urlpatterns = djankiserv_sync.urls.urlpatterns + djankiserv.api.urls.urlpatterns
