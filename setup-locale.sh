#!/bin/sh
# Cambia el locale al especificado para que los nombres provistos del servidor
# no estén en inglés. Debe ejecutarse con permisos de administrador.

# Instala el paquete de los repostorios
apt-get update -y
apt-get install -y locales
# Reconfigura el locale del sistema
sed -i -e "s/# $1/$1/" /etc/locale.gen
dpkg-reconfigure --frontend=noninteractive locales
