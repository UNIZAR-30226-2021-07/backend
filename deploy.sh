#!/bin/bash

# Paramos y borramos la versión anterior si existe
echo -e "\n--> Parando y borrando las versiones anteriores..."
docker-compose -f docker-compose.production.yml down -v 

echo -e "\n--> Construyendo y lanzando las imágenes"
# Construimos la imagen y descargamos las dependencias
docker-compose -f docker-compose.production.yml build
# Lanzamos la imagen en segundo plano
docker-compose -f docker-compose.production.yml up -d

echo -e "\n--> Generando los datos aleatorios para la base de datos..."
# Generamos los datos para la base de datos
docker-compose -f docker-compose.production.yml run web /usr/local/bin/python -m gatovid --create-db

echo -e "\n--> Aplicación desplegada, puede acceder a ella en http://localhost:80"
