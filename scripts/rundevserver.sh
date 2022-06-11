#!/bin/bash

source scripts/runsetup.sh

export DJANKISERV_DEBUG=true
export DJANKISERV_ALLOWED_HOSTS='*'
[[ ! -z "${DJANKISERV_PORT}" ]] || DJANKISERV_PORT=5000

python3 -m djankiserv_cli runserver 0.0.0.0:${DJANKISERV_PORT}
