#!/bin/bash
set -e

source scripts/runsetup.sh

cd addon/

zip -r ../djankiserv.ankiaddon *
