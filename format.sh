#!/bin/sh
# Fichero de formato automático del código y linter.

set -e

echo ">> Formatting"
python -m black .
echo ">> Sorting imports"
python -m isort .
echo ">> Running linter"
python -m flake8 . --ignore E402
