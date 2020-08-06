# -*- coding: utf-8 -*-
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import json
import re
import time

from djankiserv.unki import checksum  # checksum never actually used, so all occurrences dead code
from djankiserv.unki import splitFields

MODEL_CLOZE = 1


class ModelManager:
    def __init__(self, col):
        self.col = col
        self.needs_saving = False  # to make pylint happy
        self.models = None  # to make pylint happy

    def load(self, json_):
        "Load registry from JSON."
        self.needs_saving = False
        self.models = json.loads(json_)

    def flush(self):
        "Flush the registry if any models were changed."
        if self.needs_saving:
            self.col.db.execute(f"update {self.col.username}.col set models = %s", json.dumps(self.models))
            self.needs_saving = False

    def get(self, mid):
        "Get model with ID, or None."
        return self.models.get(str(mid))

    def all(self):
        "Get all models."
        return list(self.models.values())

    def ensure_name_unique(self, model):
        for mcur in self.all():
            if mcur["name"] == model["name"] and mcur["id"] != model["id"]:
                model["name"] += "-" + checksum(str(time.time()))[:5]
                break

    def update(self, model):
        "Add or update an existing model. Used for syncing and merging."
        self.ensure_name_unique(model)
        self.models[str(model["id"])] = model
        # mark registry changed, but don't bump mod time
        self.needs_saving = True

    def ids(self):
        return list(self.models.keys())

    @staticmethod
    def field_names(model):
        return [field["name"] for field in model["flds"]]

    @staticmethod
    def sort_idx(model):
        return model["sortf"]

    def by_name(self, name):
        "Get model with NAME."
        for model in list(self.models.values()):
            if model["name"] == name:
                return model
        return None

    # FIXME: this shouldn't be necessary!!!
    def set_current(self, model):
        self.col.conf["curModel"] = model["id"]
        self.col.db.mod = True

    def avail_ords(self, model, flds):  # noqa: C901
        "Given a joined field string, return available template ordinals."
        if model["type"] == MODEL_CLOZE:
            return self._avail_cloze_ords(model, flds)
        fields = {}
        for c, f in enumerate(splitFields(flds)):
            fields[c] = f.strip()
        avail = []
        for ordi, otype, req in model["req"]:
            # unsatisfiable template
            if otype == "none":
                continue
            # AND requirement?
            if otype == "all":
                ok = True
                for idx in req:
                    if not fields[idx]:
                        # missing and was required
                        ok = False
                        break
                if not ok:
                    continue
            # OR requirement?
            elif otype == "any":
                ok = False
                for idx in req:
                    if fields[idx]:
                        ok = True
                        break
                if not ok:
                    continue
            avail.append(ordi)
        return avail

    def _avail_cloze_ords(self, model, flds, allow_empty=True):
        sflds = splitFields(flds)
        amap = self.field_map(model)
        ords = set()
        matches = re.findall("{{[^}]*?cloze:(?:[^}]?:)*(.+?)}}", model["tmpls"][0]["qfmt"])
        matches += re.findall("<%cloze:(.+?)%>", model["tmpls"][0]["qfmt"])
        for fname in matches:
            if fname not in amap:
                continue
            ordi = amap[fname][0]
            ords.update([int(stg) - 1 for stg in re.findall(r"(?s){{c(\d+)::.+?}}", sflds[ordi])])
        if -1 in ords:
            ords.remove(-1)
        if not ords and allow_empty:
            # empty clozes use first ord
            return [0]
        return list(ords)

    @staticmethod
    def field_map(model):
        "Mapping of field name -> (ord, field)."
        return dict((field["name"], (field["ord"], field)) for field in model["flds"])
