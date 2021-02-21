#!/bin/bash
set -e

source scripts/runsetup.sh

TAG=${DJANKISERV_BUILD_TAG:-$(git describe --tags)}

MAIN_IMAGE=${DJANKISERV_DOCKER_REPO}/djankiserv:$TAG
buildah bud -t ${MAIN_IMAGE} -f images/main/Dockerfile .
buildah push -D ${MAIN_IMAGE}

STATIC_IMAGE=${DJANKISERV_DOCKER_REPO}/djankiserv-static:$TAG
python3 src/manage.py collectstatic --noinput
buildah bud -t ${STATIC_IMAGE} -f images/static/Dockerfile .
buildah push -D ${STATIC_IMAGE}
