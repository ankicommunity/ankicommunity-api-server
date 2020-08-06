# -*- coding: utf-8 -*-
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import json
import random
import string

import djankiserv.unki

from . import fieldChecksum, intTime, joinFields, splitFields, stripHTMLMedia


def guid64():
    extra = "!#$%&()*+,-./:;<=>?@[]^_`{|}~"
    num = random.randint(0, 2 ** 64 - 1)
    s = string
    table = s.ascii_letters + s.digits + extra
    buf = ""
    while num:
        num, i = divmod(num, len(table))
        buf = table[i] + buf
    return buf


def split_tags(tags):
    "Parse a string and return a list of tags."
    return [t for t in tags.replace("\u3000", " ").split(" ") if t]


class Note:  # pylint: disable=R0902
    def __init__(self, col, model=None, note_id=None):
        assert not (model and note_id)
        self.col = col
        self.mod = None
        self.usn = None
        self.newlyAdded = None

        if note_id:
            self.id = note_id
            self.load()
        else:
            self.id = col.timestamp_for_table("notes")
            self.guid = guid64()
            self._model = model
            self.mid = model["id"]
            self.tags = []
            self.fields = [""] * len(self._model["flds"])
            self.flags = 0
            self.data = ""
            self._fmap = self.col.models.field_map(self._model)
            self.scm = self.col.scm

    def load(self):
        (self.guid, self.mid, self.mod, self.usn, self.tags, self.fields, self.flags, self.data) = self.col.db.first(
            f"""select guid, mid, modified, usn, tags, flds, flags, data
                from {self.col.username}.notes where id = %s""",
            self.id,
        )
        self.fields = splitFields(self.fields)
        self.tags = split_tags(self.tags)
        self._model = self.col.models.get(self.mid)
        self._fmap = self.col.models.field_map(self._model)
        self.scm = self.col.scm

    def as_dict(self):
        return {"id": self.id, "model": self._model["name"], "fields": self.fields, "tags": self.tags}

    def __str__(self):
        return json.dumps(self.as_dict())

    def flush(self, mod=None):
        "If fields or tags have changed, write changes to disk."
        assert self.scm == self.col.scm
        self.newlyAdded = not self.col.db.scalar(f"select 1 from {self.col.username}.cards where nid = %s", self.id)

        sfld = stripHTMLMedia(self.fields[self._model["sortf"]])
        tags = self.col.tagstring_for_note(self.tags)

        fields = joinFields(self.fields)
        if not mod and self.col.db.scalar(
            f"select 1 from {self.col.username}.notes where id = %s and tags = %s and flds = %s", self.id, tags, fields
        ):
            # there has been no change, so nothing to do
            return

        csum = fieldChecksum(self.fields[0])
        self.mod = mod if mod else intTime()
        self.usn = self.col.usn
        sql = djankiserv.unki.AnkiDataModel.insert_on_conflict_update(self.col.username, "notes")
        self.col.db.execute(
            sql,
            self.id,
            self.guid,
            self.mid,
            self.mod,
            self.usn,
            tags,
            fields,
            sfld,
            csum,
            self.flags,
            self.data,
        )

        self.col.register_tags(self.tags)
        if not self.newlyAdded:
            # FIXME: this is possibly deach code - so far this hasn't been executed so it is unclear how it can work...
            self.col.genCards([self.id])
            # FIXME: see orig _postFlush method - should we do this here???
            # self.col.remEmptyCards(ids)

    def model(self):
        return self._model

    def items(self):
        return [(field["name"], self.fields[ordi]) for ordi, field in sorted(self._fmap.values())]

    def __getitem__(self, key):
        return self.fields[self._fmap[key][0]]

    def __setitem__(self, key, value):
        self.fields[self._fmap[key][0]] = value
