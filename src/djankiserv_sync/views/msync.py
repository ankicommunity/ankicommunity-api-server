import io
import os
import json
import time
import zipfile

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny

from djankiserv_unki import get_data
from djankiserv_unki.database import dump_io_to_file
from djankiserv_sync.dependencies import safe_get_session, get_collection


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
