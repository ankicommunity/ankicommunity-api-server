# -*- coding: utf-8 -*-

import logging
import os
import tempfile
import time
from sqlite3 import dbapi2 as sqlite

import djankiserv.unki
from djankiserv.assets import jsonfiles  # noqa: 401
from djankiserv.unki import REM_CARD, REM_NOTE, ids2str, intTime
from djankiserv.unki.database import StandardDB, db_conn
from djankiserv.unki.download import DB, sqlite3_for_download

logger = logging.getLogger("djankiserv.sync")


class SyncCollectionHandler:  # pylint: disable=R0904
    operations = ["meta", "applyChanges", "start", "applyGraves", "chunk", "applyChunk", "sanityCheck2", "finish"]

    def __init__(self, col, session=None):
        self.col = col
        if session:
            ## make sure not to create the property if it isn't in the dict
            ## this way we know the actual flow of events as it will raise an
            ## error. I know, this is nastiness...
            if "min_usn" in session:
                self.min_usn = session["min_usn"]
            if "max_usn" in session:
                self.max_usn = session["max_usn"]
            if "lnewer" in session:
                self.lnewer = session["lnewer"]

    ##
    ## Public API methods
    ##
    # ankidesktop >=2.1rc2 sends graves in applyGraves, but still expects
    # server-side deletions to be returned by start
    def start(self, min_usn, lnewer, offset):
        # FIXME: the clients now send an offset for the V1 scheduler, so we need to find out how
        # to distinguish between the V1 and V2 schedulers and only allow V1 for the moment
        if False and offset is not None:
            raise NotImplementedError(
                "You are using the experimental V2 scheduler, which is not supported by the server."
            )
        self.max_usn = self.col.usn
        self.min_usn = min_usn
        self.lnewer = not lnewer
        lgraves = self.removed()
        return lgraves

    def applyGraves(self, chunk):
        self.remove(chunk)

    def applyChanges(self, changes):
        lchg = self.changes()  # also has update side-effects, so must do before merge_changes
        # merge our side before returning
        self.merge_changes(changes)
        return lchg

    def applyChunk(self, chunk):
        if "revlog" in chunk:
            self.merge_revlog(chunk["revlog"])
        if "cards" in chunk:
            self.merge_cards(chunk["cards"])
        if "notes" in chunk:
            self.merge_notes(chunk["notes"])

    def all_data_to_sync_down(self):
        buf = dict(done=True)
        for table in ["revlog", "cards", "notes"]:
            cursor = self.cursor_for_table(table)
            rows = cursor.fetchall()
            # mark the objects as having been sent
            self.col.db.execute(f"update {self.col.username}.{table} set usn=%s where usn=-1", self.max_usn)
            buf[table] = rows
        return buf

    def sanityCheck2(self, client):
        server = self.sanity_check()
        if client != server:
            return dict(status="bad", c=client, s=server)
        return dict(status="ok")

    def finish(self):
        mod = intTime(1000)
        self.col.ls = mod
        self.col.usn = self.max_usn + 1
        # ensure we save the mod time even if no changes made
        self.col.db.mod = True
        self.col.save(mod=mod)
        return mod

    ##
    ## Project-internal methods
    ##
    def changes(self):
        "Bundle up small objects."
        d = dict(models=self.get_models(), decks=self.get_decks(), tags=self.get_tags())
        if self.lnewer:
            d["conf"] = self.get_conf()
            d["crt"] = self.col.crt
        return d

    def merge_changes(self, rchg):
        # then the other objects
        self.merge_models(rchg["models"])
        self.merge_decks(rchg["decks"])
        self.merge_tags(rchg["tags"])
        if "conf" in rchg:
            self.merge_conf(rchg["conf"])
        # this was left out of earlier betas
        if "crt" in rchg:
            self.col.crt = rchg["crt"]

    def sanity_check(self):  # noqa: C901
        if not self.col.basic_check():
            return "failed basic check"
        for t in "cards", "notes", "revlog", "graves":
            if self.col.db.scalar(f"select count(0) from {self.col.username}.{t} where usn = -1"):
                return "%s had usn = -1" % t
        for g in self.col.decks.all():
            if g["usn"] == -1:
                return "deck had usn = -1"
        for t, usn in self.col.all_tags():
            if usn == -1:
                return "tag had usn = -1"
        found = False
        for m in self.col.models.all():
            if m["usn"] == -1:
                return "model had usn = -1"
        if found:
            self.col.models.needs_saving = True

        self.col.sched.reset()
        # check for missing parent decks
        self.col.sched.deckDueList()
        # return summary of deck
        return [
            list(self.col.sched.counts()),
            self.col.db.scalar(f"select count(0) from {self.col.username}.cards"),
            self.col.db.scalar(f"select count(0) from {self.col.username}.notes"),
            self.col.db.scalar(f"select count(0) from {self.col.username}.revlog"),
            self.col.db.scalar(f"select count(0) from {self.col.username}.graves"),
            len(self.col.models.all()),
            len(self.col.decks.all()),
            len(self.col.decks.all_conf()),
        ]

    def cursor_for_table(self, table):
        if table == "revlog":
            return self.col.db.execute(
                f"""
                select id, cid, {self.max_usn}, ease, ivl, lastIvl, factor, rtime, type
                from {self.col.username}.revlog where usn >= {self.min_usn}"""
            )
        if table == "cards":
            return self.col.db.execute(
                f"""
                select id, nid, did, ord, modified, {self.max_usn}, type, queue, due, ivl, factor, reps,
                lapses, remaining, odue, odid, flags, data from {self.col.username}.cards where usn >= {self.min_usn}"""
            )
        return self.col.db.execute(
            f"""
            select id, guid, mid, modified, {self.max_usn}, tags, flds, '', '', flags, data
            from {self.col.username}.notes where usn >= {self.min_usn}"""
        )

    def remove(self, graves):
        # notes first, so we don't end up with duplicate graves
        self.col.rem_notes(graves["notes"])
        # then cards
        self.col.rem_cards(graves["cards"], notes=False)
        # and decks
        for oid in graves["decks"]:
            self.col.decks.rem(oid, children_too=False)

    def merge_models(self, rchg):
        for r in rchg:
            left = self.col.models.get(r["id"])
            # if missing locally or server is newer, update
            if not left or r["mod"] > left["mod"]:
                self.col.models.update(r)

    def merge_decks(self, rchg):
        for r in rchg[0]:
            left = self.col.decks.get(r["id"], False)
            # work around mod time being stored as string
            if left and not isinstance(left["mod"], int):
                left["mod"] = int(left["mod"])

            # if missing locally or server is newer, update
            if not left or r["mod"] > left["mod"]:
                self.col.decks.update(r)
        for r in rchg[1]:
            try:
                left = self.col.decks.get_conf(r["id"])
            except KeyError:
                left = None
            # if missing locally or server is newer, update
            if not left or r["mod"] > left["mod"]:
                self.col.decks.update_conf(r)

    def merge_tags(self, tags):
        self.col.register_tags(tags, usn=self.max_usn)

    def merge_revlog(self, logs):
        # import AnkiDataModel  # noqa # pylint: disable=C0415,W0611
        sql = djankiserv.unki.AnkiDataModel.insert_on_conflict_nothing(self.col.username, "revlog")

        self.col.db.executemany(sql, logs)

    def newer_rows(self, data, table, modIdx):
        ids = (r[0] for r in data)
        lmods = {}
        ids_str = ids2str(ids)
        for tid, mod in self.col.db.execute(
            f"select id, modified from {self.col.username}.{table} where id in {ids_str} and usn >= {self.min_usn}"
        ):
            lmods[tid] = mod
        update = []
        for r in data:
            if r[0] not in lmods or lmods[r[0]] < r[modIdx]:
                update.append(r)
        return update

    def merge_cards(self, cards):
        sql = djankiserv.unki.AnkiDataModel.insert_on_conflict_update(self.col.username, "cards")
        rows = self.newer_rows(cards, "cards", 4)
        self.col.db.executemany(sql, rows)

    def merge_notes(self, notes):
        rows = self.newer_rows(notes, "notes", 3)
        sql = djankiserv.unki.AnkiDataModel.insert_on_conflict_update(self.col.username, "notes")
        self.col.db.executemany(sql, rows)
        self.col.update_field_cache([f[0] for f in rows])

    def get_conf(self):
        return self.col.conf

    def merge_conf(self, conf):
        if conf != self.col.conf:
            self.col.conf = conf
            self.col.db.mod = True

    # @staticmethod
    # def _old_client(cv):
    #     if not cv:
    #         return False

    #     note = {"alpha": 0, "beta": 0, "rc": 0}
    #     client, version, platform = cv.split(',')

    #     for name in note.keys():
    #         if name in version:
    #             vs = version.split(name)
    #             version = vs[0]
    #             note[name] = int(vs[-1])

    #     # convert the version string, ignoring non-numeric suffixes like in beta versions of Anki
    #     version_nosuffix = re.sub(r'[^0-9.].*$', '', version)
    #     version_int = [int(x) for x in version_nosuffix.split('.')]

    #     if client == 'ankidesktop':
    #         return version_int < [2, 0, 27]
    #     elif client == 'ankidroid':
    #         if version_int == [2, 3]:
    #            if note["alpha"]:
    #               return note["alpha"] < 4
    #         else:
    #            return version_int < [2, 2, 3]
    #     else:  # unknown client, assume current version
    #         return False

    def removed(self):
        cards = []
        notes = []
        decks = []

        curs = self.col.db.execute(f"select oid, type from {self.col.username}.graves where usn >= %s", self.min_usn)

        for oid, t in curs:
            if t == REM_CARD:
                cards.append(oid)
            elif t == REM_NOTE:
                notes.append(oid)
            else:
                decks.append(oid)

        return dict(cards=cards, notes=notes, decks=decks)

    def get_models(self):
        return [m for m in self.col.models.all() if m["usn"] >= self.min_usn]

    def get_decks(self):
        return [
            [g for g in self.col.decks.all() if g["usn"] >= self.min_usn],
            [g for g in self.col.decks.all_conf() if g["usn"] >= self.min_usn],
        ]

    def get_tags(self):
        return [t for t, usn in self.col.all_tags() if usn >= self.min_usn]


