#!/bin/bash

source scripts/runsetup.sh

export DJANKISERV_DEBUG=true
export DJANKISERV_ALLOWED_HOSTS='*'

python3 -m djankiserv_cli runserver 0.0.0.0:8002
