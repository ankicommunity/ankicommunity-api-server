#!/usr/bin/env bash
# file: precommit-install.sh
# description: Install pre-commit Git hook.

[[ ! -z "${PRECOMMIT}" ]] || PRECOMMIT="poetry run pre-commit"
${PRECOMMIT} uninstall