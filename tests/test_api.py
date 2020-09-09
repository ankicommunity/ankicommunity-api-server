# -*- coding: utf-8 -*-

import base64
import json
import time

from django.urls import reverse
from rest_framework import status

from . import TestRemoteServer


class ApiTest(TestRemoteServer):
    # override TestRemoteServer
    def assets_package(self):
        return "assets.api"

    def test_basic_authentication(self):
        # basic, session and token should all work, non authenticated or incorrectly authenticated should all fail

        url = reverse("notes")
        data = None
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(
            HTTP_AUTHORIZATION=b"Basic " + base64.b64encode(f"{super().USERNAME}:{super().PASSWORD}".encode())
        )

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_jwt_authentication(self):
        url = reverse("notes")
        data = None
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + "abc")
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        token_url = reverse("token_obtain_pair")
        data = {"username": super().USERNAME, "password": super().PASSWORD}
        response = self.client.post(token_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue("access" in response.data)
        token = response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + token)
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_session_authentication(self):
        url = reverse("notes")
        data = None
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.client.login(username="unknown_user", password="unknown_password")

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.login(username=super().USERNAME, password=super().PASSWORD)
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_notes(self):
        url = reverse("notes")
        data = None
        self._standard_pretest(url)

        response = self.client.post(url, data, format="json")
        returned = json.loads(response.content.decode("utf8"))
        reference = self.load_json_asset("two_notes.json")

        self.assertEqual(returned, reference)

        data = {"ids": [reference["notes"][0]["id"]]}
        response = self.client.post(url, data, format="json")
        returned = json.loads(response.content.decode("utf8"))
        self.assertEqual(len(returned["notes"]), 1)
        self.assertEqual(reference["notes"][0], returned["notes"][0])

        data = {"ids": [reference["notes"][1]["id"]]}
        response = self.client.post(url, data, format="json")
        returned = json.loads(response.content.decode("utf8"))
        self.assertEqual(len(returned["notes"]), 1)
        self.assertEqual(reference["notes"][1], returned["notes"][0])

        data = {"ids": [1]}  # non-existant id
        response = self.client.post(url, data, format="json")
        returned = json.loads(response.content.decode("utf8"))

        self.assertEqual(len(returned["notes"]), 0)

    def _standard_pretest(self, url, data=None):
        self.client.credentials()
        self.client.logout()
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self.load_db_asset(super().USERNAME, "one_note_reviewed_one_deleted_sql.sql")
        self.client.login(username=super().USERNAME, password=super().PASSWORD)

    def test_decks(self):
        url = reverse("decks")
        data = None
        self._standard_pretest(url)

        response = self.client.post(url, data, format="json")

        returned = json.loads(response.content.decode("utf8"))
        reference = self.load_json_asset("decks.json")

        before = self.load_db_to_dict()

        today = int((time.time() - before["col"][0][1]) // 86400)
        for k in ["lrnToday", "newToday", "revToday", "timeToday"]:
            reference["decks"]["1"][k] = [today, 0]

        self.assertEqual(returned, reference)

    def test_decks_conf(self):
        url = reverse("decks_conf")
        data = None

        self._standard_pretest(url)
        response = self.client.post(url, data, format="json")

        returned = json.loads(response.content.decode("utf8"))
        reference = self.load_json_asset("decks_conf.json")

        self.assertEqual(returned, reference)

    def test_tags(self):
        url = reverse("tags")
        data = None

        self._standard_pretest(url)
        response = self.client.post(url, data, format="json")

        returned = json.loads(response.content.decode("utf8"))
        reference = self.load_json_asset("tags.json")

        self.assertEqual(returned, reference)

    def test_models(self):
        url = reverse("models")
        data = None

        self._standard_pretest(url)
        response = self.client.post(url, data, format="json")
        returned = json.loads(response.content.decode("utf8"))

        reference = self.load_json_asset("models.json")
        self.assertEqual(returned, reference)

    def test_delete_notes(self):

        data = None
        self._standard_pretest(reverse("delete_notes"))

        response = self.client.post(reverse("notes"), data, format="json")
        returned = json.loads(response.content.decode("utf8"))
        reference = self.load_json_asset("two_notes.json")

        self.assertEqual(returned, reference)

        # delete all notes
        data = None
        response = self.client.post(reverse("delete_notes"), data, format="json")
        returned = json.loads(response.content.decode("utf8"))
        self.assertEqual(returned, {"status": "ok"})

        response = self.client.post(reverse("notes"), data, format="json")
        returned = json.loads(response.content.decode("utf8"))

        self.assertEqual(len(returned["notes"]), 0)

        # reset database
        self._standard_pretest(reverse("delete_notes"))

        data = {"ids": [reference["notes"][0]["id"]]}
        response = self.client.post(reverse("delete_notes"), data, format="json")
        returned = json.loads(response.content.decode("utf8"))
        self.assertEqual(returned, {"status": "ok"})

        # check we still have the other one and only the other one
        data = None
        response = self.client.post(reverse("notes"), data, format="json")
        returned = json.loads(response.content.decode("utf8"))
        self.assertEqual(len(returned["notes"]), 1)
        self.assertEqual(returned["notes"][0], reference["notes"][1])

    def test_add_notes(self):
        self.client.login(username=super().USERNAME, password=super().PASSWORD)
        data = self.load_json_asset("new_notes.json")
        ref_data = data

        response = self.client.post(reverse("add_notes"), data, format="json")
        returned = json.loads(response.content.decode("utf8"))
        self.assertEqual(len(returned["note_ids"]), 2)

        created_ids = returned["note_ids"]

        data = None
        response = self.client.post(reverse("notes"), data, format="json")
        returned = json.loads(response.content.decode("utf8"))
        self.assertEqual(len(returned["notes"]), 2)
        self.assertEqual(sorted(created_ids), sorted([x["id"] for x in returned["notes"]]))

        del ref_data["deck"]
        for note in returned["notes"]:
            del note["id"]
        self.assertEqual(ref_data, returned)
