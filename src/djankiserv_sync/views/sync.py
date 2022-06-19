import os
import time

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from djankiserv_unki import get_data
from djankiserv_unki.database import dump_io_to_file
from djankiserv_sync import full_upload
from djankiserv_sync import full_download
from djankiserv_sync import SyncCollectionHandler
from djankiserv_sync.dependencies import safe_get_session, get_collection, print_request


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
