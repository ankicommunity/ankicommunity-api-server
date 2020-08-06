# -*- coding: utf-8 -*-

import djankiserv.api.urls
import djankiserv.sync.urls

urlpatterns = djankiserv.sync.urls.urlpatterns + djankiserv.api.urls.urlpatterns
