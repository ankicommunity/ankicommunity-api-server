# -*- coding: utf-8 -*-

import json
import os
import pathlib
import time

from django.conf import settings

from . import assets  # noqa # pylint: disable=C0415,W0611
from . import SyncTestRemoteServer, TestRemoteMediaServer, TestRemoteSyncServer


class SyncTestRemoteServerUp(SyncTestRemoteServer):
    # override SyncTestRemoteServer
    def assets_package(self):
        return "assets.up"


class SyncTestRemoteSyncServerUp(SyncTestRemoteServerUp):  # pylint: disable=R0904
    ##
    ## test the `start` methods
    ##
    def test_start_one_note_delete_unused_media(self):
        self._standard_no_diff_test(TestRemoteSyncServer().start, "one_note_delete_unused_media", with_start=False)

    def test_start_two_notes_one_added(self):
        self._standard_no_diff_test(TestRemoteSyncServer().start, "two_notes_one_added", with_start=False)

    def test_start_two_notes_two_studied(self):
        self._standard_no_diff_test(TestRemoteSyncServer().start, "two_notes_two_studied", with_start=False)

    def test_start_start_two_notes_delete_one(self):
        self._standard_no_diff_test(TestRemoteSyncServer().start, "start_two_notes_delete_one", with_start=False)

    def test_start_new_deck_one_new_card(self):
        self._standard_no_diff_test(TestRemoteSyncServer().start, "new_deck_one_new_card", with_start=False)

    def test_start_rem_new_deck_one_new_card(self):
        self._standard_no_diff_test(TestRemoteSyncServer().start, "rem_new_deck_one_new_card", with_start=False)

    def test_start_modify_deck_conf(self):
        self._standard_no_diff_test(TestRemoteSyncServer().start, "modify_deck_conf", with_start=False)

    ##
    ## test the `applyGraves` methods
    ##
    def test_applyGraves_one_note_delete_unused_media(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyGraves, "one_note_delete_unused_media", with_start=True)

    def test_applyGraves_two_notes_one_added(self):
        # two_notes_one_added
        rs = TestRemoteSyncServer()
        test_set = "two_notes_one_added"
        rs_method = rs.applyGraves

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
        self.assertEqual(len(diff.keys()), 1)

        # FIXME: for some totally unknown reason, the client seems to want to send a grave when adding one...
        # It is completely unclear where this comes from at the moment as it doesn't appear
        # to correspond to any note that is created. This is probably a nasty bug...
        graves = diff["graves"]
        self.assertEqual(len(graves[0]), 0)
        self.assertEqual(len(graves[1]), 1)

    def test_applyGraves_two_notes_two_studied(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyGraves, "two_notes_two_studied", with_start=True)

    def test_applyGraves_start_two_notes_delete_one(self):
        # start_two_notes_delete_one
        rs = TestRemoteSyncServer()
        test_set = "start_two_notes_delete_one"
        rs_method = rs.applyGraves

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
        self.assertEqual(len(diff.keys()), 3)

        # FIXME: should probably check the contents is the expected contents
        self.assertEqual(len(diff["notes"][0]), len(diff["notes"][1]) + 1)  # should have deleted one note
        self.assertEqual(len(diff["cards"][0]), len(diff["cards"][1]) + 1)  # should have deleted one card

        # FIXME: should definitely check to see there is a 'note grave' and a 'card grave' with the
        # ids that are in excess for the first two asserts!!!???
        self.assertEqual(len(diff["graves"][0]), len(diff["graves"][1]) - 2)  # should have added 2 graves

    def test_applyGraves_new_deck_one_new_card(self):
        # two_notes_one_added
        rs = TestRemoteSyncServer()
        test_set = "new_deck_one_new_card"
        rs_method = rs.applyGraves

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
        self.assertEqual(len(diff.keys()), 1)

        # FIXME: for some totally unknown reason, the client seems to want to send a grave when adding one...
        # It is completely unclear where this comes from at the moment as it doesn't appear
        # to correspond to any note that is created. This is probably a nasty bug...
        graves = diff["graves"]
        self.assertEqual(len(graves[0]), 0)
        self.assertEqual(len(graves[1]), 1)

    def test_applyGraves_rem_new_deck_one_new_card(self):
        # rem_new_deck_one_new_card
        rs = TestRemoteSyncServer()
        test_set = "rem_new_deck_one_new_card"
        rs_method = rs.applyGraves

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
        self.assertEqual(len(diff.keys()), 4)

        # FIXME: should probably check the contents is the expected contents
        self.assertEqual(len(diff["notes"][0]), len(diff["notes"][1]) + 1)  # should have deleted one note
        self.assertEqual(len(diff["cards"][0]), len(diff["cards"][1]) + 1)  # should have deleted one card

        self.assertEqual(len(diff["col"]), 1)  # just decks

        decks = diff["col"]["decks"]
        # # the default deck shouldn't have changed
        # self.assertEqual(json.loads(decks[0])["1"], json.loads(decks[1])["1"])

        # FIXME: this is very probably a bug in the actual code. I calculate there should be updated
        # "today" figures for all decks. It may be because these values are not updated until the end
        # of the sync run because the chunks haven't been sent yet, in which case it simply shows we
        # need a solution for simulating a long "transaction" across multiple calls...
        today = int((time.time() - before["col"][0][1]) // 86400)  # get today
        ref_def_deck = json.loads(decks[0])["1"]  # col_json["decks"]
        new_def_decks = json.loads(decks[1])["1"]
        ref_def_deck["lrnToday"][0] = today
        ref_def_deck["newToday"][0] = today
        ref_def_deck["revToday"][0] = today
        ref_def_deck["timeToday"][0] = today

        self.assertEqual(ref_def_deck, new_def_decks)

        # there should be one less deck
        self.assertEqual(len(json.loads(decks[0]).keys()), len(json.loads(decks[1]).keys()) + 1)

    ##
    ## test the `applyChanges` methods
    ##
    def test_applyChanges_one_note_delete_unused_media(self):
        self._standard_no_diff_test(
            TestRemoteSyncServer().applyChanges,
            "one_note_delete_unused_media",
            with_start=True,
            expect_today_last_unburied=True,
        )

    def test_applyChanges_two_notes_one_added(self):  # pylint: disable=R0914
        # two_notes_one_added
        rs = TestRemoteSyncServer()
        test_set = "two_notes_one_added"
        rs_method = rs.applyChanges

        # hostKey will get a session in the remote server which contains auth
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        # this puts some values into the cache which we need for subsequent calls
        # we don't actually care what is in the start json
        rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        before = self.load_db_to_dict()
        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))
        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()
        diff = self.db_diff(before, after)

        self.assertEqual(len(diff.keys()), 1)

        col = diff["col"]
        col_json = self.load_json_asset(f"{test_set}/post_{rs_method.__name__}_col.json")

        self.assertEqual(len(col), 3)  # conf, models and tags

        ref_conf = col_json["conf"]
        new_conf = col["conf"][1]
        self.assertEqual(ref_conf, new_conf)

        ref_models = col_json["models"]
        new_models = json.loads(col["models"][1])
        self.assertEqual(ref_models, new_models)

        ref_tags = col_json["tags"]
        new_tags = json.loads(col["tags"][1])  # tags is the 12th column
        self.assertEqual(ref_tags, new_tags)

        # FIXME: understand why we don't have a difference in decks with the "today's" values

    def test_applyChanges_two_notes_two_studied(self):  # pylint: disable=R0914
        # two_notes_two_studied
        rs = TestRemoteSyncServer()
        test_set = "two_notes_two_studied"
        rs_method = rs.applyChanges

        # hostKey will get a session in the remote server which contains auth
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()

        # this puts some values into the cache which we need for subsequent calls
        # we don't actually care what is in the start json
        rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        # needs to be two:
        # first, send the current decks changes from pre_....json, which will have an out-of-date set of totals for
        # the day in this case we will get a set of new, zeroed changes for the new day ([=today - col create date
        # in days, 0] second, send an updated decks changes with today's date, and then in the db we should probably
        # not get any changes because what has been sent is the most up-to-date version of this

        # Option 1:
        #
        # here we hack to find what we are expecting for "today's" values. This gets recalculated by both client
        # and server, so there are two cases - one where we send outdated values (is this actually possible? In
        # any case the server should behave properly...) and we get updated values sent back by the server, and
        # another case where we sent proper values for today's date and then expect nothing in return
        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        before = self.load_db_to_dict()
        today = int((time.time() - before["col"][0][1]) // 86400)

        input_json = self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json")
        for k in ["lrnToday", "newToday", "revToday", "timeToday"]:
            # this means we haven't done anything yet today, so the studying was done on a previous day. We expect
            # an empty return for this from the server, which is what is in our json asset
            input_json["changes"]["decks"][0][0][k] = [today, 0]

        output = rs_method(**input_json)
        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()
        diff = self.db_diff(before, after)
        self.assertEqual(len(diff.keys()), 1)

        col_json = self.load_json_asset(f"{test_set}/post_{rs_method.__name__}_col.json")
        ref_decks = col_json["decks"]

        col = diff["col"]
        # The DB should now have the updated values and be identical otherwise
        self.assertEqual(len(col), 1)  # the only diff should be the 'decks' column
        self.assertEqual(input_json["changes"]["decks"][0][0], json.loads(col["decks"][1])["1"])

        # Option 2:
        #
        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        before = self.load_db_to_dict()

        # FIXME: WTF? This appears to change and my calculation says that it should NOT return
        # what it currently does...
        # by my calculations I should have to change the col.crt to today to get what I do!!!???
        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))

        output_json = self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json")
        self.assertEqual(output, output_json)

        after = self.load_db_to_dict()
        diff = self.db_diff(before, after)
        self.assertEqual(len(diff.keys()), 1)

        col = diff["col"]
        self.assertEqual(len(col), 1)

        ref_decks = col_json["decks"]
        new_decks = json.loads(col["decks"][1])

        self.assertEqual(ref_decks, new_decks)

    def test_applyChanges_start_two_notes_delete_one(self):
        # start_two_notes_delete_one
        rs = TestRemoteSyncServer()
        test_set = "start_two_notes_delete_one"
        rs_method = rs.applyChanges

        # hostKey will get a session in the remote server which contains auth
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()
        # this puts some values into the cache which we need for subsequent calls
        # we don't actually care what is in the start json
        rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        before = self.load_db_to_dict()

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))
        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()

        diff = self.db_diff(before, after)
        self.assertEqual(len(diff.keys()), 1)

        col = diff["col"]
        self.assertEqual(len(col), 1)

        col_json = self.load_json_asset(f"{test_set}/post_{rs_method.__name__}_col.json")

        ref_conf = col_json["conf"]
        new_conf = col["conf"][1]
        self.assertEqual(ref_conf, new_conf)

    def test_applyChanges_new_deck_one_new_card(self):  # pylint: disable=R0914
        # new_deck_one_new_card
        rs = TestRemoteSyncServer()
        test_set = "new_deck_one_new_card"
        rs_method = rs.applyChanges

        # hostKey will get a session in the remote server which contains auth
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        # this puts some values into the cache which we need for subsequent calls
        # we don't actually care what is in the start json
        rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        before = self.load_db_to_dict()
        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))
        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()
        diff = self.db_diff(before, after)

        self.assertEqual(len(diff.keys()), 1)

        col = diff["col"]
        col_json = self.load_json_asset(f"{test_set}/post_{rs_method.__name__}_col.json")

        self.assertEqual(len(col), 4)  # conf, models, decks and tags
        ref_conf = col_json["conf"]
        new_conf = col["conf"][1]
        self.assertEqual(ref_conf, new_conf)

        # FIXME: this is very probably a bug in the actual code. I calculate there should be updated
        # "today" figures for all decks. It may be because these values are not updated until the end
        # of the sync run because the chunks haven't been sent yet, in which case it simply shows we
        # need a solution for simulating a long "transaction" across multiple calls...

        today = int((time.time() - before["col"][0][1]) // 86400)  # get today
        ref_decks = col_json["decks"]
        new_decks = json.loads(col["decks"][1])
        # FIXME: totally random! why has only the default deck been updated???
        ref_decks["1"]["lrnToday"][0] = today
        ref_decks["1"]["newToday"][0] = today
        ref_decks["1"]["revToday"][0] = today
        ref_decks["1"]["timeToday"][0] = today

        self.assertEqual(ref_decks, new_decks)

        for j in ["models", "tags"]:
            self.assertEqual(col_json[j], json.loads(col[j][1]))

    def test_applyChanges_rem_new_deck_one_new_card(self):
        self._standard_no_diff_test(
            TestRemoteSyncServer().applyChanges,
            "rem_new_deck_one_new_card",
            with_start=True,
            expect_today_last_unburied=False,  # we haven't done any reviews in this scenario yet, so no unburying
        )

    def test_applyChanges_modify_deck_conf(self):

        # modify_deck_conf
        rs = TestRemoteSyncServer()
        test_set = "modify_deck_conf"
        rs_method = rs.applyChanges

        # hostKey will get a session in the remote server which contains auth
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()
        # this puts some values into the cache which we need for subsequent calls
        # we don't actually care what is in the start json
        rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        before = self.load_db_to_dict()

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))

        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()

        diff = self.db_diff(before, after)
        self.assertEqual(len(diff.keys()), 1)

        col = diff["col"]
        self.assertEqual(len(col), 3)

        col_json = self.load_json_asset(f"{test_set}/post_{rs_method.__name__}_col.json")

        self.assertEqual(col_json["conf"], col["conf"][1])
        self.assertEqual(col_json["dconf"], json.loads(col["dconf"][1]))
        self.assertEqual(col_json["decks"], json.loads(col["decks"][1]))

    ##
    ## test the `chunk` methods
    ##
    def test_chunk_one_note_delete_unused_media(self):
        self._standard_chunk_test("one_note_delete_unused_media")

    def test_chunk_two_notes_one_added(self):
        self._standard_chunk_test("two_notes_one_added")

    def test_chunk_two_notes_two_studied(self):
        self._standard_chunk_test("two_notes_two_studied")

    def test_chunk_start_two_notes_delete_one(self):
        self._standard_chunk_test("start_two_notes_delete_one")

    def test_chunk_new_deck_one_new_card(self):
        self._standard_chunk_test("new_deck_one_new_card")

    def test_chunk_rem_new_deck_one_new_card(self):
        self._standard_chunk_test("rem_new_deck_one_new_card")

    def test_chunk_modify_deck_conf(self):
        self._standard_chunk_test("modify_deck_conf")

    ##
    ## test the `applyChunk` methods
    ##
    def test_applyChunk_one_note_delete_unused_media(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyChunk, "one_note_delete_unused_media", with_start=True)

    def test_applyChunk_two_notes_one_added(self):
        # two_notes_one_added
        rs = TestRemoteSyncServer()
        test_set = "two_notes_one_added"
        rs_method = rs.applyChunk

        # hostKey will get a session in the remote server which contains auth
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        # this puts some values into the cache which we need for subsequent calls
        # we don't actually care about what is in the start json!
        rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        before = self.load_db_to_dict()

        input_json = self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json")
        new_cards = [tuple(x) for x in input_json["chunk"]["cards"]]

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))
        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()
        diff = self.db_diff(before, after)
        self.assertEqual(len(diff), 2)
        # after db cards should equal before db cards plus new cards
        self.assertEqual(sorted(diff["cards"][0] + new_cards), sorted(diff["cards"][1]))

        # FIXME: something funky happens here.
        # The note that gets sent via POST really is missing values for sfld and csum, so maybe these get
        # flushed to the sqlite3 db after this method. In any case, even when there is a direct dowload request
        # just after this sync then the downloaded DB has the sfld and csum filled, so somewhere on the server
        # these are also being calculated. So our behaviour is correct, in order to check, just load the post_applyChunk
        # reference DB and compare the notes tables
        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/post_{rs_method.__name__}.sql")
        expected = self.load_db_to_dict()

        # after db notes should equal before db notes plus new notes
        self.assertEqual(sorted(expected["notes"]), sorted(diff["notes"][1]))

    def test_applyChunk_two_notes_two_studied(self):
        # two_notes_two_studied
        rs = TestRemoteSyncServer()
        test_set = "two_notes_two_studied"
        rs_method = rs.applyChunk

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

        self.assertEqual(len(diff), 2)

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/post_{rs_method.__name__}.sql")
        expected = self.load_db_to_dict()

        # get cards from the db and compare ref with calculated
        self.assertEqual(sorted(expected["cards"]), sorted(diff["cards"][1]))

        # get revlog from the db and compare ref with calculated - FIXME: this doesn't seem right, does it???
        self.assertEqual(sorted(expected["revlog"]), sorted(diff["revlog"][1]))

    def test_applyChunk_start_two_notes_delete_one(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyChunk, "start_two_notes_delete_one", with_start=True)

    def test_applyChunk_new_deck_one_new_card(self):
        # new_deck_one_new_card
        rs = TestRemoteSyncServer()
        test_set = "new_deck_one_new_card"
        rs_method = rs.applyChunk

        # hostKey will get a session in the remote server which contains auth
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        # this puts some values into the cache which we need for subsequent calls
        # we don't actually care about what is in the start json!
        rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        before = self.load_db_to_dict()

        input_json = self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json")
        new_cards = [tuple(x) for x in input_json["chunk"]["cards"]]

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))
        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()
        diff = self.db_diff(before, after)
        self.assertEqual(len(diff), 2)
        # after db cards should equal before db cards plus new cards
        self.assertEqual(sorted(diff["cards"][0] + new_cards), sorted(diff["cards"][1]))

        # FIXME: something funky happens here.
        # The note that gets sent via POST really is missing values for sfld and csum, so maybe these get
        # flushed to the sqlite3 db after this method. In any case, even when there is a direct dowload request
        # just after this sync then the downloaded DB has the sfld and csum filled, so somewhere on the server
        # these are also being calculated. So our behaviour is correct, in order to check, just load the post_applyChunk
        # reference DB and compare the notes tables
        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/post_{rs_method.__name__}.sql")
        expected = self.load_db_to_dict()

        # after db notes should equal before db notes plus new notes
        self.assertEqual(sorted(expected["notes"]), sorted(diff["notes"][1]))

    def test_applyChunk_rem_new_deck_one_new_card(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyChunk, "rem_new_deck_one_new_card", with_start=True)

    def test_applyChunk_modify_deck_conf(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyChunk, "modify_deck_conf", with_start=True)

    ##
    ## test the `sanityCheck2` methods
    ##
    def test_sanityCheck2_one_note_delete_unused_media(self):
        self._standard_sanity_check2_test("one_note_delete_unused_media", to_review=1)

    def test_sanityCheck2_two_notes_one_added(self):
        self._standard_no_diff_test(TestRemoteSyncServer().sanityCheck2, "two_notes_one_added", with_start=True)

    def test_sanityCheck2_two_notes_two_studied(self):
        self._standard_sanity_check2_test("two_notes_two_studied", to_review=2)

    def test_sanityCheck2_start_two_notes_delete_one(self):
        self._standard_sanity_check2_test("start_two_notes_delete_one", to_review=1)

    def test_sanityCheck2_new_deck_one_new_card(self):
        self._standard_no_diff_test(TestRemoteSyncServer().sanityCheck2, "new_deck_one_new_card", with_start=True)

    def test_sanityCheck2_rem_new_deck_one_new_card(self):
        self._standard_no_diff_test(TestRemoteSyncServer().sanityCheck2, "rem_new_deck_one_new_card", with_start=True)

    def test_sanityCheck2_modify_deck_conf(self):
        self._standard_no_diff_test(TestRemoteSyncServer().sanityCheck2, "modify_deck_conf", with_start=True)

    ##
    ## test the `finish` methods
    ##
    def test_finish_one_note_delete_unused_media(self):
        self._standard_finish_test("one_note_delete_unused_media")

    def test_finish_two_notes_one_added(self):
        self._standard_finish_test("two_notes_one_added")

    def test_finish_two_notes_two_studied(self):
        self._standard_finish_test("two_notes_two_studied")

    def test_finish_start_two_notes_delete_one(self):
        self._standard_finish_test("start_two_notes_delete_one")

    def test_finish_new_deck_one_new_card(self):
        self._standard_finish_test("new_deck_one_new_card")

    def test_finish_rem_new_deck_one_new_card(self):
        self._standard_finish_test("rem_new_deck_one_new_card")

    def test_finish_modify_deck_conf(self):
        self._standard_finish_test("modify_deck_conf")

    # FIXME: should we have an abort?
    # def abort(self, **kw):


