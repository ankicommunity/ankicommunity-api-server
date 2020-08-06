# -*- coding: utf-8 -*-

import gzip
import io
import json
import re
import time
from abc import ABC, abstractmethod
from hashlib import sha1


def _decode_data(data, compression=0):
    if compression:
        with gzip.GzipFile(mode="rb", fileobj=io.BytesIO(data)) as gz:
            data = gz.read()
    try:
        data = json.loads(data.decode())
    except (ValueError, UnicodeDecodeError):
        data = {"data": data}

    return data


def get_data(request):
    try:
        compression = int(request.POST["c"])
    except KeyError:
        compression = 0

    try:
        data = _decode_data(request.FILES["data"].read(), compression)
        request.FILES["data"].seek(0)  # need to seek back to zero or it will appear empty after read()!
    except KeyError:
        data = {}
    return data


# from anki.utils
# FIXME: these have both been copied to multiple modules
def intTime(scale=1):
    "The time in integer seconds. Pass scale=1000 to get milliseconds."
    return int(time.time() * scale)


def ids2str(ids):
    """Given a list of integers, return a string '(int1,int2,...)'."""
    # This is "safe" for sql string concatenation due to casting to int before recasting to string,
    # meaning that python will raise an exception for anything but lists of numbers
    idstring = f"({','.join(str(int(i)) for i in ids)})"
    return idstring if len(idstring) > 2 else "(0)"


def splitFields(string):
    return string.split("\x1f")


def joinFields(field_list):
    return "\x1f".join(field_list)


