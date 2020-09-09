# -*- coding: utf-8 -*-
# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import djankiserv.unki

from . import intTime

# Cards
##########################################################################

# Type: 0=new, 1=learning, 2=due
# Queue: same as above, and:
#        -1=suspended, -2=user buried, -3=sched buried
# Due is used differently for different queues.
# - new queue: note id or random int
# - rev queue: integer day
# - lrn queue: integer timestamp


class Card:  # pylint: disable=R0902
    def __init__(self, col, card_id=None):
        self.col = col
        self.timerStarted = None
        self._qa = None
        self._note = None
        self.mod = None
        self.usn = None

        if card_id:
            self.id = card_id
            self.load()
        else:
            # to flush, set nid, ord, and due
            self.id = col.timestamp_for_table("cards")
            self.did = 1
            self.crt = intTime()
            self.type = 0
            self.queue = 0
            self.ivl = 0
            self.factor = 0
            self.reps = 0
            self.lapses = 0
            self.left = 0
            self.odue = 0
            self.odid = 0
            self.flags = 0
            self.data = ""

    def flush(self):
        self.mod = intTime()
        self.usn = self.col.usn
        # bug check
        if self.queue == 2 and self.odue and not self.col.decks.isDyn(self.did):
            raise Exception("odueInvalid")  # FIXME: here upstream ran runHook("odueInvalid")
        assert self.due < 4294967296

        self.col.db.execute(
            djankiserv.unki.AnkiDataModel.insert_on_conflict_update(self.col.username, "cards"),
            self.id,
            self.nid,
            self.did,
            self.ord,
            self.mod,
            self.usn,
            self.type,
            self.queue,
            self.due,
            self.ivl,
            self.factor,
            self.reps,
            self.lapses,
            self.left,
            self.odue,
            self.odid,
            self.flags,
            self.data,
        )

    def load(self):
        (
            self.id,
            self.nid,
            self.did,
            self.ord,
            self.mod,
            self.usn,
            self.type,
            self.queue,
            self.due,
            self.ivl,
            self.factor,
            self.reps,
            self.lapses,
            self.left,
            self.odue,
            self.odid,
            self.flags,
            self.data,
        ) = self.col.db.first(f"select * from {self.col.username}.cards where id = %s", self.id)
        self._qa = None
        self._note = None
