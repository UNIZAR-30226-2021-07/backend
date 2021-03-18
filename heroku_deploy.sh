#!/usr/bin/env

echo ">> Creating database"
python -m gatovid --create-db

echo ">> Launching app"
gunicorn -w 1 -b :8000 gatovid.app:app
