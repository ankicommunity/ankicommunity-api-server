#!/usr/bin/env bash
# file: postgres.sh
# description:

[[ -f docker-compose.yml ]] || cp docker-compose.example.yml docker-compose.yml

docker-compose up -d postgres