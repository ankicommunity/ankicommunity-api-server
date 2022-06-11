# -*- coding: utf-8 -*-

import gzip
import io
import json
import os
import pathlib
import pickle
import pkgutil
import sys
import tempfile
import time
from abc import ABC, abstractmethod
from sqlite3 import dbapi2 as sqlite

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import connection
from django.test.client import FakePayload
from django.utils.encoding import force_bytes
from rest_framework.test import APIRequestFactory, APITransactionTestCase

from djankiserv.sync.views import (
    base_applyChanges,
    base_applyChunk,
    base_applyGraves,
    base_chunk,
    base_download,
    base_finish,
    base_hostKey,
    base_meta,
    base_sanityCheck2,
    base_start,
    base_upload,
    media_begin,
    media_downloadFiles,
    media_mediaChanges,
    media_mediaSanity,
    media_uploadChanges,
)
from djankiserv_unki import AnkiDataModel
from djankiserv_unki.database import StandardDB, db_conn

# copied from anki.consts
HTTP_BUF_SIZE = 64 * 1024
SYNC_VER = 9

ANKI_VERSION_STRING = "djankitest,anki_version,anki_other_thing"


class TestRemoteServer(APITransactionTestCase, ABC):
    databases = "__all__"
    USERNAME = "a_username"
    PASSWORD = "a_pass_word"

    @abstractmethod
    def assets_package(self):
        # return 'assets.up/down/api' in subclasses
        pass

    @staticmethod
    def root_assets_package():
        return "assets"

    def setUp(self):
        # mysql uses dbs instead of schema, so a previous failure means we didn't get a proper tearDown of
        # the userdata dbs, cleaning here
        StandardDB.delete_schema(SyncTestRemoteServer.USERNAME)

        self.user = User.objects.create_user(
            username=SyncTestRemoteServer.USERNAME, password=SyncTestRemoteServer.PASSWORD
        )

    def tearDown(self):
        self.user.delete()

    def load_db_to_dict(self):
        db_contents = {}

        with db_conn().cursor() as cur:
            for table_name, _defin in AnkiDataModel.MODEL.items():
                cur.execute(f"select * from {self.user.username}.{table_name}")  # what about ordering?
                db_contents[table_name] = sorted(cur.fetchall())
        return db_contents

    @staticmethod
    def db_diff(left_db, right_db):  # noqa: C901
        """
        Checks for diffs between two dicts corresponding to a "before calling api method" and "after". In reality,
        there are a few fields that get updated every time on the 'col' table, like 'mod' (modified), 'ls' (last sync)
        and 'lastUnburied' (which should have the int corresponding to 'today', and may or may not be present in the
        'before' db)
        """
        output = {}
        COLS = {
            0: "id",
            1: "crt",
            2: "mod",
            3: "scm",
            4: "ver",
            5: "dty",
            6: "usn",
            7: "ls",
            8: "conf",
            9: "models",
            10: "decks",
            11: "dconf",
            12: "tags",
        }
        for table_name, _defin in AnkiDataModel.MODEL.items():  # pylint: disable=R1702
            if left_db[table_name] != right_db[table_name]:
                if table_name == "col":
                    for i in range(0, len(COLS.keys())):
                        # FIXME: is this ok??? mod and ls should be different, others the same
                        if i in (2, 7):  # 2 is the 'mod' column, 7 is the 'ls' column, both are zero-indexed here
                            continue  # FIXME: should we rather make sure they are indeed different?
                        # the scheduler adds an entry to the json, which changes depending on the day it is run
                        # we could calculate it but wtf is this doing in the db for the collection...
                        if i == 8:  # 8 = the zero-indexed 'conf' column
                            oclean = json.loads(left_db[table_name][0][i])
                            nclean = json.loads(right_db[table_name][0][i])
                            nclean.pop("lastUnburied", None)  # lastUnburied field gets added which we don't care about
                            oclean.pop("lastUnburied", None)  # lastUnburied field gets added which we don't care about

                            if oclean != nclean:
                                if table_name not in output:
                                    output[table_name] = {}
                                output[table_name][COLS[i]] = (oclean, nclean)
                        elif left_db[table_name][0][i] != right_db[table_name][0][i]:
                            if table_name not in output:
                                output[table_name] = {}

                            output[table_name][COLS[i]] = (left_db[table_name][0][i], right_db[table_name][0][i])
                else:
                    output[table_name] = (left_db[table_name], right_db[table_name])

        return output

    def load_db_asset(self, schema_name, fname):

        sql = pkgutil.get_data(self.assets_package(), fname).decode("utf-8")

        # load a db that has values in each table
        # FIXME: for some reason if I use the test object's connection instead of creating a new one the tables
        # aren't visible after... Why?
        with db_conn().cursor() as cur:
            # recreate if exists
            cur.execute(AnkiDataModel.DROP_SCHEMA.format(schema_name=schema_name))
            StandardDB.create_schema(schema_name)
            cur.execute(f"TRUNCATE TABLE {schema_name}.col")

            cur.execute(
                sql.replace("{schema_name}", schema_name).replace("{db_owner}", connection.settings_dict["USER"])
            )

    def load_json_asset(self, fname):
        return json.loads(pkgutil.get_data(self.assets_package(), fname).decode("utf-8"))

    def load_bin_asset(self, fname):
        return pickle.loads(pkgutil.get_data(self.assets_package(), fname))

    def copy_asset_to_path(self, fname, dest_fname):
        pathlib.Path(os.path.dirname(dest_fname)).mkdir(parents=True, exist_ok=True)
        with open(dest_fname, "wb") as fh:
            fh.write(pkgutil.get_data(self.assets_package(), fname))

    def get_asset(self, fname):
        return pkgutil.get_data(self.assets_package(), fname)


