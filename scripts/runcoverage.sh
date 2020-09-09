#!/bin/bash

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests

coverage run --source='src' src/manage.py test tests
