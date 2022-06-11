#!/bin/bash

source scripts/runsetup.sh


[[ ! -z "${DJANGO_MANAGE}" ]] || DJANGO_MANAGE="${PYTHON} src/manage.py"
# [[ ! -z "${DJANGO_MANAGE_OPTS}" ]] || DJANGO_MANAGE_OPTS=
[[ ! -z "${DJANGO_MANAGE_CMD}" ]] || DJANGO_MANAGE_CMD=$@
# [[ ! -z "${DJANGO_MANAGE_ARGS}" ]] || DJANGO_MANAGE_CMD=$@

${DJANGO_MANAGE} ${DJANGO_MANAGE_CMD}