class SyncTestRemoteServer(TestRemoteServer):
    def _standard_no_diff_test(self, rs_method, test_set, with_start, expect_today_last_unburied=False):
        rs = rs_method.__self__  # get the object of the bound method

        # hostKey will get a session in the remote server which contains auth
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()  # adds values to cache

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")

        if with_start:
            # this puts some values into the cache which we need for subsequent calls
            # we don't actually care what is in the start json
            rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        before = self.load_db_to_dict()
        today = int((time.time() - before["col"][0][1]) // 86400)

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))

        # FIXME: why should we not have this every time?
        if today and expect_today_last_unburied:  # verify there is a lastUnburied and that it has the right value
            self.assertIn("lastUnburied", output["conf"])
            self.assertEqual(output["conf"].pop("lastUnburied"), today)

        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()
        self.assertFalse(self.db_diff(before, after))  # should return an empty dict for this input/output

    def _standard_begin_test(self, test_set, expected_usn):
        rms = TestRemoteMediaServer()
        rms.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rms.meta()

        rs_method = rms.begin

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")

        before = self.load_db_to_dict()

        output = rs_method()["data"]
        self.assertEqual(len(output), 2)
        self.assertEqual(output["usn"], expected_usn)
        self.assertIsNotNone(output.get("sk"))

        # no db change expected
        after = self.load_db_to_dict()
        self.assertFalse(self.db_diff(before, after))

    def _standard_media_sanity_test(self, test_set):
        rms = TestRemoteMediaServer()
        rms.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rms.meta()
        rms.begin()  # this sets the skey

        rs_method = rms.mediaSanity

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")

        before = self.load_db_to_dict()

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))["data"]
        self.assertEqual(output, "OK")

        # no db change expected
        after = self.load_db_to_dict()
        self.assertFalse(self.db_diff(before, after))

    def _standard_chunk_test(self, test_set):
        rs = TestRemoteSyncServer()
        rs_method = rs.chunk

        # hostKey will get a session in the remote server which contains auth
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        # this puts some values into the cache which we need for subsequent calls
        # we don't actually care about what is in the start json!
        rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        before = self.load_db_to_dict()

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))
        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()
        diff = self.db_diff(before, after)

        self.assertFalse(diff)

    def _standard_sanity_check2_test(self, test_set, to_review):
        rs = TestRemoteSyncServer()
        rs_method = rs.sanityCheck2

        # hostKey will get a session in the remote server which contains auth
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        # this puts some values into the cache which we need for subsequent calls
        # we don't actually care about what is in the start json!
        rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        before = self.load_db_to_dict()

        input_json = self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json")
        today = int((time.time() - before["col"][0][1]) // 86400)  # were the test files generated today?
        input_json["client"][0][2] = 0 if not today else to_review

        output = rs_method(**input_json)
        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()
        diff = self.db_diff(before, after)

        self.assertFalse(diff)

    def _standard_finish_test(self, test_set):
        rs = TestRemoteSyncServer()
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()

        rs_method = rs.finish

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        # this puts some values into the cache which we need for subsequent calls
        # we don't actually care about what is in the start json!
        rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        before = self.load_db_to_dict()

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))
        self.assertIsInstance(output, int)
        # FIXME: is the following necessary? it could make for flakey tests!!!
        self.assertGreater(output, int(time.time() * 1000) - 3000)

        after = self.load_db_to_dict()

        diff = self.db_diff(before, after)
        self.assertEqual(len(diff), 1)

        col = diff["col"]
        self.assertEqual(len(col), 1)
        self.assertEqual(col["usn"][0] + 1, col["usn"][1])  # The DB should have the usn increased by 1


