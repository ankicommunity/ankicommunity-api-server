#!/bin/bash

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests

coverage report -m --skip-covered --skip-empty --fail-under 80

