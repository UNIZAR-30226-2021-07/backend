"""
API de Juegos
=============

Módulo con el API de websockets para la comunicación en tiempo real con los
clientes, como el juego mismo o el chat de la partida.

Funcionamiento del juego
########################

En esta sección se incluyen diagramas sobre la comunicación entre el cliente y
el servidor de forma más visual que textualmente. Para más detalles sobre los
mensajes consultar la :ref:`reference`.

Creación de Partidas Privadas
*****************************

Las partidas privadas son las más simples porque su inicio se realiza de forma
manual con el líder.

.. uml::
    :align: center

    @startuml
    hide footbox

    actor Usuario
    actor Líder
    participant Frontend
    participant Backend

    Líder -> Frontend: Crear Partida
    Frontend -> Backend: create_game
    Frontend <-- Backend: create_game("A18X")

    loop hasta que N >= 2
        Usuario -> Frontend: Unirse a Partida
        Frontend -> Backend: join("A18X")
        Frontend <-- Backend: users_waiting(N)
    end

    Líder -> Frontend: Iniciar partida
    Frontend -> Backend: start_game
    Frontend <-- Backend: start_game

    @enduml

Creación de Partidas Públicas
*****************************

Las partidas públicas se administran de forma automática, por lo que el flujo es
algo maś complejo. Se creará una partida para los jugadores que estén buscando
una (con un timer que limite el tiempo de espera), y posteriormente tendrán que
confirmar que se quieren unir.

.. uml::
    :align: center

    @startuml
    hide footbox

    actor Usuario
    participant Frontend
    participant Backend

    loop
        Usuario -> Frontend: Buscar Partida
        Frontend -> Backend: create_game
        Frontend <-- Backend: create_game("A18X")

        opt no había nadie buscando partida
            Frontend -> Frontend: start_timer(TIME_UNTIL_START)
        end

        opt timer termina y hay 2 usuarios buscando partida
            break
        end
    end

    Frontend <-- Backend: found_game("8XA1")
    Frontend -> Frontend: start_timer(TIME_UNTIL_START)

    loop hasta que el timer termine o todos los usuarios se hayan unido
        Usuario -> Frontend: Entrar en Partida encontrada
        Frontend -> Backend: join("8XA1")
        Frontend --> Backend: start_game
    end

    alt hay >=2 usuarios
        Frontend <-- Backend: start_game
    else hay <2 usuarios
        Frontend <-- Backend: game_cancelled
    end

    @enduml

Partida
*******

.. uml::
    :align: center

    @startuml
    hide footbox

    actor Usuario
    participant Frontend
    participant Backend

    loop hasta que acabe la partida
        alt descarte
            Usuario -> Frontend: Descartar
            Frontend -> Backend: play_discard
            Frontend <-- Backend: TODO
        else jugar carta
            Usuario -> Frontend: Jugar Carta
            Frontend -> Backend: play_card
            Frontend <-- Backend: TODO
        else pasar
            Usuario -> Frontend: Pasar
            Frontend -> Backend: play_pass
            Frontend <-- Backend: TODO
        else robar
            Usuario -> Frontend: Robar
            Frontend -> Backend: play_draw
            Frontend <-- Backend: TODO
        end

        opt un usuario sale de la partida
            Usuario -> Frontend: Abandonar Partida
            Frontend -> Backend: leave
            alt quedan usuarios
                Frontend <-- Backend: chat("El usuario foo ha abandonado la partida")
                Frontend <-- Backend: chat("El usuario bar es el nuevo líder")
                Frontend <-- Backend: game_owner(bar), solo al nuevo líder
            else no quedan usuarios
                Frontend <-- Backend: game_cancelled
            end
        end
    end

    Frontend <-- Backend: game_ended(winners)
    Frontend -> Usuario: winners

    loop por cada usuario
        User -> Frontend: Salir de Partida
        Frontend -> Backend: leave
    end

    @enduml

Mensajes Websockets
###################

Para el correcto funcionamiento de la comunicación, es necesario el uso de la
librería SocketIO en el cliente.

El nombre de los mensajes es el mismo que las funciones a contactar. Por
ejemplo, si se quiere contactar con el endpoint de :meth:`create_game`, se debe
emitir un mensaje de tipo ``create_game``.

Parámetros
##########

El paso de parámetros será pasando directamente el valor en mensajes con solo un
parámetro (y cuando no haya posibles parámetros opcionales), o con un objeto
JSON cuando haya múltiples parámetros.

Los parámetros devueltos se ajustarán a las descripciones de return de cada
endpoint.

.. _errores:

Errores y Validación
####################

Los errores de las peticiones serán devueltos al cliente llamando a un callback
definido en la función emit de SocketIO. Todos los errores estarán en formato
JSON, donde habrá un campo ``error: str`` que contendrá el mensaje de error
devuelto.

.. code-block:: javascript
  :linenos:

  socket.emit('join', dataToEmit, function (data) {
      if (data && data.error) {
          console.error(data.error);
      }
  });

.. _reference:

Referencia
##########
"""

