#!/bin/bash

DEFAULT_BIND=unix:/sockets/web.socket
ACTUAL_BIND=${GUNICORN_BIND:-$DEFAULT_BIND}

mkdir /sockets -p

# TODO: create DB (if necessary), make migrations, apply migrations

gunicorn --log-conf /web/log.conf --capture-output --workers 1 --reload --bind $ACTUAL_BIND app:app --timeout 300