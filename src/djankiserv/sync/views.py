# -*- coding: utf-8 -*-

import io
import json
import logging
import os
import time
import zipfile

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from djankiserv.sync import SyncCollectionHandler, full_download, full_upload
from djankiserv.unki import get_data
from djankiserv.unki.collection import Collection
from djankiserv.unki.database import dump_io_to_file

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


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def base_meta(request):
    session = safe_get_session(request)

    if settings.DJANKISERV_GENERATE_TEST_ASSETS:
        session["dump_base"] = os.path.join(settings.DJANKISERV_GENERATE_TEST_ASSETS_DIR, str(time.time()))
        session.save()

    with get_collection(session) as col:
        return JsonResponse(
            {
                "cont": True,
                "hostNum": 1,
                "mod": col.mod,
                "msg": "",
                "musn": col.last_media_usn(),
                "scm": col.scm,
                "ts": int(time.time()),
                "uname": session["name"],
                "usn": col.usn,
            }
        )


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def base_start(request):
    session = safe_get_session(request)
    data = get_data(request)

    dump_io_to_file(session, "start", request)

    with get_collection(session) as col:
        col_handler = SyncCollectionHandler(col)

        # FIXME: for the moment we are just ignoring the 'offset' parameter, hoping it will just work if
        # we only use the V1 scheduler
        output = col_handler.start(min_usn=data.get("minUsn"), lnewer=data.get("lnewer"), offset=data.get("offset"))

        ## The following gets values that are required for subsequent calls in a sync flow
        ## as a side-effect of the start. This obviously needs to be completely rethought!!!
        ##
        ## We also need the dump_base in the media so we set for a first time in meta, as start isn't
        ## called if there is no main db sync needed
        ##
        ## FIXME: this needs serious testing for at least:
        ## - failure and then start again with a new sync
        session["min_usn"] = col_handler.min_usn
        session["max_usn"] = col_handler.max_usn
        session["lnewer"] = col_handler.lnewer
        session.save()

        resp = JsonResponse(output)

    dump_io_to_file(session, "start", resp)

    return resp


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def base_applyGraves(request):
    session = safe_get_session(request)
    data = get_data(request)

    dump_io_to_file(session, "applyGraves", request)

    with get_collection(session) as col:
        col_handler = SyncCollectionHandler(col, session=session)
        col_handler.applyGraves(chunk=data.get("chunk"))

        resp = JsonResponse({})
    dump_io_to_file(session, "applyGraves", resp)

    return resp


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def base_applyChanges(request):
    session = safe_get_session(request)
    data = get_data(request)

    dump_io_to_file(session, "applyChanges", request)

    with get_collection(session) as col:
        col_handler = SyncCollectionHandler(col, session=session)

        ## tests for doing it by chunking rather than all in one go
        # output = col_handler.applyChanges(changes=data.get("changes"))
        # session["tablesLeft"] = col_handler.tablesLeft
        # cache.set(session.skey, session)

        output = col_handler.applyChanges(changes=data.get("changes"))
        resp = JsonResponse(output)

    dump_io_to_file(session, "applyChanges", resp)
    return resp


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def base_chunk(request):
    session = safe_get_session(request)  # performs auth that raises an error if not auth'ed

    dump_io_to_file(session, "chunk", request)

    with get_collection(session) as col:
        col_handler = SyncCollectionHandler(col, session=session)

        ## FIXME: this is where  the chunking needs to happen. The original call was to col_handler.chunk()
        ## which is from a persistent thread which has a database cursor that gets called with chunks of up
        ## to 250 lines, and it can be called as many times as required until there are none left. This is
        ## obviously very stupid in our context. The all_data_to_sync_down updates the db to say that everything
        ## has already been transferred, though in theory the same logic could be used as the cursor but using
        ## a cache value (we can cache the rows returned but not the cursor)

        all_new_data = col_handler.all_data_to_sync_down()

        resp = JsonResponse(all_new_data, safe=False)

    dump_io_to_file(session, "chunk", resp)

    return resp


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def base_applyChunk(request):
    session = safe_get_session(request)
    data = get_data(request)

    dump_io_to_file(session, "applyChunk", request)

    with get_collection(session) as col:
        col_handler = SyncCollectionHandler(col, session=session)

        col_handler.applyChunk(chunk=data.get("chunk"))  # is a void

        resp = JsonResponse({})
    dump_io_to_file(session, "applyChunk", resp)

    return resp


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def base_sanityCheck2(request):
    session = safe_get_session(request)
    data = get_data(request)

    dump_io_to_file(session, "sanityCheck2", request)

    with get_collection(session) as col:
        col_handler = SyncCollectionHandler(col, session=session)
        output = col_handler.sanityCheck2(client=data.get("client"))
        resp = JsonResponse(output)
    dump_io_to_file(session, "sanityCheck2", resp)

    return resp


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def base_finish(request):
    session = safe_get_session(request)

    dump_io_to_file(session, "finish", request)

    with get_collection(session) as col:
        col_handler = SyncCollectionHandler(col, session=session)

        resp = HttpResponse(col_handler.finish())
    dump_io_to_file(session, "finish", resp)

    return resp


