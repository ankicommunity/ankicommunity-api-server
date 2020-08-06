# -*- coding: utf-8 -*-

import json
import logging
import os
import pathlib
import pickle
import subprocess

from django.conf import settings
from django.db import connections
from django.http import HttpResponse

import djankiserv.unki
from djankiserv.assets import jsonfiles  # noqa: 401  # pylint: disable=W0611

from . import AnkiDataModelBase, get_data

MODEL_STD = 0
NEW_CARDS_DUE = 1

logger = logging.getLogger("djankiserv.unki.database")


def db_conn():
    return connections["userdata"]


class StandardDB:
    def __init__(self):  # pylint: disable=W0231
        self._db = db_conn()
        self.mod = False

    @staticmethod
    def schema_exists(schema_name):
        with db_conn().cursor() as cur:
            cur.execute("SELECT 1 FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = %s", (schema_name,))
            res = cur.fetchone()
        return res[0] if res else 0

    @staticmethod
    def create_schema(schema_name):
        assert schema_name.isidentifier()
        with db_conn().cursor() as cur:
            for sql in djankiserv.unki.AnkiDataModel.generate_schema_sql_list(schema_name):
                if not sql.strip():
                    continue
                # print("executing", sql)
                cur.execute(sql)
            res = cur.fetchone()
            return res[0]  # returns an Ok message
        # db_conn().commit()

    @staticmethod
    def delete_schema(schema_name):
        with db_conn().cursor() as cur:
            cur.execute(djankiserv.unki.AnkiDataModel.DROP_SCHEMA.replace("{schema_name}", schema_name))

    def execute(self, sql, *a, **ka):
        s = sql.strip().lower()
        # mark modified?
        for stmt in "insert", "update", "delete":
            if s.startswith(stmt):
                self.mod = True
        cur = self._db.cursor()
        if ka:
            cur.execute(sql, ka)
        else:
            cur.execute(sql, a)
        return cur

    def executemany(self, sql, li):
        self.mod = True
        cur = self._db.cursor()
        cur.executemany(sql, li)
        return cur

    def commit(self):
        pass
        # self._db.commit()

    def scalar(self, *a):
        res = self.execute(*a).fetchone()  # pylint: disable=E1120  # FIXME: how should I get rid of this disable?
        if res:
            return res[0]
        return None

    def first(self, *a):
        c = self.execute(*a)
        res = c.fetchone()
        c.close()
        return res

    def list(self, *a):
        return [x[0] for x in self.execute(*a)]  # pylint: disable=E1120  # FIXME: how should I get rid of this disable?

    def close(self):
        # FIXME: is this Ok?
        pass
        # self._db.commit()
        # self._db.close()


# for getting dumps of the DB to compare for unittests
def dump_io_to_file(session, method, io_obj, is_media=False):  # noqa: C901  # pylint: disable=R0914
    if not settings.DJANKISERV_GENERATE_TEST_ASSETS:  # we need this only for getting new test files
        return
    schema_name = session["name"]
    fname_dir = session["dump_base"] if not is_media else session["dump_base_media"]
    pathlib.Path(fname_dir).mkdir(parents=True, exist_ok=True)

    if isinstance(io_obj, HttpResponse):
        fname_base = os.path.join(fname_dir, "post_" + method)
        to_print = f"Response Content:\n{io_obj.content}\n"
        try:
            io_obj_json = json.loads(io_obj.content)
        except (json.decoder.JSONDecodeError, UnicodeDecodeError):
            io_obj_json = {"to_return": io_obj.content}  # this will get pickled below
    else:
        fname_base = os.path.join(fname_dir, "pre_" + method)
        to_print = f"POST:\n{io_obj.POST}\n\n"
        to_print += f"DATA:\n{get_data(io_obj)}\n"
        io_obj_json = get_data(io_obj)

    if os.path.exists(fname_base + ".txt"):
        i = 1
        while os.path.exists(f"{fname_base}.{i}.txt"):
            i += 1
        fname_base = f"{fname_base}.{i}"

    with open(fname_base + ".txt", "w") as fh:
        fh.write(to_print)

    proc_res = subprocess.run(
        ["pg_dump", connections["userdata"].settings_dict["NAME"], "--schema", schema_name, "--column-inserts"],
        capture_output=True,
        text=True,
        check=True,
    )

    with open(fname_base + ".sql", "w") as fh:
        fh.write(proc_res.stdout)

    try:
        with open(fname_base + ".json", "w") as fh:
            json.dump(io_obj_json, fh, indent=4, sort_keys=True)
    except TypeError:
        # there is binary data in the json, so pickle instead
        with open(fname_base + ".bin", "wb") as fh:
            pickle.dump(io_obj_json, fh)
        try:  # to remove the broken .json file that was created
            os.remove(fname_base + ".json")
        except OSError:
            pass

    with open(fname_base + "_col.json", "w") as fh, db_conn().cursor() as cur:
        cur.execute(f"select conf, models, decks, dconf, tags from {schema_name}.col")
        row = cur.fetchall()
        if len(row) > 1:
            raise Exception("There should only ever be one collection, right?")
        conf = json.loads(row[0][0])
        models = json.loads(row[0][1])
        decks = json.loads(row[0][2])
        dconf = json.loads(row[0][3])
        tags = json.loads(row[0][4])
        fh.write(
            json.dumps(
                {"conf": conf, "models": models, "decks": decks, "dconf": dconf, "tags": tags},
                sort_keys=True,
                indent=4,
            )
        )