class SyncTestRemoteServerCommon(SyncTestRemoteServer):
    def assets_package(self):
        # unused here
        pass

    def test_host_key(self):
        rs = TestRemoteSyncServer()
        self.assertIsNotNone(rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD))
        self.assertIsNone(rs.hostKey(SyncTestRemoteServer.USERNAME + "bad", SyncTestRemoteServer.PASSWORD))
        self.assertIsNone(rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD + "bad"))
        self.assertIsNone(rs.hostKey(SyncTestRemoteServer.USERNAME + "bad", SyncTestRemoteServer.PASSWORD + "bad"))

    def test_meta(self):
        rs = TestRemoteSyncServer()
        rs.hostKey(SyncTestRemoteServer.USERNAME + "bad", SyncTestRemoteServer.PASSWORD)
        self.assertIsNone(rs.meta())

        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        meta = rs.meta()

        self.assertGreater(meta["scm"], 1)
        self.assertGreater(meta["ts"], 1)
        self.assertGreater(meta["mod"], 1)
        self.assertEqual(meta["usn"], 0)
        self.assertEqual(meta["musn"], 0)
        self.assertEqual(meta["msg"], "")
        self.assertTrue(meta["cont"])


class SyncTestFullSyncer(SyncTestRemoteServer):
    # override SyncTestRemoteServer

    @staticmethod
    def assets_package():
        return "assets"

    def test_download(self):  # pylint: disable=R0914
        fss = TestFullSyncer()
        fss.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        fss.meta()

        self.load_db_asset(SyncTestRemoteServer.USERNAME, "one_note_reviewed_one_deleted_sql.sql")

        cont = fss.download()
        self.maxDiff = None
        self.assertIsNotNone(cont)

        with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as f:
            temp_db_path = f.name
            f.write(cont)

        with sqlite.connect(temp_db_path) as sqlite_conn:
            cur = sqlite_conn.cursor()
            cur.execute("pragma integrity_check")
            self.assertEqual(cur.fetchone()[0], "ok")

            for table, props in AnkiDataModel.MODEL.items():
                if props["parent"] != AnkiDataModel.COLLECTION_PARENT_DB:
                    continue

                with db_conn().cursor() as from_pg_cursor:
                    to_sqlite_cursor = sqlite_conn.cursor()  # can't use `with` with an sqlite3 cursor

                    pgcols = ",".join([x["name"] for x in props["fields"]])

                    col_names = []
                    for x in props["fields"]:
                        col_names.append(x["sqlite_name"] if "sqlite_name" in x else x["name"])
                    mycols = ",".join(col_names)

                    sql = f"SELECT {mycols} FROM {table}"
                    psql = f"SELECT {pgcols} FROM {SyncTestRemoteServer.USERNAME}.{table}"
                    from_pg_cursor.execute(psql)
                    to_sqlite_cursor.execute(sql)
                    pg_res = from_pg_cursor.fetchall()
                    sl_res = to_sqlite_cursor.fetchall()
                    to_sqlite_cursor.close()
                    # FIXME: we have to compare strings because sqlite is fucking stupid
                    # and you can store the empty string in a type long.
                    self.assertEqual(
                        [[str(y) for y in x] for x in pg_res], [[str(y) for y in x] for x in sl_res],
                    )

        os.unlink(temp_db_path)

    def test_upload(self):
        fss = TestFullSyncer()
        fss.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        fss.meta()

        sqlite_db = pkgutil.get_data(self.root_assets_package(), "one_note_reviewed_one_deleted_sql.anki2")
        self.assertTrue(fss.upload(sqlite_db))

        ref_db_path = os.path.join(
            os.path.dirname(sys.modules[self.root_assets_package()].__file__), "one_note_reviewed_one_deleted_sql.anki2"
        )

        with sqlite.connect(ref_db_path) as sqlite_conn:
            cur = sqlite_conn.cursor()
            cur.execute("pragma integrity_check")
            self.assertEqual(cur.fetchone()[0], "ok")  # not strictly necessary as it is our ref file

            for table, props in AnkiDataModel.MODEL.items():
                if props["parent"] != AnkiDataModel.COLLECTION_PARENT_DB:
                    continue

                with db_conn().cursor() as from_pg_cursor:
                    to_sqlite_cursor = sqlite_conn.cursor()  # can't use `with` with an sqlite3 cursor

                    stdcols = ",".join([x["name"] for x in props["fields"]])

                    col_names = []
                    for x in props["fields"]:
                        col_names.append(x["sqlite_name"] if "sqlite_name" in x else x["name"])

                    from_pg_cursor.execute(f"SELECT {stdcols} FROM {SyncTestRemoteServer.USERNAME}.{table}")
                    to_sqlite_cursor.execute(f"SELECT {','.join(col_names)} FROM {table}")
                    pg_res = from_pg_cursor.fetchall()
                    sl_res = to_sqlite_cursor.fetchall()
                    to_sqlite_cursor.close()
                    # FIXME: we have to compare strings because sqlite is fucking stupid
                    # and you can store the empty string in a type long.
                    self.assertEqual(
                        [[str(y) for y in x] for x in pg_res], [[str(y) for y in x] for x in sl_res],
                    )


