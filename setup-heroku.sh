#!/usr/bin/env bash
# Script needed to configure the Heroku environment with `heroku.yml`.

# heroku.yml doesn't support submodules, apparently
echo ">> Cloning dependencies"
git init
./setup-submodules.sh
ls /usr/src/app/gatovid
ls /usr/src/app/gatovid/assets

# Also gatovid-specific processes
echo ">> Setting up database"
python -m gatovid --reset-db
python -m gatovid --create-db