def full_upload(data, username):
    # from sqlite to a standard db
    # TODO, maybe make this from config or an envvar
    insert_cursor_size = 10000  # this has no effect on memory and less than 1k significantly increases the time

    if not len(data) > 0:
        raise Exception("There is no data in the uploaded file")

    # write data to a tempfile
    with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as f:
        temp_db_path = f.name
        f.write(data)

    # Verify integrity of the received database file before replacing our existing db.
    _check_sqlite3_db(temp_db_path)

    # create new schema in pg db that we'll fill with the new data
    timestamp = str(time.time()).replace(".", "_")
    tmp_schema_name = f"{username}_{timestamp}"
    StandardDB.create_schema(tmp_schema_name)

    # should maybe create a global transaction here?
    # same issue as https://github.com/tsudoko/anki-sync-server/issues/6
    with sqlite.connect(temp_db_path) as sqlite_conn, db_conn().cursor() as to_std_cursor:
        # clean the default values from the collection table
        to_std_cursor.execute(f"TRUNCATE TABLE {tmp_schema_name}.col")

        for table, props in djankiserv.unki.AnkiDataModel.MODEL.items():
            if props["parent"] != djankiserv.unki.AnkiDataModel.COLLECTION_PARENT_DB:
                continue

            start_sqlite_cursor = sqlite_conn.cursor()
            start_sqlite_cursor.execute(f"SELECT * FROM {table}")
            while True:
                current_data = start_sqlite_cursor.fetchmany(insert_cursor_size)
                if not current_data:
                    break
                # FIXME: psycopg2.extras is MUCH better than executemany, but is pgsql-specific
                # psycopg2.extras.execute_values(
                #     to_std_cursor, f"INSERT INTO {tmp_schema_name}.{table} VALUES %s", current_data)

                cols = ",".join(["%s"] * len(current_data[0]))
                to_std_cursor.executemany(f"INSERT INTO {tmp_schema_name}.{table} VALUES ({cols})", current_data)
            start_sqlite_cursor.close()
        djankiserv.unki.AnkiDataModel.replace_schema(to_std_cursor, username, tmp_schema_name)
        os.remove(temp_db_path)

    return "OK"


