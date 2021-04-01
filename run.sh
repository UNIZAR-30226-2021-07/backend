#!/bin/sh
# Command ran for docker-compose and deployment

extra_flags=""
if [ "$DEBUG" = "True" ]; then
    extra_flags="--reload"
fi

/usr/local/bin/gunicorn --worker-class eventlet -w 1 -b :$PORT 'gatovid.app:app' $extra_flags
