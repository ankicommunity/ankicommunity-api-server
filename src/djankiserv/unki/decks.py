# -*- coding: utf-8 -*-
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import copy
import json
import operator
import pkgutil
import unicodedata

from djankiserv.unki import ids2str, intTime  # intTime is never actually used, so all occurrences are dead code

REM_DECK = 2


class DeckManager:  # pylint: disable=R0904
    def __init__(self, col):
        self.col = col
        self.decks = None  # to make pylint happy
        self.dconf = None  # to make pylint happy
        self.changed = False  # to make pylint happy

    def load(self, decks, dconf):
        self.decks = json.loads(decks)
        self.dconf = json.loads(dconf)
        # set limits to within bounds
        found = False
        for c in list(self.dconf.values()):
            for t in ("rev", "new"):
                pd = "perDay"
                if c[t][pd] > 999999:
                    c[t][pd] = 999999
                    self.save(c)
                    found = True
        if not found:
            self.changed = False

    def save(self, g=None):
        "Can be called with either a deck or a deck configuration."
        if g:
            g["mod"] = intTime()
            g["usn"] = self.col.usn
        self.changed = True

    def flush(self):
        if self.changed:
            self.col.db.execute(
                f"update {self.col.username}.col set decks=%s, dconf=%s", json.dumps(self.decks), json.dumps(self.dconf)
            )
            self.changed = False

    def all(self):
        "A list of all decks."
        return list(self.decks.values())

    def get(self, did, default=True):
        sid = str(did)
        if sid in self.decks:
            return self.decks[sid]
        if default:
            return self.decks["1"]
        return None

    def update(self, g):
        "Add or update an existing deck. Used for syncing and merging."
        self.decks[str(g["id"])] = g
        self.maybe_add_to_active()
        # mark registry changed, but don't bump mod time
        self.save()

    def update_conf(self, g):
        self.dconf[str(g["id"])] = g
        self.save()

    def all_conf(self):
        "A list of all deck config."
        return list(self.dconf.values())

    def conf_for_did(self, did):
        deck = self.get(did, default=False)
        assert deck
        if "conf" in deck:
            conf = self.get_conf(deck["conf"])
            conf["dyn"] = False
            return conf
        # dynamic decks have embedded conf
        return deck

    def get_conf(self, confId):
        return self.dconf[str(confId)]

    def maybe_add_to_active(self):
        # reselect current deck, or default if current has disappeared
        c = self.current()
        self.select(c["id"])

    def _recover_orphans(self):
        dids = list(self.decks.keys())
        mod = self.col.db.mod
        self.col.db.execute(f"update {self.col.username}.cards set did = 1 where did not in " + ids2str(dids))
        self.col.db.mod = mod

    def _check_deck_tree(self):
        decks = self.col.decks.all()
        decks.sort(key=operator.itemgetter("name"))
        names = set()

        for deck in decks:
            # two decks with the same name?
            if deck["name"] in names:
                print("fix duplicate deck name", deck["name"].encode("utf8"))
                deck["name"] += "%d" % intTime(1000)
                self.save(deck)

            # ensure no sections are blank
            if not all(deck["name"].split("::")):
                print("fix deck with missing sections", deck["name"].encode("utf8"))
                deck["name"] = "recovered%d" % intTime(1000)
                self.save(deck)

            # immediate parent must exist
            if "::" in deck["name"]:
                immediateParent = "::".join(deck["name"].split("::")[:-1])
                if immediateParent not in names:
                    print("fix deck with missing parent", deck["name"].encode("utf8"))
                    self._ensure_parents(deck["name"])
                    names.add(immediateParent)

            names.add(deck["name"])

    def check_integrity(self):
        self._recover_orphans()
        self._check_deck_tree()

    # FIXME: this should be removed - it should have no relevance server-side!!!
    def active(self):
        "The currrently active dids. Make sure to copy before modifying."
        return self.col.conf["activeDecks"]

    # FIXME: this should be removed - it should have no relevance server-side!!!
    def selected(self):
        "The currently selected did."
        return self.col.conf["curDeck"]

    # FIXME: this should be removed - it should have no relevance server-side!!!
    def current(self):
        return self.get(self.selected())

    # FIXME: this should be removed - it should have no relevance server-side!!!
    # or should it???
    def select(self, did):
        "Select a new branch."
        # make sure arg is an int
        did = int(did)
        # current deck
        self.col.conf["curDeck"] = did
        # and active decks (current + all children)
        actv = self.children(did)
        actv.sort()
        self.col.conf["activeDecks"] = [did] + [a[1] for a in actv]
        self.changed = True

    def children(self, did):
        "All children of did, as (name, id)."
        name = self.get(did)["name"]
        actv = []
        for g in self.all():
            if g["name"].startswith(name + "::"):
                actv.append((g["name"], g["id"]))
        return actv

    def parents(self, did, deck_name_map=None):
        "All parents of did."
        # get parent and grandparent names
        parents = []
        for part in self.get(did)["name"].split("::")[:-1]:
            if not parents:
                parents.append(part)
            else:
                parents.append(parents[-1] + "::" + part)
        # convert to objects
        for c, p in enumerate(parents):
            if deck_name_map:
                deck = deck_name_map[p]
            else:
                deck = self.get(self.id(p))
            parents[c] = deck
        return parents

    def name_map(self):
        return dict((d["name"], d) for d in self.decks.values())

    def rem(self, did, cards_too=False, children_too=True):  # noqa: C901 # pylint: disable=R0912
        "Remove the deck. If cardsToo, delete any cards inside."
        if str(did) == "1":
            # we won't allow the default deck to be deleted, but if it's a
            # child of an existing deck then it needs to be renamed
            deck = self.get(did)
            if "::" in deck["name"]:
                base = deck["name"].split("::")[-1]
                suffix = ""
                while True:
                    # find an unused name
                    name = base + suffix
                    if not self.by_name(name):
                        deck["name"] = name
                        self.save(deck)
                        break
                    suffix += "1"
            return
        # log the removal regardless of whether we have the deck or not
        self.col.add_graves([did], REM_DECK)
        # do nothing else if doesn't exist
        if not str(did) in self.decks:
            return
        deck = self.get(did)
        if deck["dyn"]:
            # deleting a cramming deck returns cards to their previous deck
            # rather than deleting the cards
            self.col.sched.emptyDyn(did)
            if children_too:
                for name, ch_id in self.children(did):
                    self.rem(ch_id, cards_too)
        else:
            # delete children first
            if children_too:
                # we don't want to delete children when syncing
                for name, ch_id in self.children(did):
                    self.rem(ch_id, cards_too)
            # delete cards too?
            if cards_too:
                # don't use cids(), as we want cards in cram decks too
                cids = self.col.db.list(f"select id from {self.col.username}.cards where did=%s or odid=%s", did, did)
                self.col.rem_cards(cids)
        # delete the deck and add a grave
        del self.decks[str(did)]
        # ensure we have an active deck
        if did in self.active():
            self.select(int(list(self.decks.keys())[0]))
        self.save()

    def by_name(self, name):
        "Get deck with NAME."
        for m in list(self.decks.values()):
            if m["name"] == name:
                return m
        return None

    def get_or_add(self, name, create=True, dtype=None):
        "Add a deck with NAME. Reuse deck if already exists. Return id as int."
        if dtype is None:
            dtype = json.loads(pkgutil.get_data("djankiserv.assets.jsonfiles", "default_deck.json").decode("utf-8"))

        name = name.replace('"', "")
        name = unicodedata.normalize("NFC", name)
        for did, g in list(self.decks.items()):
            if unicodedata.normalize("NFC", g["name"].lower()) == name.lower():
                return int(did)
        if not create:
            return None
        g = copy.deepcopy(dtype)
        if "::" in name:
            # not top level; ensure all parents exist
            name = self._ensure_parents(name)
        g["name"] = name
        while 1:
            did = intTime(1000)
            if str(did) not in self.decks:
                break
        g["id"] = did
        self.decks[str(did)] = g
        self.save(g)
        self.maybe_add_to_active()
        return int(did)

    @staticmethod
    def _path(name):
        return name.split("::")

    def _ensure_parents(self, name):
        "Ensure parents exist, and return name with case matching parents."
        s = ""
        path = self._path(name)
        if len(path) < 2:
            return name
        for p in path[:-1]:
            if not s:
                s += p
            else:
                s += "::" + p
            # fetch or create
            did = self.get_or_add(s)
            # get original case
            s = self.name(did)
        name = s + "::" + path[-1]
        return name

    def name(self, did, default=False):
        deck = self.get(did, default=default)
        if deck:
            return deck["name"]
        return "[no deck]"
