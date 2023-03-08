#!/bin/bash

DEFAULT_BIND=unix:/sockets/web.socket
ACTUAL_BIND=${GUNICORN_BIND:-$DEFAULT_BIND}

mkdir /sockets -p
gunicorn --log-file out.log --log-level debug --error-logfile=- --workers 1 --reload --bind $ACTUAL_BIND app:app --timeout 300