def full_download(col, username):
    select_cursor_size = 10000  # this has no effect on memory and less than 1k significantly increases the time

    download_db = _create_empty_sqlite3_db()

    # should maybe create a global transaction here?
    # same issue as https://github.com/tsudoko/anki-sync-server/issues/6
    col.save()

    with sqlite.connect(download_db) as sqlite_conn:
        sqlite_conn.isolation_level = "EXCLUSIVE"
        for table, props in djankiserv.unki.AnkiDataModel.MODEL.items():
            if props["parent"] != djankiserv.unki.AnkiDataModel.COLLECTION_PARENT_DB:
                continue

            with db_conn().cursor() as from_std_cursor:
                to_sqlite_cursor = sqlite_conn.cursor()  # can't use `with` with an sqlite3 cursor

                pgcols = ",".join([x["name"] for x in props["fields"]])

                from_std_cursor.execute(f"SELECT {pgcols} FROM {username}.{table}")
                while True:
                    current_data = from_std_cursor.fetchmany(select_cursor_size)

                    if not current_data:
                        break
                    cols = ",".join(["?"] * len(current_data[0]))
                    # TODO: executemany has terrible performance but whatever
                    to_sqlite_cursor.executemany(f"INSERT INTO {table} VALUES ({cols})", current_data)

                to_sqlite_cursor.close()

    _check_sqlite3_db(download_db)

    data = open(download_db, "rb").read()
    os.remove(download_db)

    return data


# using anki's own methods for empty db creation
def _create_empty_sqlite3_db():
    # we need to get a tmp filename where the file doesn't exist, or we can't use anki.storage.Collection
    # to create it
    tmp = tempfile.mktemp(suffix=".anki2")

    sqlite3_for_download(tmp)  # .close()  # will create and close cleanly

    # clean up the rows added in up-upstream db initialisation and leave only the schema
    #
    # conn.isolation_level = None and cur.execute("pragma journal_mode = delete")
    # are both required or the sqlite3 file will stay in WAL mode and not flush the transactions to disk
    with sqlite.connect(tmp) as conn:
        cur = conn.cursor()  # can't use `with` with an sqlite3 cursor
        cur.execute("DELETE FROM col")
        cur.close()

    return tmp


def _check_sqlite3_db(db_path):
    try:
        with DB(db_path) as test_db:
            if test_db.scalar("pragma integrity_check") != "ok":
                raise Exception("Integrity check failed for uploaded collection database file.")
    except sqlite.Error as err:
        raise Exception("Uploaded collection database file is corrupt.") from err
