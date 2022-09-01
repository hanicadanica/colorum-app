#!/bin/sh

gunicorn --worker-class eventlet \
    --workers 1 \
    --bind 0.0.0.0:34568 \
    --max-requests 10000 \
    --timeout 60 \
    --keep-alive 5 \
    --log-level info \
    application:application
