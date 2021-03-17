# Gatovid

## Instalación

Posiblemente necesite `sudo`:

```sh
$ docker-compose build
$ docker-compose up -d
$ docker-compose run api /usr/local/bin/python -m gatovid --create-db
```

Para ver en qué dirección está corriendo el servidor (mirar el de `ngnix`):

```sh
$ docker-compose ps
```

Internamente usa Python 3.8, por lo que se puede usar todo lo del lenguaje hasta
dicha versión. Cualquier cambio al código se verá reflejado en tiempo real, no
hace falta volver a correr el setup inicial mas que una vez, o cuando se quiera
cambiar la base de datos o añadir alguna dependencia.

Para ver los logs de la aplicación (se puede añadir el flag `-f` para que sea en
tiempo real):

```sh
$ docker-compose logs
```

## Formatting

Requiere instalar algunos módulos, recomiendo usar un virtualenv si no lo
quieres instalar en tu sistema:

```sh
$ # Iniciar virtualenv, sólo la primera vez
$ python -m venv .venv
$ # Entrar al virtualenv
$ source .venv/bin/activate
$ # Instalar programas en el virtualenv, sólo la primera vez
$ pip install black isort flake8
$ # El script de formatting y etc
$ ./format.sh
$ # Salir del virtualenv
$ deactivate
```

Sino, manualmente con `./format.sh` o:

* Auto formatting con `python -m black .`
* Imports ordenados con `python -m isort .`
* Linter con `python -m flake8 .`

## Tests

Se pueden hacer peticiones simples de prueba con `curl`:

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
