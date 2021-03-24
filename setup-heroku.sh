#!/usr/bin/env bash
# Script needed to configure the Heroku environment with `heroku.yml`.

# heroku.yml doesn't support submodules, apparently
echo ">> Cloning dependencies"
echo ">>>>>> /usr/src/app/gatovid"
ls /usr/src/app/gatovid
echo ">>>>>> /usr/src/app/gatovid/assets"
ls /usr/src/app/gatovid/assets
echo ">>>>>> done"

# Also gatovid-specific processes
echo ">> Setting up database"
python -m gatovid --reset-db
python -m gatovid --create-db
