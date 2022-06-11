#!/usr/bin/env bash
# file: postgres-init.sh
# description: Initalise postgres database.

${BASH} ./scripts/runmanage.sh migrate
${BASH} ./scripts/runmanage.sh createsuperuser