import functools

from flask import request, session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_socketio import emit, join_room, leave_room

from gatovid.exts import socket
from gatovid.match import MAX_MATCH_USERS, MM, GameLogicException, PrivateMatch
from gatovid.models import User
from gatovid.util import get_logger

logger = get_logger(__name__)


def _requires_game(started=False):
    """
    Decorador para comprobar si el usuario está en una partida. Si started es
    True, se comprueba también que la partida ha empezado.
    """

    def deco(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            game = session.get("game")
            if not game:
                return {"error": "No estás en una partida"}

            match = MM.get_match(game)
            if not match:
                # FIXME: creo que esto no podría llegar a pasar, porque para que
                # la partida no exista, el usuario ha tenido que salir. Sino, se
                # retiene la partida.
                return {"error": "La partida no existe"}

            if started and not match.is_started():
                return {"error": "La partida no ha comenzado"}

            return f(*args, **kwargs)

        return wrapper

    return deco


@socket.on("connect")
def connect():
    """
    Devuelve falso si se prohibe la conexión del usuario porque no ha iniciado
    sesión.
    """

    try:
        # Comprobamos si el token es válido. Si el token es inválido, lanzará
        # una excepción.
        verify_jwt_in_request()
    except Exception:
        return False

    # Inicializamos la sesión del usuario
    email = get_jwt_identity()

    session["user"] = User.query.get(email)
    session["user"].sid = request.sid

    logger.info(f"New session with user {session['user'].name}")
    return True


@socket.on("disconnect")
def disconnect():
    # La sesión del usuario se limpia al reconectarse, aunque existen casos que
    # necesitan limpieza.
    logger.info(f"Ending session with user {session['user'].name}")

    # Puede estar buscando una partida pública
    if session["user"] in MM.users_waiting:
        MM.stop_waiting(session["user"])

    # Puede estar metido en una partida, tenemos que hacer que salga.
    if session.get("game"):
        leave()


@socket.on("search_game")
def search_game():
    """
    Unión a una partida pública organizada por el servidor.

    :return: El cliente no recibirá respuesta hasta que el servidor haya
        encontrado oponentes contra los que jugar. Una vez encontrada una
        partida, recibirá un mensaje de tipo `found_game` con un objeto JSON que
        contiene un atributo ``code: str`` con el código de la partida.
    """

    logger.info(f"User {session['user'].name} is waiting for a game")
    MM.wait_for_game(session["user"])


@socket.on("create_game")
def create_game():
    """
    Creación y unión automática a una partida privada.

    :return: Un mensaje de tipo ``create_game`` con un objeto JSON con el campo:

        * ``game: str``
    """

    game_code = MM.create_private_game(owner=session["user"])
    join(game_code)
    emit("create_game", {"code": game_code})

    logger.info(f"User {session['user'].name} has created private game {game_code}")


@socket.on("start_game")
@_requires_game()
def start_game():
    """
    Puesta en marcha de una partida privada.

    Requiere que el usuario esté en una partida y que sea el líder o se
    devolverá un :ref:`error <errores>`. También deben haber al menos 2
    jugadores en total esperando la partida para empezarla.

    :return: Un mensaje de tipo ``start_game`` a todos los jugadores esperando
        en la sala.
    """

    game = session["game"]
    match = MM.get_match(game)

    # Comprobamos si el que empieza la partida es el creador
    try:
        if match.owner != session["user"]:
            return {"error": "Debes ser el lider para empezar partida"}
    except (AttributeError, TypeError):
        # Si la partida devuelta por el MM es una pública, no tiene sentido
        # empezar la partida (ya se encarga el manager)
        return {"error": "La partida no es privada"}

    if len(match.users) < 2:
        return {"error": "Se necesitan al menos dos jugadores"}

    match.start()

    logger.info(f"User {session['user'].name} has started private game {game}")


@socket.on("join")
def join(game_code):
    """
    Unión a una partida proporcionando un código de partida.

    Un jugador no se puede unir a una partida si ya está en otra o si ya está
    llena.

    :param game_code: Código de partida
    :type game_code: ``str``

    :return: Si la partida es privada, un mensaje de tipo ``users_waiting`` con
        un entero indicando el número de jugadores esperando a la partida
        (incluido él mismo). En cualquier caso, un mensaje de chat (ver formato
        en :meth:`chat`) indicando que el jugador se ha unido a la partida.
    """

    if session.get("game"):
        return {"error": "Ya estás en una partida"}

    if not isinstance(game_code, str):
        return {"error": "Tipo incorrecto para el código de partida"}

    # Restricciones para unirse a la sala
    match = MM.get_match(game_code)
    if match is None or len(match.users) > MAX_MATCH_USERS:
        return {"error": "La partida no existe o está llena"}

    # Guardamos la partida actual en la sesión
    session["game"] = game_code

    # Guardamos al jugador en la partida
    try:
        match.add_user(session["user"])
    except GameLogicException as e:
        return {"error": str(e)}

    # Unimos al usuario a la sesión de socketio
    join_room(game_code)

    if isinstance(match, PrivateMatch):
        # Si es una partida privada, informamos a todos los de la sala del nuevo
        # número de jugadores. El lider decidirá cuando iniciarla.
        emit("users_waiting", len(match.users), room=game_code)
    else:
        # Si es una partida pública, iniciamos la partida si ya están todos.
        # Si hay algún jugador que no se une a la partida, la partida acabará
        # empezando (si hay suficientes jugadores) debido al start_timer en
        # PublicMatch.
        if len(match.users) == match.num_users:
            match.start()

    emit(
        "chat",
        {
            "msg": session["user"].name + " se ha unido a la partida",
            "owner": "[GATOVID]",
        },
        room=game_code,
    )

    logger.info(f"User {session['user'].name} has joined the game {game_code}")


@socket.on("leave")
@_requires_game()
def leave():
    """
    Salir de la partida actual. Requiere que el usuario esté en una partida o se
    devolverá un :ref:`error <errores>`.

    :return:
        * Si la partida no se borra porque quedan jugadores:

          - Un mensaje de tipo ``users_waiting`` con un entero indicando el
            número de jugadores esperando a la partida.
          - Un mensaje de ``chat`` (ver formato en :meth:`chat`) indicando que
            el jugador ha abandonado la partida.
          - Si se ha delegado el cargo de líder, el nuevo líder recibirá un
            mensaje de tipo ``game_owner``.
        * Si la partida se borra porque no quedan jugadores:

          - Si ya había terminado, un mensaje de tipo ``game_ended``, acompañado
            por un objeto con información sobre los ganadores. TODO describir.
          - Si no había terminado y se ha cancelado, un mensaje de tipo
            ``game_cancelled``.
    """

    game_code = session["game"]
    leave_room(game_code)
    emit(
        "chat",
        {
            "msg": session["user"].name + " ha abandonado la partida",
            "owner": "[GATOVID]",
        },
        room=game_code,
    )
    del session["game"]

    match = MM.get_match(game_code)
    match.users.remove(session["user"])
    if len(match.users) == 0:
        match.end()
        # Eliminarla del gestor de partidas
        MM.remove_match(game_code)
        return  # La partida ha acabado, no seguir
    else:
        emit("users_waiting", len(match.users), room=game_code)

    # Comprobar si hay que delegar el cargo de lider
    if isinstance(match, PrivateMatch):
        if match.owner == session["user"]:
            # Si él es el lider, delegamos el cargo de lider a otro jugador
            match.owner = match.users[0]
            # Mensaje solo al nuevo dueño de la sala
            emit(
                "chat",
                {
                    "msg": match.owner.name + " es el nuevo líder",
                    "owner": "[GATOVID]",
                },
                room=game_code,
            )
            emit("game_owner", room=match.owner.sid)

    logger.info(f"User {session['user'].name} has left the game {game_code}")


@socket.on("chat")
@_requires_game(started=True)
def chat(msg):
    """
    Enviar un mensaje al chat de la partida. Requiere que el usuario esté en una
    partida y que esté empezada o se devolverá un :ref:`error <errores>`.

    :param msg: Mensaje a enviar
    :type msg: ``str``

    :return: Un mensaje de tipo ``chat`` con un objeto JSON que contiene los
        campos:

        * ``msg: str`` Mensaje enviado por el jugador
        * ``owner: str`` Nombre de usuario del jugador que envía el mensaje
    """

    if not isinstance(msg, str):
        return {"error": "Tipo incorrecto para el mensaje"}

    emit(
        "chat",
        {
            "msg": msg,
            "owner": session["user"].name,
        },
        room=session["game"],
    )

    logger.info(
        f"New message at game {session['game']} from user {session['user'].name}"
    )


@socket.on("play_discard")
@_requires_game(started=True)
def play_discard(data):
    """
    Descarta las cartas indicadas de la mano del usuario.

    Requiere que el usuario esté en una partida y que esté empezada o se
    devolverá un :ref:`error <errores>`.
    """


@socket.on("play_draw")
@_requires_game(started=True)
def play_draw():
    """
    Roba tantas cartas como sean necesarias para que el usuario tenga 3.

    Requiere que el usuario esté en una partida y que esté empezada o se
    devolverá un :ref:`error <errores>`.
    """


@socket.on("play_pass")
@_requires_game(started=True)
def play_pass():
    """
    Pasa el turno del usuario.

    Requiere que el usuario esté en una partida y que esté empezada o se
    devolverá un :ref:`error <errores>`.
    """


@socket.on("play_card")
@_requires_game(started=True)
def play_card(data):
    """
    Juega una carta de su mano.

    Requiere que el usuario esté en una partida y que esté empezada o se
    devolverá un :ref:`error <errores>`.
    """
