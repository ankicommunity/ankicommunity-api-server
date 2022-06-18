#!/bin/bash

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests

coverage run --source='src' src/djankiserv_cli/manage.py test tests/
