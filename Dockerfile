FROM python:3.8-slim

WORKDIR /usr/src/app

# Configuración del locale a español
ENV DEBIAN_FRONTEND noninteractive
COPY setup-locale.sh ./
RUN ./setup-locale.sh "es_ES.UTF-8 UTF-8"
ENV LANG es_ES
ENV LANGUAGE es_ES
ENV LC_ALL es_ES

# External dependencies installation
RUN apt-get -y update
RUN apt-get -y install git curl

# Python dependencies installation
RUN python -m pip install --upgrade pip
COPY . .
RUN pip install .
