# -*- coding: utf-8 -*-

import io
import json
import os
import time
import zipfile

from django.conf import settings

from djankiserv.unki.database import db_conn

from . import SyncTestRemoteServer, TestRemoteMediaServer, TestRemoteSyncServer


class SyncTestRemoteServerDown(SyncTestRemoteServer):
    # override SyncTestRemoteServer
    @staticmethod
    def assets_package():
        return "assets.down"


class SyncTestRemoteSyncServerDown(SyncTestRemoteServerDown):  # pylint: disable=R0904
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
        self._standard_no_diff_test(TestRemoteSyncServer().applyGraves, "two_notes_one_added", with_start=True)

    def test_applyGraves_two_notes_two_studied(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyGraves, "two_notes_two_studied", with_start=True)

    def test_applyGraves_start_two_notes_delete_one(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyGraves, "start_two_notes_delete_one", with_start=True)

    def test_applyGraves_new_deck_one_new_card(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyGraves, "new_deck_one_new_card", with_start=True)

    def test_applyGraves_rem_new_deck_one_new_card(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyGraves, "rem_new_deck_one_new_card", with_start=True)

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

    def test_applyChanges_two_notes_one_added(self):
        self._standard_no_diff_test(
            TestRemoteSyncServer().applyChanges, "two_notes_one_added", with_start=True, expect_today_last_unburied=True
        )

    def test_applyChanges_two_notes_two_studied(self):
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
        # the day in this case we will get a set of new, zeroed changes for the new day ([=today - col create date in
        # days, 0] second, send an updated decks changes with today's date, and then in the db we should probably not
        # get any changes because what has been sent is the most up-to-date version of this

        # Option 1:
        #
        # here we hack to find what we are expecting for "today's" values. This gets recalculated by both client
        # and server, so there are two cases - one where we send outdated values (is this actually possible? In
        # any case the server should behave properly...) and we get updated values sent back by the server, and
        # another case where we sent proper values for today's date and then expect nothing in return

        # FIXME: implement these two
        # whether:
        # - the changes were made today
        # in this case
        # - the changes were made before today

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        before = self.load_db_to_dict()

        self.maxDiff = None
        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))

        expected = self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json")

        # we need to update because the code should say that we have both
        # - some buried that have been unburied
        # - the "today" figures should be reset to zero, given that the DB we loaded with updates was from before today
        today = int((time.time() - before["col"][0][1]) // 86400)

        for k in ["lrnToday", "newToday", "revToday", "timeToday"]:
            # this means we haven't done anything yet today, so the studying was done on a previous day. We expect
            # an empty return for this from the server, which is what is in our json asset
            expected["decks"][0][0][k] = [today, 0]

        if today and "conf" in output:  # verify there is a lastUnburied and that it has the right value
            self.assertIn("lastUnburied", output["conf"])
            self.assertEqual(output["conf"].pop("lastUnburied"), today)

        self.assertEqual(output, expected)

        after = self.load_db_to_dict()
        self.assertFalse(self.db_diff(before, after))

        # Option 2:
        #
        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        # Here we are simulating the case where the studying was done today. The ref sql db was created on "day 0", so
        # the modifications were on that day. So we simulate it being that day in the DB
        fake_crt = int(time.time())  # FIXME: will this work when the day rolls over?
        with db_conn().cursor() as cur:
            cur.execute(f"update {SyncTestRemoteServer.USERNAME}.col set crt = %s", (fake_crt,))

        before = self.load_db_to_dict()

        # FIXME: WTF? This appears to change and my calculation says that it should NOT return
        # what it currently does...
        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))

        output_json = self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json")
        output_json["crt"] = fake_crt
        self.assertEqual(output, output_json)

        after = self.load_db_to_dict()
        self.assertFalse(self.db_diff(before, after))

    def test_applyChanges_start_two_notes_delete_one(self):
        self._standard_no_diff_test(
            TestRemoteSyncServer().applyChanges,
            "start_two_notes_delete_one",
            with_start=True,
            expect_today_last_unburied=True,
        )

    def test_applyChanges_new_deck_one_new_card(self):
        # FIXME: why did a direct copy/paste of test_applyChanges_two_notes_two_studied work???
        # new_deck_one_new_card
        rs = TestRemoteSyncServer()
        test_set = "new_deck_one_new_card"
        rs_method = rs.applyChanges

        # hostKey will get a session in the remote server which contains auth
        rs.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rs.meta()

        # this puts some values into the cache which we need for subsequent calls
        # we don't actually care what is in the start json
        rs.start(**self.load_json_asset(f"{test_set}/pre_start.json"))

        # needs to be two:
        # first, send the current decks changes from pre_....json, which will have an out-of-date set of totals for
        # the day in this case we will get a set of new, zeroed changes for the new day ([=today - col create date in
        # days, 0] second, send an updated decks changes with today's date, and then in the db we should probably not
        # get any changes because what has been sent is the most up-to-date version of this

        # Option 1:
        #
        # here we hack to find what we are expecting for "today's" values. This gets recalculated by both client
        # and server, so there are two cases - one where we send outdated values (is this actually possible? In
        # any case the server should behave properly...) and we get updated values sent back by the server, and
        # another case where we sent proper values for today's date and then expect nothing in return

        # FIXME: implement these two
        # whether:
        # - the changes were made today
        # in this case
        # - the changes were made before today

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        before = self.load_db_to_dict()

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))

        expected = self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json")

        # we need to update because the code should say that we have both
        # - some buried that have been unburied
        # - the "today" figures should be reset to zero, given that the DB we loaded with updates was from before today
        today = int((time.time() - before["col"][0][1]) // 86400)

        for k in ["lrnToday", "newToday", "revToday", "timeToday"]:
            # this means we haven't done anything yet today, so the studying was done on a previous day. We expect
            # an empty return for this from the server, which is what is in our json asset
            expected["decks"][0][0][k] = [today, 0]

        if today and "conf" in output:  # verify there is a lastUnburied and that it has the right value
            self.assertIn("lastUnburied", output["conf"])
            self.assertEqual(output["conf"].pop("lastUnburied"), today)

        self.assertEqual(output, expected)

        after = self.load_db_to_dict()
        self.assertFalse(self.db_diff(before, after))

        # Option 2:
        #
        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        # Here we are simulating the case where the studying was done today. The ref sql db was created on "day 0", so
        # the modifications were on that day. So we simulate it being that day in the DB
        fake_crt = int(time.time())  # FIXME: will this work when the day rolls over?
        with db_conn().cursor() as cur:
            cur.execute(f"update {SyncTestRemoteServer.USERNAME}.col set crt = %s", (fake_crt,))

        before = self.load_db_to_dict()

        # FIXME: WTF? This appears to change and my calculation says that it should NOT return
        # what it currently does...
        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))

        output_json = self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json")
        output_json["crt"] = fake_crt
        self.assertEqual(output, output_json)

        after = self.load_db_to_dict()
        self.assertFalse(self.db_diff(before, after))

    def test_applyChanges_rem_new_deck_one_new_card(self):
        self._standard_no_diff_test(
            TestRemoteSyncServer().applyChanges,
            "rem_new_deck_one_new_card",
            with_start=True,
            expect_today_last_unburied=True,
        )

    def test_applyChanges_modify_deck_conf(self):
        # TODO: This would ideally have both the options test_applyChanges_new_deck_one_new_card has
        # and they would be made generic and DRY

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

        expected = self.load_json_asset(f"{test_set}/post_{rs_method.__name__}.json")

        # we need to update because the code should say that we have both
        # - some buried that have been unburied
        # - the "today" figures should be reset to zero, given that the DB we loaded with updates was from before today
        today = int((time.time() - before["col"][0][1]) // 86400)

        for k in ["lrnToday", "newToday", "revToday", "timeToday"]:
            # this means we haven't done anything yet today, so the studying was done on a previous day. We expect
            # an empty return for this from the server, which is what is in our json asset
            expected["decks"][0][0][k] = [today, 0]

        if today and "conf" in output:  # verify there is a lastUnburied and that it has the right value
            self.assertIn("lastUnburied", output["conf"])
            self.assertEqual(output["conf"].pop("lastUnburied"), today)

        self.assertEqual(output, expected)

        after = self.load_db_to_dict()
        self.assertFalse(self.db_diff(before, after))

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
        self._standard_no_diff_test(TestRemoteSyncServer().applyChunk, "two_notes_one_added", with_start=True)

    def test_applyChunk_two_notes_two_studied(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyChunk, "two_notes_two_studied", with_start=True)

    def test_applyChunk_start_two_notes_delete_one(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyChunk, "start_two_notes_delete_one", with_start=True)

    def test_applyChunk_new_deck_one_new_card(self):
        self._standard_no_diff_test(TestRemoteSyncServer().applyChunk, "new_deck_one_new_card", with_start=True)

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


class SyncTestRemoteMediaServerDown(SyncTestRemoteServerDown):
    ##
    ## test the `begin` methods
    ##
    def test_begin_one_note_delete_unused_media(self):
        self._standard_begin_test("one_note_delete_unused_media", expected_usn=3)

    def test_begin_one_note_w_media(self):
        self._standard_begin_test("one_note_w_media", expected_usn=1)

    def test_begin_start_two_notes_delete_one(self):
        self._standard_begin_test("start_two_notes_delete_one", expected_usn=2)

    def test_begin_two_notes_one_added(self):
        self._standard_begin_test("two_notes_one_added", expected_usn=2)

    def test_begin_two_notes_two_studied(self):
        self._standard_begin_test("two_notes_two_studied", expected_usn=2)

    ##
    ## test the `downloadFiles` methods
    ##
    def _standard_download_files_down_test(self, test_set, fname):
        rms = TestRemoteMediaServer()
        rms.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rms.meta()
        rms.begin()

        rs_method = rms.downloadFiles

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")
        # FIXME: there is probably a better way to do this!
        # copy asset to expected location for download
        path_to_download = os.path.join(settings.DJANKISERV_DATA_ROOT, SyncTestRemoteServer.USERNAME, fname)

        self.copy_asset_to_path(fname, path_to_download)

        before = self.load_db_to_dict()

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json")).content

        z = zipfile.ZipFile(io.BytesIO(output), "r")
        meta = json.loads(z.read("_meta").decode("utf8"))
        self.assertEqual(len(z.infolist()), 2)
        self.assertEqual(meta["0"], fname)
        self.assertEqual(z.read("0"), self.get_asset(fname))

        # no db change expected
        after = self.load_db_to_dict()
        self.assertFalse(self.db_diff(before, after))

    def test_downloadFiles_one_note_w_media(self):
        self._standard_download_files_down_test("one_note_w_media", "wo1.png")

    def test_downloadFiles_two_notes_one_added(self):
        self._standard_download_files_down_test("two_notes_one_added", "wo2.png")

    ##
    ## test the `mediaChanges` methods
    ##
    def _standard_media_changes_down_test(self, test_set, expected_changes):
        rms = TestRemoteMediaServer()
        rms.hostKey(SyncTestRemoteServer.USERNAME, SyncTestRemoteServer.PASSWORD)
        rms.meta()
        rms.begin()

        rs_method = rms.mediaChanges

        self.load_db_asset(SyncTestRemoteServer.USERNAME, f"{test_set}/pre_{rs_method.__name__}.sql")

        before = self.load_db_to_dict()

        output = rs_method(**self.load_json_asset(f"{test_set}/pre_{rs_method.__name__}.json"))["data"]
        self.assertEqual(output, expected_changes)

        # no db change expected
        after = self.load_db_to_dict()
        self.assertFalse(self.db_diff(before, after))

    def test_mediaChanges_one_note_delete_unused_media(self):
        self._standard_media_changes_down_test("one_note_delete_unused_media", [["wo2.png", 3, None]])

    def test_mediaChanges_one_note_w_media(self):
        self._standard_media_changes_down_test(
            "one_note_w_media", [["wo1.png", 1, "f18e0dc430b26c75e16315bd6367bdcc744ea2c8"]]
        )

    def test_mediaChanges_two_notes_one_added(self):
        self._standard_media_changes_down_test(
            "two_notes_one_added", [["wo2.png", 2, "f18e0dc430b26c75e16315bd6367bdcc744ea2c8"]]
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
