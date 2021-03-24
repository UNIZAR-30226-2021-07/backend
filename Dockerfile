FROM python:3.8-slim

WORKDIR /usr/src/app

# Custom locale configuration
ENV DEBIAN_FRONTEND noninteractive
COPY setup-locale.sh ./
RUN ./setup-locale.sh "es_ES.UTF-8 UTF-8"
ENV LANG es_ES
ENV LANGUAGE es_ES
ENV LC_ALL es_ES

COPY . .

# External dependencies installation
RUN apt-get -y update
RUN apt-get -y install git curl

# External dependencies
RUN ./setup-submodules.sh

# Python dependencies installation
RUN python -m pip install --upgrade pip
RUN pip install .