# copied from anki 2.1.11 anki.sync, and modified
class RemoteServer(ABC):
    def __init__(self):
        self.hkey = None
        self.skey = None
        self.postVars = {}

        self.factory = APIRequestFactory()

    # Posting data as a file
    ######################################################################
    # We don't want to post the payload as a form var, as the percent-encoding is
    # costly. We could send it as a raw post, but more HTTP clients seem to
    # support file uploading, so this is the more compatible choice.

    def _buildPostData(self, fobj, comp):
        BOUNDARY = b"Anki-sync-boundary"
        bdry = b"--" + BOUNDARY
        buf = io.BytesIO()
        # post vars
        self.postVars["c"] = 1 if comp else 0
        for (key, value) in list(self.postVars.items()):
            buf.write(bdry + b"\r\n")
            buf.write(('Content-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (key, value)).encode("utf8"))
        # payload as raw data or json
        rawSize = 0
        if fobj:
            # header
            buf.write(bdry + b"\r\n")
            buf.write(
                b"""\
Content-Disposition: form-data; name="data"; filename="data"\r\n\
Content-Type: application/octet-stream\r\n\r\n"""
            )
            # write file into buffer, optionally compressing
            if comp:
                tgt = gzip.GzipFile(mode="wb", fileobj=buf, compresslevel=comp)
            else:
                tgt = buf
            while 1:
                data = fobj.read(65536)
                if not data:
                    if comp:
                        tgt.close()
                    break
                rawSize += len(data)
                tgt.write(data)
            buf.write(b"\r\n")
        buf.write(bdry + b"--\r\n")
        size = buf.tell()
        buf.seek(0)

        if size >= 100 * 1024 * 1024 or rawSize >= 250 * 1024 * 1024:
            raise Exception("Collection too large to upload to AnkiWeb.")

        return buf

    # copied and hacked a lot from django.test.client.RequestFactory django 3.1
    def generic(self, data=""):
        """Construct an arbitrary HTTP request."""

        body = self._buildPostData(data, 6)
        content_type = "multipart/form-data; boundary=Anki-sync-boundary"

        data = force_bytes(body.read(), settings.DEFAULT_CHARSET)
        r = {
            "PATH_INFO": "/",  # this is actually unused because we apply the result to the view manually
            "REQUEST_METHOD": "POST",
            "SERVER_PORT": 80,
            "wsgi.url_scheme": "http",
            "QUERY_STRING": "",
        }
        if data:
            r.update({"CONTENT_LENGTH": str(len(data)), "CONTENT_TYPE": content_type, "wsgi.input": FakePayload(data)})

        request = self.factory.request(**r)
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()

        return request

    def hostKey(self, user, pw):
        self.postVars = dict()

        req = self.generic(io.BytesIO(json.dumps(dict(u=user, p=pw)).encode("utf8")))
        ret = base_hostKey(req)

        if ret.status_code != 200:
            # invalid auth or other issue
            return None

        self.hkey = json.loads(ret.content.decode("utf8"))["key"]
        self.skey = self.hkey  # is this really ok?
        return self.hkey

    def meta(self):
        if not self.hkey:
            return None

        self.postVars = dict(k=self.hkey, s=self.skey)

        req = self.generic(io.BytesIO(json.dumps(dict(v=SYNC_VER, cv=ANKI_VERSION_STRING)).encode("utf8")))
        ret = base_meta(req)

        if ret.status_code != 200:
            # invalid auth or another issue
            return None
        return json.loads(ret.content.decode("utf8"))


class TestRemoteSyncServer(RemoteServer):
    def applyGraves(self, **kw):
        return self._run(kw, base_applyGraves)

    def applyChanges(self, **kw):
        return self._run(kw, base_applyChanges)

    def start(self, **kw):
        return self._run(kw, base_start)

    def chunk(self, **kw):
        return self._run(kw, base_chunk)

    def applyChunk(self, **kw):
        return self._run(kw, base_applyChunk)

    def sanityCheck2(self, **kw):
        return self._run(kw, base_sanityCheck2)

    def finish(self, **kw):
        return self._run(kw, base_finish)

    def abort(self, **kw):
        raise NotImplementedError
        # return self._run("abort", kw)

    def _run(self, data, view_method):

        req = self.generic(io.BytesIO(json.dumps(data).encode("utf8")))
        ret = view_method(req)

        if ret.status_code != 200:
            # invalid auth or another issue
            raise Exception(f"Error calling {view_method} with data {data}")

        return json.loads(ret.content.decode("utf8"))


class TestFullSyncer(RemoteServer):
    def download(self):
        self.postVars = dict(k=self.hkey, s=self.skey)

        req = self.generic(io.BytesIO(json.dumps(dict(v=ANKI_VERSION_STRING)).encode("utf8")))

        ret = base_download(req)

        if ret.status_code != 200:
            # invalid auth or another issue
            return None
        return ret.content

    def upload(self, bin_data):
        self.postVars = dict(k=self.hkey, s=self.skey)

        req = self.generic(io.BytesIO(bin_data))
        ret = base_upload(req)

        if ret.status_code != 200:
            # invalid auth or another issue
            return None
        return ret.content


class TestRemoteMediaServer(RemoteServer):
    @staticmethod
    def _safe_return(query_return):
        if query_return.status_code != 200:
            # invalid auth or another issue
            raise Exception("Invalid auth or other HTTP code error")

        resp = json.loads(query_return.content.decode("utf8"))

        if resp["err"]:
            raise Exception(f"SyncError:{resp['err']}")

        return resp

    def begin(self):
        self.postVars = dict(k=self.hkey, v=ANKI_VERSION_STRING)

        req = self.generic(io.BytesIO(json.dumps(dict()).encode("utf8")))
        resp = self._safe_return(media_begin(req))
        self.skey = resp["data"]["sk"]  # also initialise the skey, which we need for all subsequent calls
        return resp

    # args: lastUsn
    def mediaChanges(self, **kw):
        self.postVars = dict(sk=self.skey)

        req = self.generic(io.BytesIO(json.dumps(kw).encode("utf8")))
        return self._safe_return(media_mediaChanges(req))

    # args: files
    def downloadFiles(self, **kw):
        self.postVars = dict(sk=self.skey)

        req = self.generic(io.BytesIO(json.dumps(kw).encode("utf8")))
        # this is just the zip binary so no json to test for an error, we rely simply on the HTTP code

        resp = media_downloadFiles(req)
        if resp.status_code != 200:
            raise Exception("Error downloading file with status_code {resp.status_code}")

        return resp

    def uploadChanges(self, zip_file):
        # no compression, as we compress the zip file instead
        self.postVars = dict(sk=self.skey)

        req = self.generic(io.BytesIO(zip_file))
        return self._safe_return(media_uploadChanges(req))

    # args: local
    def mediaSanity(self, **kw):
        self.postVars = dict(sk=self.skey)

        req = self.generic(io.BytesIO(json.dumps(kw).encode("utf8")))
        return self._safe_return(media_mediaSanity(req))
