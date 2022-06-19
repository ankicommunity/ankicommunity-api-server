#!/bin/bash

source scripts/runsetup.sh
export PYTHONPATH=$PYTHONPATH:tests

[[ ! -z "${COVERAGE_FAIL_UNDER}" ]] || COVERAGE_FAIL_UNDER=80

coverage report -m --skip-covered --skip-empty --fail-under ${COVERAGE_FAIL_UNDER}

