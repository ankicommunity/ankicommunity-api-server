#!/bin/bash
set -e

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests
export DJANKISERV_DATA_ROOT=/tmp/djankiserv_tests

pylint --ignore requirements.txt,djankiserv.egg-info src/*
pylint tests/*

# pre-commit also has flake8 linter
pre-commit run --all-files --verbose

# Test with the default db backend, postgresql
coverage run --source='src' src/manage.py test --verbosity=1 tests
coverage report -m --skip-covered --skip-empty --fail-under 82

# Test with the mariadb/mysql db backend
DJANKISERV_MAINDB_ENGINE=django.db.backends.mysql DJANKISERV_USERDB_ENGINE=django.db.backends.mysql python src/manage.py test --verbosity=1 tests
