# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import PermissionDenied

from djankiserv_unki.collection import Collection
from djankiserv_utils import print_request


logger = logging.getLogger("djankiserv.views")

## In order to be compatible with the clients and use the bespoke auth, we need to tell DRF not to manage
## auth for the xSYNC methods


def get_session(request):
    return SessionStore(session_key=(request.POST.get("k") or request.GET.get("k") or request.POST.get("sk")))


def safe_get_session(request):
    # Get and verify the session
    print_request(request)

    session = get_session(request)

    if not session.get("skey"):  # FIXME: there is probably a better way than this
        raise PermissionDenied

    return session


def get_collection(session):
    return Collection(session["name"], settings.DJANKISERV_DATA_ROOT)
