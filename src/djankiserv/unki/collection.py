# -*- coding: utf-8 -*-

import copy
import datetime
import json
import logging
import os
import pathlib
import pkgutil
import random
import re
import shutil
import time
import unicodedata

import djankiserv.unki
from djankiserv.assets import jsonfiles  # noqa: 401  # pylint: disable=W0611
from djankiserv.unki.database import StandardDB

from . import REM_CARD, REM_NOTE, checksum, fieldChecksum, ids2str, intTime, joinFields, splitFields, stripHTMLMedia
from .cards import Card
from .decks import DeckManager
from .models import ModelManager
from .notes import Note
from .sched import Scheduler

MODEL_STD = 0
NEW_CARDS_DUE = 1

logger = logging.getLogger("djankiserv.unki.collection")


# from anki.utils
def maxID(db, username):
    "Return the first safe ID to use."
    now = max(
        intTime(1000),
        db.scalar(f"select max(id) from {username}.notes") or 0,
        db.scalar(f"select max(id) from {username}.cards") or 0,
    )
    return now + 1


class Collection:  # pylint: disable=R0902,R0904
    def __init__(self, username, media_dir_base):
        self.username = username
        self._media_dir = os.path.join(media_dir_base, self.username)
        self.tags = None  # to make pylint happy
        self.tags_changed = False  # to make pylint happy
        self.mod = 0  # to make pylint happy

        self.db = StandardDB()
        self.models = ModelManager(self)
        self.decks = DeckManager(self)

        create = not StandardDB.schema_exists(self.username)
        if create:
            StandardDB.create_schema(self.username)
            self.db.execute(f"update {self.username}.col set scm = %s", intTime(1000))

            c = json.loads(
                pkgutil.get_data("djankiserv.assets.jsonfiles", "default_collection_conf.json").decode("utf-8")
            )
            g = json.loads(pkgutil.get_data("djankiserv.assets.jsonfiles", "default_deck.json").decode("utf-8"))
            # g["mod"] = intTime() FIXME: is this necessary??? can we leave the original mod times?
            gc = json.loads(pkgutil.get_data("djankiserv.assets.jsonfiles", "default_deck_conf.json").decode("utf-8"))

            model = json.loads(pkgutil.get_data("djankiserv.assets.jsonfiles", "default_model.json").decode("utf-8"))

            self.db.execute(
                f"update {self.username}.col set conf = %s, decks = %s, dconf = %s, models = %s",
                json.dumps(c),
                json.dumps({"1": g}),
                json.dumps({"1": gc}),
                json.dumps(model),
            )

        self._lastSave = time.time()
        self.load()

        if not self.crt:
            d = datetime.datetime.today()
            d -= datetime.timedelta(hours=4)
            d = datetime.datetime(d.year, d.month, d.day)
            d += datetime.timedelta(hours=4)
            self.crt = int(time.mktime(d.timetuple()))

        self.save()

        self.sched = Scheduler(self)

        if not self.conf.get("newBury", False):
            self.conf["newBury"] = True
            self.db.mod = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *args):
        # FIXME: should this be self.close(save=True)?
        self.close()

    @staticmethod
    def delete(username, media_dir_base):
        shutil.rmtree(os.path.join(media_dir_base, username), ignore_errors=True)
        StandardDB.delete_schema(username)

    def media_changes(self, client_last_usn):

        result = []
        server_last_usn = self.last_media_usn()

        if client_last_usn < server_last_usn or client_last_usn == 0:
            for fname, usn, csum, in self.db.execute(
                f"select fname,usn,csum from {self.username}.media order by usn desc limit %s",
                server_last_usn - client_last_usn,
            ):
                result.append([fname, usn, csum])

        result.reverse()
        return result

    def media_dir(self):
        return self._media_dir

    def last_media_usn(self):
        return self.db.scalar(f"SELECT max(usn) FROM {self.username}.media") or 0

    def media_count(self):
        return self.db.scalar(f"SELECT count(0) FROM {self.username}.media WHERE csum IS NOT NULL")

    def media_sync_delete(self, fname):
        fpath = os.path.join(self.media_dir(), fname)
        if os.path.exists(fpath):
            os.remove(fpath)
        self.db.execute(
            f"UPDATE {self.username}.media SET csum = NULL, usn = %s WHERE fname = %s",
            self.last_media_usn() + 1,
            fname,
        )

    @staticmethod
    def check_zip_data(zip_file):
        max_zip_size = 100 * 1024 * 1024
        max_meta_file_size = 100000

        meta_file_size = zip_file.getinfo("_meta").file_size
        sum_file_sizes = sum(info.file_size for info in zip_file.infolist())

        if meta_file_size > max_meta_file_size:
            raise ValueError("Zip file's metadata file is larger than %s " "Bytes." % max_meta_file_size)
        if sum_file_sizes > max_zip_size:
            raise ValueError("Zip file contents are larger than %s Bytes." % max_zip_size)

    def _remove_media_files(self, filenames):
        """
        Marks all files in list filenames as deleted and removes them from the
        media directory.
        """
        logger.debug("Removing %d files from media dir.", len(filenames))
        for filename in filenames:
            try:
                self.media_sync_delete(filename)
                self.db.commit()
            except OSError as err:
                logger.error("Error when removing file '%s' from media dir: " "%s", filename, str(err))

    def adopt_media_changes_from_zip(self, zip_file):  # pylint: disable=R0914
        """
        Adds and removes files to/from the database and media directory
        according to the data in zip file zipData.
        """

        # Get meta info first.
        meta = json.loads(zip_file.read("_meta").decode())

        # Remove media files that were removed on the client.
        media_to_remove = []
        for normname, ordinal in meta:
            if not ordinal:
                media_to_remove.append(unicodedata.normalize("NFC", normname))

        # Add media files that were added on the client.
        media_to_add = []
        usn = self.last_media_usn()
        oldUsn = usn
        for i in zip_file.infolist():
            if i.filename == "_meta":  # Ignore previously retrieved metadata.
                continue

            file_data = zip_file.read(i)
            csum = checksum(file_data)
            filename = unicodedata.normalize("NFC", meta[int(i.filename)][0])

            # FIXME: need to completely redo everything regarding media files!!!
            pathlib.Path(self.media_dir()).mkdir(parents=True, exist_ok=True)
            file_path = os.path.join(self.media_dir(), filename)

            # Save file to media directory.
            with open(file_path, "wb") as f:
                f.write(file_data)

            usn += 1
            media_to_add.append((filename, usn, csum))

        # We count all files we are to remove, even if we don't have them in
        # our media directory and our db doesn't know about them.
        processed_count = len(media_to_remove) + len(media_to_add)

        assert len(meta) == processed_count  # sanity check

        if media_to_remove:
            self._remove_media_files(media_to_remove)

        if media_to_add:
            sql = djankiserv.unki.AnkiDataModel.insert_on_conflict_update(self.username, "media")
            self.db.executemany(sql, media_to_add)
            self.db.commit()

        assert self.last_media_usn() == oldUsn + processed_count  # TODO: move to some unit test
        return processed_count

    def reopen(self):
        "Reconnect to DB"
        if not self.db:
            self.db = StandardDB()

    def load_tags(self, json_):
        self.tags = json.loads(json_)
        self.tags_changed = False

    def flush_tags(self):
        if self.tags_changed:
            self.db.execute(f"update {self.username}.col set tags=%s", json.dumps(self.tags))
            self.tags_changed = False

    def register_tags(self, tags, usn=None):
        "Given a list of tags, add any missing ones to tag registry."
        for t in tags:
            if t not in self.tags:
                self.tags[t] = self.usn if usn is None else usn
                self.tags_changed = True

    def all_tags(self):
        return list(self.tags.items())

    def tagstring_for_note(self, note_tags):
        "Strip duplicates, adjust case to match existing tags, and sort."
        stripped_tags = []
        for t in note_tags:
            s = re.sub("[\"']", "", t)
            for existing_tag in self.tags:
                if s.lower() == existing_tag.lower():
                    s = existing_tag
            stripped_tags.append(s)
        tags = sorted(set(stripped_tags))
        if not tags:
            return ""
        return " %s " % " ".join(tags)

    def load(self):
        (
            self.crt,
            self.mod,
            self.scm,
            self.dty,  # no longer used
            self.usn,
            self.ls,
            self.conf,
            models,
            decks,
            dconf,
            tags,
        ) = self.db.first(
            f"""
            select crt, modified, scm, dty, usn, ls,
            conf, models, decks, dconf, tags from {self.username}.col"""
        )
        self.conf = json.loads(self.conf)

        # FIXME: remove when
        # https://stackoverflow.com/questions/63760777/psycopg2-vs-mysqldb-backslash-escaping-behaviour
        # has an answer. This is due to exec'ing the inserts for the tests NOT escaping the backslashes in
        # mariadb, so when they try to get loaded they get interpreted as escapes in the json...
        # try:
        self.models.load(models)
        # except json.decoder.JSONDecodeError:
        #     self.models.load(repr(models)[1:-1])

        self.decks.load(decks, dconf)
        self.load_tags(tags)

    def flush(self, mod=None):
        "Flush state to DB, updating mod time."
        self.mod = intTime(1000) if mod is None else mod
        self.db.execute(
            f"""update {self.username}.col set
                crt=%s, modified=%s, scm=%s, dty=%s, usn=%s, ls=%s, conf=%s""",
            self.crt,
            self.mod,
            self.scm,
            self.dty,
            self.usn,
            self.ls,
            json.dumps(self.conf),
        )

    def save(self, mod=None):
        "Flush, commit DB, and take out another write lock."
        # let the managers conditionally flush
        self.models.flush()
        self.decks.flush()
        self.flush_tags()
        # and flush deck + bump mod if db has been changed
        if self.db.mod:
            self.flush(mod=mod)
            self.db.commit()
            # self.lock()
            self.db.mod = False
        self._lastSave = time.time()

    def close(self, save=True):
        "Disconnect from DB."
        if self.db:
            if save:
                self.save()

            self.db.close()
            self.db = None

    def add_graves(self, ids, obj_type):
        self.db.executemany(
            f"insert into {self.username}.graves values ({self.usn}, %s, {obj_type})", ([x] for x in ids)
        )

    def get_notes(self, note_ids=None):
        where = ""
        if note_ids:
            where = f" where id in {ids2str(note_ids)}"
        return [Note(self, note_id=i) for i in self.db.list(f"select id from {self.username}.notes {where}")]

    def all_note_ids(self):
        return self.db.list(f"select id from {self.username}.notes")

    def rem_notes(self, ids):
        "Bulk delete notes by ID. Don't call this directly."
        if not ids:
            return
        strids = ids2str(ids)
        # we need to log these independently of cards, as one side may have
        # more card templates
        self.add_graves(ids, REM_NOTE)
        self.db.execute(f"delete from {self.username}.notes where id in {strids}")

    def rem_cards(self, ids, notes=True):
        "Bulk delete cards by ID."
        if not ids:
            return
        sids = ids2str(ids)
        nids = self.db.list(f"select nid from {self.username}.cards where id in " + sids)
        # remove cards
        self.add_graves(ids, REM_CARD)
        self.db.execute(f"delete from {self.username}.cards where id in " + sids)
        # then notes
        if not notes:
            return
        nids = self.db.list(
            f"""select id from {self.username}.notes
            where id in {ids2str(nids)} and id not in (select nid from {self.username}.cards)"""
        )
        self.rem_notes(nids)

    def update_field_cache(self, nids):
        "Update field checksums and sort cache, after find&replace, etc."
        snids = ids2str(nids)

        r = []
        for (nid, mid, flds) in self.db.execute(f"select id, mid, flds from {self.username}.notes where id in {snids}"):
            fields = splitFields(flds)
            model = self.models.get(mid)
            if not model:
                # note points to invalid model
                continue
            r.append((stripHTMLMedia(fields[self.models.sort_idx(model)]), fieldChecksum(fields[0]), nid))
        # apply, relying on calling code to bump usn+mod
        self.db.executemany(f"update {self.username}.notes set sfld=%s, csum=%s where id=%s", r)

    def basic_check(self):
        "Basic integrity check for syncing. True if ok."
        # cards without notes
        # FIXME: this should be done with a foreign key!!!
        if self.db.scalar(
            f"""select 1 from {self.username}.cards
                where nid not in (select id from {self.username}.notes) limit 1"""
        ):
            return False
        # notes without cards or models
        # FIXME: this can be done with foreign keys when migrate to new collection tables structure
        if self.db.scalar(
            f"""select 1 from {self.username}.notes where id not in (select distinct nid from {self.username}.cards)
                                or mid not in {ids2str(self.models.ids())} limit 1"""
        ):
            return False
        # invalid ords
        for model in self.models.all():
            # ignore clozes
            if model["type"] != MODEL_STD:
                continue
            ids_string = ids2str([template["ord"] for template in model["tmpls"]])
            if self.db.scalar(
                f"""select 1 from {self.username}.cards where ord not in {ids_string} and nid in (
                    select id from {self.username}.notes where mid = %s) limit 1""",
                model["id"],
            ):
                return False
        return True

    # all new...
    def new_note(self, model):
        return Note(self, model)

    def set_note_review_in(self, note_id, review_in):
        # This method *should* allow one to change the due date. It DEFINITELY hasn't been properly
        # tested yet though!!!
        note = self.get_note(note_id=note_id)

        # see https://github.com/ankidroid/Anki-Android/wiki/Database-Structure
        # for more details of ids
        # type            integer not null,
        #   -- 0=new, 1=learning, 2=due, 3=filtered
        # queue           integer not null,
        #   -- -3=sched buried, -2=user buried, -1=suspended,
        #   -- 0=new, 1=learning, 2=due (as for type)
        #   -- 3=in learning, next rev in at least a day after the previous review
        # due             integer not null,
        #  -- Due is used differently for different card types:
        #  --   new: note id or random int
        #  --   due: integer day, relative to the collection's creation time
        #  --   learning: integer timestamp
        # odue            integer not null,
        #   -- original due: only used when the card is currently in filtered deck
        # odid            integer not null,
        #   -- original did: only used when the card is currently in filtered deck

        # TODO: we should also be able to add definitions from the UI

        # TODO: decide what to do about:
        # factor
        # ivl
        # filtered cards

        # FIXME: this may be way too dumb to actually work - I am assuming this will work not
        # only for cards that are for reviewing in the future but also new and learning cards
        # and that is just a blind guess! There may well be other fields/things that need to
        # be modified in addition to factor, ivl and filtered cards

        due = self.today() + review_in
        for card in note.cards():
            if card.type == 3:
                raise Exception("We don't know what to do with filtered cards yet, come back soon")

            card.type = 2
            card.queue = 2
            card.due = due
            card.flush()

        self.save()  # FIXME: Find a better way to unlock the db  - is this still necessary???

    def today(self):
        return int((time.time() - self.crt) // 86400)

    def create_note(self, note_json, deck_name, review_in=0):
        # models.by_name <- the model MUST exist
        model_name = note_json["model"]
        model = self.models.by_name(model_name)

        deck_id = self.decks.get_or_add(deck_name)

        note = self.new_note(model)
        note.model()["did"] = deck_id

        # print('my map', self.models.field_map(model))
        # print('my map', self.models.field_map(model).values())
        # raise Exception('here')
        # note_json["fields"]

        for field in self.models.field_map(model).values():
            note[field[1]["name"]] = note_json["fields"][field[0]]

        for tag in note_json["tags"]:
            if tag.strip():
                note.tags.append(tag)

        self.add_note(note)
        self.save()

        if review_in > 0:
            self.set_note_review_in(note.id, review_in)

        return note.id

    def add_note(self, note):
        "Add a note to the collection. Return number of new cards."
        # check we have card models available, then save
        cms = self.find_templates(note)
        if not cms:
            return 0
        note.flush()
        # deck conf governs which of these are used
        due = self.next_id("pos")
        # add cards
        ncards = 0
        for template in cms:
            self._new_card(note, template, due)
            ncards += 1
        return ncards

    def get_note(self, note_id):
        return Note(self, note_id=note_id)

    def find_templates(self, note):
        "Return (active), non-empty templates."
        model = note.model()
        avail = self.models.avail_ords(model, joinFields(note.fields))
        return self._templates_from_ordinals(model, avail)

    # def next_id(self, otype, inc=True):  we don't call with this it looks like so it's always True
    def next_id(self, otype):
        atype = "next" + otype.capitalize()
        an_id = self.conf.get(atype, 1)
        # if inc:
        #     self.conf[atype] = an_id + 1
        self.conf[atype] = an_id + 1

        return an_id

    @staticmethod
    def _templates_from_ordinals(model, avail):
        ok = []
        if model["type"] == MODEL_STD:
            for t in model["tmpls"]:
                if t["ord"] in avail:
                    ok.append(t)
        else:
            # cloze - generate temporary templates from first
            for ordi in avail:
                t = copy.copy(model["tmpls"][0])
                t["ord"] = ordi
                ok.append(t)
        return ok

    def _new_card(self, note, template, due, flush=True, did=None):
        "Create a new card."
        card = Card(self)
        card.nid = note.id
        card.ord = template["ord"]
        card.did = self.db.scalar(
            f"select did from {self.username}.cards where nid = %s and ord = %s", card.nid, card.ord
        )
        # Use template did (deck override) if valid, otherwise did in argument, otherwise model did
        if not card.did:
            if template["did"] and str(template["did"]) in self.decks.decks:
                card.did = template["did"]
            elif did:
                card.did = did
            else:
                card.did = note.model()["did"]
        # if invalid did, use default instead
        deck = self.decks.get(card.did)
        if deck["dyn"]:
            # must not be a filtered deck
            card.did = 1
        else:
            card.did = deck["id"]
        card.due = self._due_for_did(card.did, due)
        if flush:
            card.flush()
        return card

    def _due_for_did(self, did, due):
        conf = self.decks.conf_for_did(did)
        # in order due?
        if conf["new"]["order"] == NEW_CARDS_DUE:
            return due

        # random mode; seed with note ts so all cards of this note get the
        # same random number
        r = random.Random()
        r.seed(due)
        return r.randrange(1, max(due, 1000))

    def timestamp_for_table(self, table_name):
        "Return a non-conflicting timestamp for table."
        # Adapted from anki.utils.timestampID
        ts = intTime(1000)

        while self.db.scalar(f"select id from {self.username}.{table_name} where id = %s", ts):
            ts += 1
        return ts

    def gen_cards(self, note_ids):  # noqa: C901  # pylint: disable=R0914,R0912
        "Generate cards for non-empty templates, return ids to remove."
        # build map of (nid,ord) so we don't create dupes
        note_id_strings = ids2str(note_ids)
        have = {}
        deck_ids = {}
        dues = {}
        for card_id, note_id, ordi, deck_id, due, odue, odid in self.db.execute(
            f"select id, nid, ord, did, due, odue, odid from {self.username}.cards where nid in " + note_id_strings
        ):
            # existing cards
            if note_id not in have:
                have[note_id] = {}
            have[note_id][ordi] = card_id
            # if in a filtered deck, add new cards to original deck
            if odid != 0:
                did = odid
            # and their dids
            if note_id in deck_ids:
                if deck_ids[note_id] and deck_ids[note_id] != deck_id:
                    # cards are in two or more different decks; revert to
                    # model default
                    deck_ids[note_id] = None
            else:
                # first card or multiple cards in same deck
                deck_ids[note_id] = deck_id
            # save due
            if odid != 0:
                due = odue
            if note_id not in dues:
                dues[note_id] = due
        # build cards for each note
        data = []
        ts = maxID(self.db, self.username)
        now = intTime()
        rem = []
        usn = self.usn
        for note_id, model_id, flds in self.db.execute(
            f"select id, mid, flds from {self.username}.notes where id in " + note_id_strings
        ):
            model = self.models.get(model_id)
            available_ords = self.models.avail_ords(model, flds)
            deck_id = deck_ids.get(note_id) or model["did"]
            due = dues.get(note_id)
            # add any missing cards
            for t in self._templates_from_ordinals(model, available_ords):
                doHave = note_id in have and t["ord"] in have[note_id]
                if not doHave:
                    # FIXME: this has not been executed yet, maybe dead code to remove!!!
                    # check deck is not a cram deck
                    deck_id = t["did"] or deck_id
                    if self.decks.isDyn(deck_id):
                        deck_id = 1
                    # if the deck doesn't exist, use default instead
                    did = self.decks.get(did)["id"]
                    # use sibling due# if there is one, else use a new id
                    if due is None:
                        due = self.nextID("pos")
                    data.append((ts, note_id, did, t["ord"], now, usn, due))
                    ts += 1
            # note any cards that need removing
            if note_id in have:
                for ordi, card_id in list(have[note_id].items()):
                    if ordi not in available_ords:
                        rem.append(card_id)
        # bulk update
        self.db.executemany(
            """
            insert into {self.username}.cards values (%s,%s,%s,%s,%s,%s,0,0,%s,0,0,0,0,0,0,0,0,'')""",
            data,
        )
        return rem
