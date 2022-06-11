#!/usr/bin/env bash
# file: postgres-clean.sh
# description: Stop and remove local postgres database files.

docker-compose rm --stop postgres
trash instances/postgres_5432