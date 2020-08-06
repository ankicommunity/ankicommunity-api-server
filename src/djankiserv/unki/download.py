# -*- coding: utf-8 -*-
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import json
import os
import pkgutil
from sqlite3 import dbapi2 as sqlite

from djankiserv.assets.sql import sqlite3  # noqa: F401 # pylint: disable=W0611
from djankiserv.unki import AnkiDataModelBase, intTime


class DB:  # this is only for the sqlite db
    def __init__(self, path):
        self._db = sqlite.connect(path, timeout=0)
        self._db.text_factory = self._textFactory
        self._path = path
        self.mod = False

    def execute(self, sql, *a):
        s = sql.strip().lower()
        # mark modified?
        for stmt in "insert", "update", "delete":
            if s.startswith(stmt):
                self.mod = True
                break

        return self._db.execute(sql, a)

    def executescript(self, sql):
        self.mod = True
        self._db.executescript(sql)

    def scalar(self, *a):
        res = self.execute(*a).fetchone()  # pylint: disable=E1120  # FIXME: how should I get rid of this disable?
        if res:
            return res[0]
        return None

    def close(self):
        self._db.text_factory = None
        self._db.close()

    def __enter__(self):
        self._db.execute("begin")
        return self

    def __exit__(self, exc_type, *args):
        self._db.close()

    # strip out invalid utf-8 when reading from db
    @staticmethod
    def _textFactory(data):
        return str(data, errors="ignore")


def sqlite3_for_download(path):
    path = os.path.abspath(path)
    if os.path.exists(path):
        raise Exception("This file must not exist!")

    base = os.path.basename(path)
    for c in ("/", ":", "\\"):
        assert c not in base

    db = DB(path)
    # db.isolation_level = None

    db.execute("pragma page_size = 4096")
    db.execute("pragma legacy_file_format = 0")
    db.execute("vacuum")

    db.executescript(pkgutil.get_data("djankiserv.assets.sql.sqlite3", "create_tables.sql").decode("utf-8"))
    db.executescript(
        pkgutil.get_data("djankiserv.assets.sql.sqlite3", "init_col_table.sql").decode("utf-8")
        % ({"v": AnkiDataModelBase.VERSION, "s": intTime(1000)})
    )

    c = json.loads(pkgutil.get_data("djankiserv.assets.jsonfiles", "default_collection_conf.json").decode("utf-8"))
    g = json.loads(pkgutil.get_data("djankiserv.assets.jsonfiles", "default_deck.json").decode("utf-8"))
    g["mod"] = intTime()
    gc = json.loads(pkgutil.get_data("djankiserv.assets.jsonfiles", "default_deck_conf.json").decode("utf-8"))

    db.execute(
        "update col set conf = ?, decks = ?, dconf = ?", json.dumps(c), json.dumps({"1": g}), json.dumps({"1": gc})
    )

    db.executescript(pkgutil.get_data("djankiserv.assets.sql.sqlite3", "add_indices.sql").decode("utf-8"))

    db.execute("analyze")
    db.execute("pragma temp_store = memory")
    db.execute("pragma cache_size = 10000")
    db.execute("pragma journal_mode = delete")  # this forces flush to disk when closing the file: MUST KEEP
    # db.execute("pragma journal_mode = wal")  # MUSTN'T use this

    # db.isolation_level = ""

    db.close()
