#!/usr/bin/env bash
# Script needed to configure the Heroku environment with `heroku.yml`.

# Gatovid-specific processes
echo ">> Setting up database"
python -m gatovid --reset-db
python -m gatovid --create-db