def checksum(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return sha1(data).hexdigest()


# deck schema & syncing vars
REM_CARD = 0
REM_NOTE = 1
# REM_DECK = 2  # declared and used only in unki.decks


# HTML
##############################################################################
reComment = re.compile("(?s)<!--.*?-->")
reStyle = re.compile("(?si)<style.*?>.*?</style>")
reScript = re.compile("(?si)<script.*?>.*?</script>")
reTag = re.compile("(?s)<.*?>")
reEnts = re.compile(r"&#?\w+;")
reMedia = re.compile("(?i)<img[^>]+src=[\"']?([^\"'>]+)[\"']?[^>]*>")


def entsToTxt(html):
    # entitydefs defines nbsp as \xa0 instead of a standard space, so we
    # replace it first
    html = html.replace("&nbsp;", " ")

    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return chr(int(text[4:-1], 16))
                return chr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                # FIXME: name2codepoint doesn't exist anywhere!!!
                text = chr(name2codepoint[text[1:-1]])  # noqa: F821  # pylint: disable=E0602
            except KeyError:
                pass
        return text  # leave as is

    return reEnts.sub(fixup, html)


def stripHTML(s):
    s = reComment.sub("", s)
    s = reStyle.sub("", s)
    s = reScript.sub("", s)
    s = reTag.sub("", s)
    s = entsToTxt(s)
    return s


def stripHTMLMedia(s):
    "Strip HTML but keep media filenames"
    s = reMedia.sub(" \\1 ", s)
    return stripHTML(s)


def fieldChecksum(data):
    # 32 bit unsigned number from first 8 digits of sha1 hash
    return int(checksum(stripHTMLMedia(data).encode("utf-8"))[:8], 16)


AnkiDataModel = None  # This gets set as a module/global variable in the app init with the db connector (mysql or pgsql)


# This class is the source of truth for the Anki data model. It is used
# for various SQL generation purposes, such as creating schemas, query
# rewrites and getting all the tables for sqlite -> pg and pg -> sqlite
# import/export
class AnkiDataModelBase(ABC):
    VERSION = 11
    COLLECTION_PARENT_DB = "collection"
    MEDIA_PARENT_DB = "media"

    # is_pk gives a primary key constraint and an identity sequence, currently only supports single
    MODEL = {
        "notes": {
            "fields": [
                {"name": "id", "type": "bigint", "is_pk": True},
                {"name": "guid", "type": "text"},
                {"name": "mid", "type": "bigint"},
                {"name": "modified", "type": "bigint", "sqlite_name": "mod"},
                {"name": "usn", "type": "bigint"},
                {"name": "tags", "type": "text"},
                {"name": "flds", "type": "text"},
                {"name": "sfld", "type": "text"},  # WARNING! This is an `integer` in sqlite but contains text...
                # csum is actually an integer but must be text col because empty strings get inserted!
                # {"name": "csum", "type": "bigint", "nullable": True},
                {"name": "csum", "type": "text"},
                {"name": "flags", "type": "bigint"},
                {"name": "data", "type": "text"},
            ],
            "indexes": [
                {"name": "ix_notes_csum", "fields": [{"name": "csum", "type": "text"}]},
                {"name": "ix_notes_usn", "fields": [{"name": "usn", "type": "bigint"}]},
            ],
            "parent": COLLECTION_PARENT_DB,
        },
        "cards": {
            "fields": [
                {"name": "id", "type": "bigint", "is_pk": True},
                {"name": "nid", "type": "bigint"},
                {"name": "did", "type": "bigint"},
                {"name": "ord", "type": "bigint"},
                {"name": "modified", "type": "bigint", "sqlite_name": "mod"},
                {"name": "usn", "type": "bigint"},
                {"name": "type", "type": "bigint"},
                {"name": "queue", "type": "bigint"},
                {"name": "due", "type": "bigint"},
                {"name": "ivl", "type": "bigint"},
                {"name": "factor", "type": "bigint"},
                {"name": "reps", "type": "bigint"},
                {"name": "lapses", "type": "bigint"},
                {"name": "remaining", "type": "bigint", "sqlite_name": "left"},
                {"name": "odue", "type": "bigint"},
                {"name": "odid", "type": "bigint"},
                {"name": "flags", "type": "bigint"},
                {"name": "data", "type": "text"},
            ],
            "indexes": [
                {"name": "ix_cards_nid", "fields": [{"name": "nid", "type": "bigint"}]},
                {
                    "name": "ix_cards_sched",
                    "fields": [
                        {"name": "did", "type": "bigint"},
                        {"name": "queue", "type": "bigint"},
                        {"name": "due", "type": "bigint"},
                    ],
                },
                {"name": "ix_cards_usn", "fields": [{"name": "usn", "type": "bigint"}]},
            ],
            "parent": COLLECTION_PARENT_DB,
        },
        "col": {
            "fields": [
                {"name": "id", "type": "bigint", "is_pk": True},
                {"name": "crt", "type": "bigint"},
                {"name": "modified", "type": "bigint", "sqlite_name": "mod"},
                {"name": "scm", "type": "bigint"},
                {"name": "ver", "type": "bigint"},
                {"name": "dty", "type": "bigint"},
                {"name": "usn", "type": "bigint"},
                {"name": "ls", "type": "bigint"},
                {"name": "conf", "type": "text"},
                {"name": "models", "type": "text"},
                {"name": "decks", "type": "text"},
                {"name": "dconf", "type": "text"},
                {"name": "tags", "type": "text"},
            ],
            "indexes": [],
            "parent": COLLECTION_PARENT_DB,
            "initsql": (
                "insert into {schema_name}.col values " f"(1, 0, 0, 1, {VERSION}, 0, 0, 0, '', '{{}}', '', '', '{{}}');"
            ),
        },
        "graves": {
            "fields": [
                {"name": "usn", "type": "bigint"},
                {"name": "oid", "type": "bigint"},
                {"name": "type", "type": "bigint"},
            ],
            "indexes": [],
            "parent": COLLECTION_PARENT_DB,
        },
        "revlog": {
            "fields": [
                {"name": "id", "type": "bigint", "is_pk": True},
                {"name": "cid", "type": "bigint"},
                {"name": "usn", "type": "bigint"},
                {"name": "ease", "type": "bigint"},
                {"name": "ivl", "type": "bigint"},
                {"name": "lastivl", "type": "bigint"},
                {"name": "factor", "type": "bigint"},
                {"name": "rtime", "type": "bigint", "sqlite_name": "time"},
                {"name": "type", "type": "bigint"},
            ],
            "indexes": [
                {"name": "ix_revlog_cid", "fields": [{"name": "cid", "type": "bigint"}]},
                {"name": "ix_revlog_usn", "fields": [{"name": "usn", "type": "bigint"}]},
            ],
            "parent": COLLECTION_PARENT_DB,
        },
        "media": {
            "fields": [
                {"name": "fname", "type": "text", "is_pk": True},
                {"name": "usn", "type": "bigint"},
                {"name": "csum", "type": "text", "nullable": True},
            ],
            "indexes": [{"name": "ix_media_usn", "fields": [{"name": "usn", "type": "bigint"}]}],
            "parent": MEDIA_PARENT_DB,
        },
        "meta": {
            "fields": [{"name": "dirmod", "type": "bigint"}, {"name": "lastusn", "type": "bigint"}],
            "indexes": [],
            "parent": MEDIA_PARENT_DB,
            "initsql": "insert into {schema_name}.meta values (0, 0);",
        },
    }

    @staticmethod
    @abstractmethod
    def generate_schema_sql_list(schema_name):
        pass

    @staticmethod
    @abstractmethod
    def insert_on_conflict_update(schema_name, table_name):
        pass

    @staticmethod
    @abstractmethod
    def insert_on_conflict_nothing(schema_name, table_name):
        pass

    @staticmethod
    @abstractmethod
    def replace_schema(cur, to_replace_name, replace_with_name):
        pass
