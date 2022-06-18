#!/bin/bash
set -e

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests
export DJANKISERV_DATA_ROOT=./instances/djankiserv_tests

pylint --ignore requirements.txt,requirements.ci.txt,requirements.postgres.txt,requirements.mariadb.txt,djankiserv.egg-info src/*
pylint tests/*

pre-commit run --all-files --verbose