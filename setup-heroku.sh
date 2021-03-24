#!/usr/bin/env bash
# Script needed to configure the Heroku environment with `heroku.yml`.

# heroku.yml doesn't support submodules, apparently
echo ">> Cloning dependencies"
git init
./setup-submodules.sh
echo ">>>>>> /usr/src/app/gatovid"
ls /usr/src/app/gatovid
echo ">>>>>> /usr/src/app/gatovid/assets"
ls /usr/src/app/gatovid/assets
echo ">>>>>> done"
git submodule init
git submodule update

# Also gatovid-specific processes
echo ">> Setting up database"
python -m gatovid --reset-db
python -m gatovid --create-db
