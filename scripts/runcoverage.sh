#!/bin/bash

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests

coverage run --source='src,tests' src/manage.py test tests/
