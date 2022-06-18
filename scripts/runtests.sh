#!/bin/bash
set -e

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests
export DJANKISERV_DATA_ROOT=./instances/djankiserv_tests

coverage run --source='src' src/djankiserv_cli/manage.py test --verbosity=1 tests/