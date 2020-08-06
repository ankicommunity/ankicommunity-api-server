#!/bin/bash
set -e

source scripts/runsetup.sh

MAIN_IMAGE=${DJANKISERV_DOCKER_REPO}/djankiserv:$(git describe --tags)
docker build -f images/main/Dockerfile . -t ${MAIN_IMAGE}
docker push ${MAIN_IMAGE}

STATIC_IMAGE=${DJANKISERV_DOCKER_REPO}/djankiserv-static:$(git describe --tags)
python src/manage.py collectstatic --noinput
docker build -f images/static/Dockerfile . -t ${STATIC_IMAGE}
docker push ${STATIC_IMAGE}
