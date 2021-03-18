FROM python:3.8-slim

# Configuración del locale a español
ENV DEBIAN_FRONTEND noninteractive
COPY setlocale.sh ./
RUN ./setlocale.sh "es_ES.UTF-8 UTF-8"
ENV LANG es_ES
ENV LANGUAGE es_ES
ENV LC_ALL es_ES

RUN python -m pip install --upgrade pip

WORKDIR /usr/src/app

COPY README.md setup.py ./
RUN pip install .
