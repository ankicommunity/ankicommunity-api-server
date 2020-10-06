# -*- coding: utf-8 -*-
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

# flake8: noqa  # this will eventually be rewritten but for the moment just keep upstream
# pylint: disable=W,R

import time
from heapq import *
from operator import itemgetter

from djankiserv.unki import ids2str, intTime

# queue types: 0=new/cram, 1=lrn, 2=rev, 3=day lrn, -1=suspended, -2=buried
# revlog types: 0=lrn, 1=rev, 2=relrn, 3=cram
# positive revlog intervals are in days (rev), negative in seconds (lrn)

# copied from anki.consts
NEW_CARDS_DISTRIBUTE = 0


class Scheduler:
    name = "std"
    haveCustomStudy = True
    _spreadRev = True
    _burySiblingsOnAnswer = True

    def __init__(self, col):
        self.col = col
        self.queueLimit = 50
        self.reportLimit = 1000
        self.reps = 0
        self.today = None
        self._haveQueues = False
        self._updateCutoff()

    def reset(self):
        self._updateCutoff()
        self._resetLrn()
        self._resetRev()
        self._resetNew()
        self._haveQueues = True

    def counts(self, card=None):
        counts = [self.newCount, self.lrnCount, self.revCount]
        if card:
            idx = self.countIdx(card)
            if idx == 1:
                counts[1] += card.left // 1000
            else:
                counts[idx] += 1
        return tuple(counts)

    def unburyCards(self):
        "Unbury cards."
        self.col.conf["lastUnburied"] = self.today
        self.col.db.execute(f"update {self.col.username}.cards set queue=type where queue = -2")

    def _walkingCount(self, limFn=None, cntFn=None):
        tot = 0
        pcounts = {}
        # for each of the active decks
        name_map = self.col.decks.name_map()
        for did in self.col.decks.active():
            # early alphas were setting the active ids as a str
            did = int(did)
            # get the individual deck's limit
            lim = limFn(self.col.decks.get(did))
            if not lim:
                continue
            # check the parents
            parents = self.col.decks.parents(did, name_map)
            for p in parents:
                # add if missing
                if p["id"] not in pcounts:
                    pcounts[p["id"]] = limFn(p)
                # take minimum of child and parent
                lim = min(pcounts[p["id"]], lim)
            # see how many cards we actually have
            cnt = cntFn(did, lim)
            # if non-zero, decrement from parent counts
            for p in parents:
                pcounts[p["id"]] -= cnt
            # we may also be a parent
            pcounts[did] = lim - cnt
            # and add to running total
            tot += cnt
        return tot

    def deckDueList(self):
        "Returns [deckname, did, rev, lrn, new]"
        self._checkDay()
        self.col.decks.check_integrity()
        decks = self.col.decks.all()
        decks.sort(key=itemgetter("name"))
        lims = {}
        data = []

        def parent(name):
            parts = name.split("::")
            if len(parts) < 2:
                return None
            parts = parts[:-1]
            return "::".join(parts)

        for deck in decks:
            p = parent(deck["name"])
            # new
            nlim = self._deckNewLimitSingle(deck)
            if p:
                nlim = min(nlim, lims[p][0])
            new = self._newForDeck(deck["id"], nlim)
            # learning
            lrn = self._lrnForDeck(deck["id"])
            # reviews
            rlim = self._deckRevLimitSingle(deck)
            if p:
                rlim = min(rlim, lims[p][1])
            rev = self._revForDeck(deck["id"], rlim)
            # save to list
            data.append([deck["name"], deck["id"], rev, lrn, new])
            # add deck as a parent
            lims[deck["name"]] = [nlim, rlim]
        return data

    def _resetNewCount(self):
        cntFn = lambda did, lim: self.col.db.scalar(
            f"select least(count(0), %s) from {self.col.username}.cards where did = %s and queue = 0", lim, did,
        )
        self.newCount = self._walkingCount(self._deckNewLimitSingle, cntFn)

    def _resetNew(self):
        self._resetNewCount()
        self._newDids = self.col.decks.active()[:]
        self._newQueue = []
        self._updateNewCardRatio()

    def _updateNewCardRatio(self):
        if self.col.conf["newSpread"] == NEW_CARDS_DISTRIBUTE:
            if self.newCount:
                self.newCardModulus = (self.newCount + self.revCount) // self.newCount
                # if there are cards to review, ensure modulo >= 2
                if self.revCount:
                    self.newCardModulus = max(2, self.newCardModulus)
                return
        self.newCardModulus = 0

    def _newForDeck(self, did, lim):
        "New count for a single deck."
        if not lim:
            return 0
        lim = min(lim, self.reportLimit)
        return self.col.db.scalar(
            f"""select count(0) from {self.col.username}.cards where did = %s and queue = 0 limit %s""", did, lim
        )

    def _deckNewLimitSingle(self, g):
        "Limit for deck without parent limits."
        if g["dyn"]:
            return self.reportLimit
        c = self.col.decks.conf_for_did(g["id"])
        return max(0, c["new"]["perDay"] - g["newToday"][1])

    def _resetLrnCount(self):
        # sub-day
        self.lrnCount = int(
            self.col.db.scalar(
                f"""
                select sum(remaining/1000) from (select remaining from {self.col.username}.cards where
                did in {self._deckLimit()} and queue = 1 and due < %s limit {self.reportLimit}) as foo""",
                self.dayCutoff,
            )
            or 0
        )
        # day
        self.lrnCount += self.col.db.scalar(
            f"""
            select count(0) from {self.col.username}.cards where did in {self._deckLimit()} and queue = 3
            and due <= %s limit {self.reportLimit}""",
            self.today,
        )

    def _resetLrn(self):
        self._resetLrnCount()
        self._lrnQueue = []
        self._lrnDayQueue = []
        self._lrnDids = self.col.decks.active()[:]

    def _lrnForDeck(self, did):
        cnt = int(
            self.col.db.scalar(
                f"""select sum(remaining/1000) from
                        (select remaining from {self.col.username}.cards
                            where did = %s and queue = 1 and due < %s limit %s) as foo""",
                did,
                intTime() + self.col.conf["collapseTime"],
                self.reportLimit,
            )
            or 0
        )
        return cnt + self.col.db.scalar(
            f"""select count(0) from
                {self.col.username}.cards where did = %s and queue = 3
                and due <= %s limit %s""",
            did,
            self.today,
            self.reportLimit,
        )

    def _deckRevLimitSingle(self, d):
        if d["dyn"]:
            return self.reportLimit
        c = self.col.decks.conf_for_did(d["id"])
        return max(0, c["rev"]["perDay"] - d["revToday"][1])

    def _revForDeck(self, did, lim):
        lim = min(lim, self.reportLimit)
        return self.col.db.scalar(
            f""" select count(0) from {self.col.username}.cards where did = %s and queue = 2
                and due <= %s limit %s""",
            did,
            self.today,
            lim,
        )

    def _resetRevCount(self):
        def cntFn(did, lim):
            return self.col.db.scalar(
                f"""
                select count(0) from {self.col.username}.cards where
                did = %s and queue = 2 and due <= %s limit {lim}""",
                did,
                self.today,
            )

        self.revCount = self._walkingCount(self._deckRevLimitSingle, cntFn)

    def _resetRev(self):
        self._resetRevCount()
        self._revQueue = []
        self._revDids = self.col.decks.active()[:]

    def _deckLimit(self):
        return ids2str(self.col.decks.active())

    def _updateCutoff(self):
        oldToday = self.today
        # days since col created
        self.today = int((time.time() - self.col.crt) // 86400)
        # end of day cutoff
        self.dayCutoff = self.col.crt + (self.today + 1) * 86400
        # update all daily counts, but don't save decks to prevent needless
        # conflicts. we'll save on card answer instead
        def update(g):
            for t in "new", "rev", "lrn", "time":
                key = t + "Today"
                if g[key][0] != self.today:
                    g[key] = [self.today, 0]

        for deck in self.col.decks.all():
            update(deck)
        # unbury if the day has rolled over
        unburied = self.col.conf.get("lastUnburied", 0)
        if unburied < self.today:
            self.unburyCards()

    def _checkDay(self):
        # check if the day has rolled over
        if time.time() > self.dayCutoff:
            self.reset()