@csrf_exempt
@api_view(["POST", "GET"])
@permission_classes((AllowAny,))
def base_hostKey(request):
    data = get_data(request)

    print_request(request)

    username = data.get("u")
    password = data.get("p")

    if not authenticate(username=username, password=password):
        raise PermissionDenied

    s = SessionStore()
    s.create()
    s["skey"] = s.session_key
    s["name"] = username

    s.save()

    return JsonResponse({"key": s.session_key, "hostNum": 1, "host_number": 2})


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def base_upload(request):
    session = safe_get_session(request)

    dump_io_to_file(session, "upload", request)

    db_bytes = get_data(request)["data"]

    resp = HttpResponse(full_upload(db_bytes, session["name"]))
    dump_io_to_file(session, "upload", resp)

    return resp


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def base_download(request):
    session = safe_get_session(request)

    dump_io_to_file(session, "download", request)

    with get_collection(session) as col:
        resp = HttpResponse(full_download(col, session["name"]))
    dump_io_to_file(session, "download", resp)

    return resp


@csrf_exempt
@api_view(["GET", "POST"])
@permission_classes((AllowAny,))
def media_begin(request):
    session = safe_get_session(request)

    if settings.DJANKISERV_GENERATE_TEST_ASSETS:
        session["dump_base_media"] = os.path.join(
            settings.DJANKISERV_GENERATE_TEST_ASSETS_DIR, "media", str(time.time())
        )
        session.save()

    with get_collection(session) as col:
        data = {
            "data": {"sk": session["skey"], "usn": col.last_media_usn()},
            "err": "",
        }
        resp = JsonResponse(data)

    return resp


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def media_mediaChanges(request):
    session = safe_get_session(request)

    dump_io_to_file(session, "mediaChanges", request, is_media=True)

    with get_collection(session) as col:
        data = get_data(request)

        resp = JsonResponse({"data": col.media_changes(data["lastUsn"]), "err": ""})
    dump_io_to_file(session, "mediaChanges", resp, is_media=True)

    return resp


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def media_mediaSanity(request):
    session = safe_get_session(request)

    dump_io_to_file(session, "mediaSanity", request, is_media=True)

    with get_collection(session) as col:
        if col.media_count() == get_data(request)["local"]:
            resp = JsonResponse({"data": "OK", "err": ""})
        else:
            resp = JsonResponse({"data": "FAILED", "err": ""})

    dump_io_to_file(session, "mediaSanity", resp, is_media=True)

    return resp


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def media_uploadChanges(request):
    session = safe_get_session(request)

    dump_io_to_file(session, "uploadChanges", request, is_media=True)

    with get_collection(session) as col:
        data = get_data(request)["data"]

        """
        The zip file contains files the client hasn't synced with the server
        yet ('dirty'), and info on files it has deleted from its own media dir.
        """
        with zipfile.ZipFile(io.BytesIO(data), "r") as z:
            col.check_zip_data(z)
            processed_count = col.adopt_media_changes_from_zip(z)

        resp = JsonResponse({"data": [processed_count, col.last_media_usn()], "err": ""})
    dump_io_to_file(session, "uploadChanges", resp, is_media=True)

    return resp


@csrf_exempt
@api_view(["POST"])
@permission_classes((AllowAny,))
def media_downloadFiles(request):
    SYNC_ZIP_SIZE = int(2.5 * 1024 * 1024)
    SYNC_ZIP_COUNT = 25

    session = safe_get_session(request)
    data = get_data(request)

    dump_io_to_file(session, "downloadFiles", request, is_media=True)

    with get_collection(session) as col:
        files = data["files"]
        flist = {}
        cnt = 0
        sz = 0
        f = io.BytesIO()

        with zipfile.ZipFile(f, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for fname in files:
                z.write(os.path.join(col.media_dir(), fname), str(cnt))
                flist[str(cnt)] = fname
                sz += os.path.getsize(os.path.join(col.media_dir(), fname))
                if sz > SYNC_ZIP_SIZE or cnt > SYNC_ZIP_COUNT:
                    break
                cnt += 1

            z.writestr("_meta", json.dumps(flist))

        resp = HttpResponse(f.getvalue())
    dump_io_to_file(session, "downloadFiles", resp, is_media=True)

    return resp


# DEBUG AND TESTING STUFF
def print_request(request):
    try:
        if settings.DJANKISERV_DEBUG:
            print(pretty_request(request))
    except NameError:
        pass  # we haven't defined it, so can't be interested


def pretty_request(request):

    headers = ""
    for header, value in request.META.items():
        if not header.startswith("HTTP"):
            continue
        # header = "-".join([h.capitalize() for h in header[5:].lower().split("_")])
        header = "-".join([h.capitalize() for h in header.lower().split("_")])
        headers += "{}: {}\n".format(header, value)

    return (
        "{path}\n"
        "{method} HTTP/1.1\n"
        "Content-Length: {content_length}\n"
        "Content-Type: {content_type}\n"
        "{headers}\n\n"
        "{body}\n\n"
    ).format(
        path=request.path,
        method=request.method,
        content_length=request.META.get("CONTENT_LENGTH"),
        content_type=request.META.get("CONTENT_TYPE"),
        headers=headers,
        body=request.data,
    )


# END DEBUG AND TESTING STUFF