class PostgresAnkiDataModel(AnkiDataModelBase):
    MODEL_SETUP = """
        SET statement_timeout = 0;
        SET lock_timeout = 0;
        SET idle_in_transaction_session_timeout = 0;
        SET client_encoding = 'UTF8';
        SET standard_conforming_strings = on;
        SELECT pg_catalog.set_config('search_path', '', false);
        SET check_function_bodies = false;
        SET client_min_messages = warning;
        SET row_security = off;

        SET default_tablespace = '';

        SET default_with_oids = false;"""

    MODEL_SETUP_LIST = MODEL_SETUP.split(";")
    CREATE_SCHEMA = "CREATE SCHEMA {schema_name};"
    DROP_SCHEMA = "DROP SCHEMA IF EXISTS {schema_name} CASCADE;"

    @staticmethod
    def generate_schema_sql_list(schema_name):
        sql = []
        sql += PostgresAnkiDataModel.MODEL_SETUP_LIST
        sql.append(PostgresAnkiDataModel.CREATE_SCHEMA.format(schema_name=schema_name))

        for table_name, defin in AnkiDataModelBase.MODEL.items():
            tsql = (
                f"CREATE TABLE {schema_name}.{table_name} ("
                + ",".join(
                    [f"{f['name']} {f['type']} {'' if f.get('nullable') else 'NOT'} NULL" for f in defin["fields"]]
                )
                + ");"
            )
            sql.append(tsql)
            identity = [x["name"] for x in defin["fields"] if "is_pk" in x and x["type"] == "bigint"]
            if identity:
                tsql = f"""
                ALTER TABLE {schema_name}.{table_name}
                    ALTER COLUMN {identity[0]} ADD GENERATED BY DEFAULT AS IDENTITY (
                        SEQUENCE NAME {schema_name}.{table_name}_{identity[0]}_seq
                        START WITH 1
                        INCREMENT BY 1
                        NO MINVALUE
                        NO MAXVALUE
                        CACHE 1
                    );"""

                sql.append(tsql)

            pk = [x["name"] for x in defin["fields"] if "is_pk" in x]
            if pk:
                tsql = f"""
                ALTER TABLE ONLY {schema_name}.{table_name}
                    ADD CONSTRAINT {table_name}_pkey PRIMARY KEY ({pk[0]});"""
                sql.append(tsql)

            for i in defin["indexes"]:
                tsql = (
                    f"CREATE INDEX {i['name']} ON {schema_name}.{table_name} ("  # defaults to btree for postgresql
                    + ",".join([x["name"] for x in i["fields"]])
                    + ");"
                )
                sql.append(tsql)

            if "initsql" in defin:
                tsql = defin["initsql"].replace("{schema_name}", schema_name)  # dynamic replace rather than fstring
                sql.append(tsql)

        sql.append(f"SELECT {AnkiDataModelBase.VERSION};")

        return sql

    @staticmethod
    def insert_on_conflict_update(schema_name, table_name):
        identity = [x["name"] for x in AnkiDataModelBase.MODEL[table_name]["fields"] if "is_pk" in x]
        fstr = ", ".join(["%s"] * len(AnkiDataModelBase.MODEL[table_name]["fields"]))

        return (
            f"INSERT INTO {schema_name}.{table_name} ("
            + ",".join([f"{f['name']}" for f in AnkiDataModelBase.MODEL[table_name]["fields"]])
            + f") VALUES ({fstr}) "
            + f"ON CONFLICT ({identity[0]}) DO UPDATE SET "
            + ",".join(
                [
                    f"{f['name']} = EXCLUDED.{f['name']}"
                    for f in AnkiDataModelBase.MODEL[table_name]["fields"]
                    if "is_pk" not in f
                ]
            )
        )

    @staticmethod
    def insert_on_conflict_nothing(schema_name, table_name):
        identity = [x["name"] for x in AnkiDataModelBase.MODEL[table_name]["fields"] if "is_pk" in x]
        fstr = ", ".join(["%s"] * len(AnkiDataModelBase.MODEL[table_name]["fields"]))

        return (
            f"INSERT INTO {schema_name}.{table_name} ("
            + ",".join([f"{f['name']}" for f in AnkiDataModelBase.MODEL[table_name]["fields"]])
            + f") VALUES ({fstr}) "
            + f"ON CONFLICT ({identity[0]}) DO NOTHING "
        )

    @staticmethod
    def replace_schema(cur, to_replace_name, replace_with_name):
        # rename the existing schema, rename the new schema to the username, delete the old schema
        cur.execute(f"ALTER SCHEMA {to_replace_name} RENAME TO {to_replace_name}_old")
        cur.execute(f"ALTER SCHEMA {replace_with_name} RENAME TO {to_replace_name}")
        cur.execute(f"DROP SCHEMA {to_replace_name}_old CASCADE")


