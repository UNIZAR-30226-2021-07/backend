#!/usr/bin/env

echo ---
pwd
echo ---
ls /usr/src/app
echo ---

echo ">> Creating database"
python -m gatovid --create-db

echo ">> Launching app"
gunicorn -w 1 -b :8000 gatovid.app:app