class SyncTestRemoteMediaServerUp(SyncTestRemoteServerUp):
    ##
    ## test the `begin` methods
    ##
    def test_begin_one_note_delete_unused_media(self):
        self._standard_begin_test("one_note_delete_unused_media", expected_usn=2)

    def test_begin_one_note_w_media(self):
        self._standard_begin_test("one_note_w_media", expected_usn=0)

    def test_begin_start_two_notes_delete_one(self):
        self._standard_begin_test("start_two_notes_delete_one", expected_usn=2)

    def test_begin_two_notes_one_added(self):
        self._standard_begin_test("two_notes_one_added", expected_usn=1)

    def test_begin_two_notes_two_studied(self):
        self._standard_begin_test("two_notes_two_studied", expected_usn=2)

    ##
    ## test the `mediaChanges` methods
    ##
    def _standard_media_changes_up_test(self, test_set):
        rms = TestRemoteMediaServer()
        rms.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rms.meta()
        rms.begin()  # this sets the skey

        rs_method = rms.mediaChanges

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")

        before = self.load_db_to_dict()

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))["data"]
        self.assertFalse(output)

        # no db change expected
        after = self.load_db_to_dict()
        self.assertFalse(self.db_diff(before, after))

    def test_mediaChanges_one_note_delete_unused_media(self):
        self._standard_media_changes_up_test("one_note_delete_unused_media")

    def test_mediaChanges_one_note_w_media(self):
        self._standard_media_changes_up_test("one_note_w_media")

    def test_mediaChanges_two_notes_one_added(self):
        self._standard_media_changes_up_test("two_notes_one_added")

    ##
    ## test the `uploadChanges` methods
    ##
    def _standard_upload_changes_up_test(self, test_set, new_media_entry):
        rms = TestRemoteMediaServer()
        rms.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rms.meta()
        rms.begin()  # this sets the skey

        rs_method = rms.uploadChanges

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")

        before = self.load_db_to_dict()
        zip_data = self.load_bin_asset(f"{test_set}/pre_{rs_method.__name__}.bin")
        output = rs_method(zip_file=zip_data["data"])

        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()
        diff = self.db_diff(before, after)
        media = diff["media"]
        # expecting one new file in the db
        self.assertEqual(media[0] + [new_media_entry], media[1])

        # we should have copied the file to the new path
        # we should, however, probably have a specific dir that we create and use only for the tests...
        self.assertTrue(
            pathlib.Path(
                os.path.join(settings.DJANKISERV_DATA_ROOT, SyncTestRemoteServer.USERNAME, new_media_entry[0])
            ).exists()
        )

    def test_uploadChanges_one_note_delete_unused_media(self):
        rms = TestRemoteMediaServer()
        rms.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rms.meta()
        rms.begin()  # this sets the skey

        test_set = "one_note_delete_unused_media"
        rs_method = rms.uploadChanges

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")

        before = self.load_db_to_dict()
        zip_data = self.load_bin_asset(f"{test_set}/pre_{rs_method.__name__}.bin")
        output = rs_method(zip_file=zip_data["data"])

        self.assertEqual(output, self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json"))

        after = self.load_db_to_dict()
        diff = self.db_diff(before, after)
        media = diff["media"]
        # expecting one file 'deleted' in the db
        self.assertEqual([media[0][0], ("wo2.png", 3, None)], media[1])

        # FIXME: we should probably test that there is a file there that gets deleted by the method
        # self.assertTrue(pathlib.Path(f'{settings.DJANKISERV_DATA_ROOT}/
        # {SyncTestRemoteServer.USERNAME}/wo2.png').exists())

    def test_uploadChanges_one_note_w_media(self):
        self._standard_upload_changes_up_test(
            "one_note_w_media", ("wo1.png", 1, "f18e0dc430b26c75e16315bd6367bdcc744ea2c8")
        )

    def test_uploadChanges_two_notes_one_added(self):
        self._standard_upload_changes_up_test(
            "two_notes_one_added", ("wo2.png", 2, "f18e0dc430b26c75e16315bd6367bdcc744ea2c8")
        )

    ##
    ## test the `mediaSanity` methods
    ##
    def test_mediaSanity_one_note_delete_unused_media(self):
        self._standard_media_sanity_test("one_note_delete_unused_media")

    def test_mediaSanity_one_note_w_media(self):
        self._standard_media_sanity_test("one_note_w_media")

    def test_mediaSanity_two_notes_one_added(self):
        self._standard_media_sanity_test("two_notes_one_added")