class MariadbAnkiDataModel(AnkiDataModelBase):

    MODEL_SETUP = ""
    MODEL_SETUP_LIST = []

    CREATE_SCHEMA = "CREATE DATABASE {schema_name} CHARACTER SET utf8;"
    DROP_SCHEMA = "DROP DATABASE IF EXISTS {schema_name};"

    @staticmethod
    def generate_schema_sql_list(schema_name):
        sql = []
        sql += MariadbAnkiDataModel.MODEL_SETUP_LIST
        sql.append(MariadbAnkiDataModel.CREATE_SCHEMA.format(schema_name=schema_name))

        for table_name, defin in AnkiDataModelBase.MODEL.items():
            tsql = (
                f"CREATE TABLE {schema_name}.{table_name} ("
                + ",".join(
                    [f"{f['name']} {f['type']} {'' if f.get('nullable') else 'NOT'} NULL" for f in defin["fields"]]
                )
                + ");"
            )
            sql.append(tsql)
            identity = [x["name"] for x in defin["fields"] if "is_pk" in x and x["type"] == "bigint"]
            if identity:
                tsql = (
                    f"""ALTER TABLE {schema_name}.{table_name} MODIFY """
                    f"""{identity[0]} BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY"""
                )

                sql.append(tsql)
            else:
                pk = [x for x in defin["fields"] if "is_pk" in x]
                if pk:
                    pk_colspec = pk[0]["name"] + "(255)" if pk[0]["type"] == "text" else ""
                    tsql = f"""
                    ALTER TABLE {schema_name}.{table_name}
                        ADD CONSTRAINT {table_name}_pkey PRIMARY KEY ({pk_colspec});"""
                    sql.append(tsql)

            for i in defin["indexes"]:
                tsql = (
                    f"CREATE INDEX {i['name']} ON {schema_name}.{table_name} ("  # defaults to btree for postgresql
                    + ",".join([x["name"] + ("(255)" if x["type"] == "text" else "") for x in i["fields"]])
                    + ");"
                )
                sql.append(tsql)

            if "initsql" in defin:
                tsql = defin["initsql"].replace("{schema_name}", schema_name)  # dynamic replace rather than fstring
                sql.append(tsql)

            # sql += tsql
        sql.append(f"SELECT {AnkiDataModelBase.VERSION};")

        return sql

    @staticmethod
    def insert_on_conflict_update(schema_name, table_name):

        fstr = ", ".join(["%s"] * len(MariadbAnkiDataModel.MODEL[table_name]["fields"]))

        return (
            f"INSERT INTO {schema_name}.{table_name} ("
            + ",".join([f"{f['name']}" for f in MariadbAnkiDataModel.MODEL[table_name]["fields"]])
            + f") VALUES ({fstr}) "
            + "ON DUPLICATE KEY UPDATE "
            + ",".join(
                [
                    f"{f['name']} = VALUES({f['name']})"
                    for f in MariadbAnkiDataModel.MODEL[table_name]["fields"]
                    if "is_pk" not in f
                ]
            )
        )

    @staticmethod
    def insert_on_conflict_nothing(schema_name, table_name):

        identity = [x["name"] for x in MariadbAnkiDataModel.MODEL[table_name]["fields"] if "is_pk" in x]
        fstr = ", ".join(["%s"] * len(MariadbAnkiDataModel.MODEL[table_name]["fields"]))

        return (
            f"INSERT INTO {schema_name}.{table_name} ("
            + ",".join([f"{f['name']}" for f in MariadbAnkiDataModel.MODEL[table_name]["fields"]])
            + f") VALUES ({fstr}) "
            + f"ON DUPLICATE KEY UPDATE {identity[0]} = {identity[0]}"
        )

    @staticmethod
    def replace_schema(cur, to_replace_name, replace_with_name):
        # rename the existing schema, rename the new schema to the username, delete the old schema

        sql = f"""
            SELECT CONCAT('RENAME TABLE ',
                table_schema, '.', table_name, ' TO ', '{to_replace_name}.', table_name, ';') as commands
            FROM information_schema.TABLES
            WHERE table_schema = '{replace_with_name}';
            """
        cur.execute(sql)
        copy_commands = cur.fetchall()

        sql = f"DROP DATABASE {to_replace_name}; CREATE DATABASE {to_replace_name} CHARACTER SET utf8;"
        cur.execute(sql)

        for com in copy_commands:
            cur.execute(com[0])

        sql = f"DROP DATABASE {replace_with_name};"
        cur.execute(sql)
