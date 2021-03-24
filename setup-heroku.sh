#!/usr/bin/env bash
# Script needed to configure the Heroku environment with `heroku.yml`.

echo ">> TEST"
ls /usr/src/app/gatovid
ls /usr/src/app/gatovid/assets
git status
ls -a
pwd

# heroku.yml doesn't support submodules, apparently
echo ">> Cloning dependencies"
git init
git submodule init
git submodule update
ls /usr/src/app/gatovid
ls /usr/src/app/gatovid/assets

# Also gatovid-specific processes
echo ">> Setting up database"
python -m gatovid --create-db
