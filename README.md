# Guía de inicio a Gatovid

## Instalación

Posiblemente necesite `sudo`. Para más información sobre las variables de
entorno a configurar, consultar la sección de [Despliegue](#despliegue). Por
defecto se desplegará en http://localhost/.

```sh
$ # Construcción y despliegue de la aplicación
$ docker-compose build
$ docker-compose up -d
$ # Limpia y crea la base de datos desde cero
$ docker-compose run api /usr/local/bin/python -m gatovid --reset-db
$ # Inicializa la base de datos con algunos valores de prueba
$ docker-compose run api /usr/local/bin/python -m gatovid --create-db
```

Internamente usa Python 3.8, por lo que se puede usar todo lo del lenguaje hasta
dicha versión. Cualquier cambio al código se verá reflejado en tiempo real, no
hace falta volver a correr el setup inicial mas que una vez, o cuando se quiera
cambiar la base de datos o añadir alguna dependencia.

Para ver los logs de la aplicación usar `docker-compose logs`. Se puede añadir
el flag `-f` para que sea en tiempo real, y se le puede indicar el servicio
específico del que mostrar información.

## Formatting

Requiere instalar algunos módulos de Python, por lo que es recomendado usar un
virtualenv si no lo quieres instalar en tu sistema:

```sh
$ # Iniciar virtualenv, sólo la primera vez
$ python -m venv .venv
$ # Entrar al virtualenv
$ source .venv/bin/activate
$ # Instalar programas en el virtualenv, sólo la primera vez
$ pip install -e '.[format]'
$ # El script de formatting y etc
$ ./format.sh
$ # Salir del virtualenv
$ deactivate
```

Se automatiza el proceso en `./format.sh`. Referirse a ese script para más
información.

## Tests

Se pueden hacer peticiones simples de prueba con `curl`, tanto en local como al
servidor desplegado:

```sh
$ # Petición GET con parámetros
$ curl "localhost/data/test?var=3"
$ # Petición POST con parámetros
$ curl -X POST "localhost/data/test" -d 'var=val'
```

Y para los tests automáticos:

```sh
$ docker-compose run api /usr/local/bin/python -m unittest
```

## Documentación

Se tiene un setup sencillo de documentación con
[Sphinx](https://www.sphinx-doc.org/en/master/usage/quickstart.html), que es la
herramienta más usada para ello en Python. Se pretende mantenerlo sencillo
porque su único uso es para el desarrollo de los clientes en el equipo, y no es
necesario un formato demasiado complejo.

Para construir la documentación se pueden seguir los siguientes pasos:

```
$ pip install -e '.[docs]'
$ cd docs
$ make html
```

Se incluirán todas las páginas autogeneradas en el directorio `build/html`.
También se puede generar LaTeX con `make latex`.

La documentación está configurada desde [Read The
Docs](https://readthedocs.org/) para que se genere en cada commit a master de
forma automática.

## Despliegue

Se incluyen archivos de configuración para el deployment en
[Heroku](https://www.heroku.com/). Los pasos seguidos son los siguientes:

1. Añadir un addon como [Heroku Postgres](https://www.heroku.com/postgres) con
   una base de datos de tipo postgres. Asegurarse de que exporte la variable
   `DATABASE_URL` (la mayoría lo hacen por defecto, y estará en el apartado de
   "Secrets").
2. Adicionalmente, se tendrán que incluir los siguientes secretos:
    * `SECRET_KEY` para encriptar con Flask. Usar una cadena larga con
      caracteres de todos los tipos.

El proyecto actualmente reside en https://gatovid.herokuapp.com/. Se ha
configurado con Continuous Deployment para que cada commit a la rama `master`
suba una actualización, después de que se hayan pasado todos los tests
correctamente.

Para realizar pruebas localmente se recomienda usar el fichero .env [de ejemplo
incluido en este
repositorio](https://github.com/UNIZAR-30226-2021-07/backend/blob/master/.env.example).
Únicamente es necesario cambiarle el nombre a `.env` y seguir los pasos de
`docker-compose` en la sección de [instalación](#instalación).
