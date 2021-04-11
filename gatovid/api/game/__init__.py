"""
API del Juego
=============

Módulo con el API de websockets para la comunicación en tiempo real con los
clientes, como el juego mismo o el chat de la partida.

Funcionamiento del juego
########################

En esta sección se incluyen diagramas sobre la comunicación entre el cliente y
el servidor de forma más visual que textualmente. Para más detalles sobre los
mensajes consultar la :ref:`game_msgs_reference`, y para los endpoints
:ref:`game_reference`.

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
confirmar que se quieren unir (también con un timer para evitar esperas
infinitas).

.. uml::
    :align: center

    @startuml
    hide footbox

    actor Usuario
    participant Frontend
    participant Backend

    loop hasta que acabe el timer o hayan 6 usuarios buscando partida
        Usuario -> Frontend: Buscar Partida
        Frontend -> Backend: search_game

        Frontend -> Frontend: start_timer(TIME_UNTIL_START)
    end

    Frontend <-- Backend: found_game("8XA1")
    Frontend -> Frontend: start_timer(TIME_UNTIL_START)

    loop hasta que el timer termine o todos los usuarios se hayan unido
        Frontend -> Backend: join("8XA1")
        Frontend --> Backend: start_game
    end

    alt hay >=2 usuarios
        Frontend <-- Backend: start_game
    else hay <2 usuarios
        Frontend <-- Backend: game_cancelled
    end

    @enduml

Transcurso de la Partida
************************

Una vez la partida haya comenzado, el transcurso de la partida será el
siguiente:

.. uml::
    :align: center

    @startuml
    hide footbox

    actor Usuario
    participant Frontend
    participant Backend

    loop hasta que acabe la partida
        opt chat
            Usuario -> Frontend: Enviar Mensaje
            Frontend -> Backend: chat(msg)
            Frontend <-- Backend: chat(msg)
        end

        opt abandonar
            Usuario -> Frontend: Abandonar Partida
            Frontend -> Backend: leave

            alt quedan usuarios
                Frontend <-- Backend: chat("El usuario foo ha abandonado la partida")
                alt es privada
                    Frontend <-- Backend: chat("El usuario bar es el nuevo líder")
                    Frontend <-- Backend: game_owner(bar), solo al nuevo líder
                else es publica
                    Backend -> Backend: enable_ia(usuario)
                end
            else no quedan usuarios
                Frontend <-- Backend: game_cancelled
            end
        end

        alt descarte
            Usuario -> Frontend: Descartar
            Frontend -> Backend: play_discard
            Frontend <-- Backend: game_update
        else jugar carta
            Usuario -> Frontend: Jugar Carta
            Frontend -> Backend: play_card
            Frontend <-- Backend: game_update
        else pasar
            Usuario -> Frontend: Pasar
            Frontend -> Backend: play_pass
            Frontend <-- Backend: game_update
        else robar
            Usuario -> Frontend: Robar
            Frontend -> Backend: play_draw
            Frontend <-- Backend: game_update
        end
    end

    Frontend <-- Backend: game_ended(winners)
    Frontend -> Usuario: podio(winners)

    loop por cada usuario
        Usuario -> Frontend: Salir de Partida
        Frontend -> Backend: leave
        Frontend <-- Backend: chat("El usuario foo ha abandonado la partida")
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

.. _game_msgs_reference:

Mensajes
########

Se listan en esta sección todos los tipos de mensajes, como referencia
principal, para que se puedan serializar como objetos si se considera necesario:

.. _msg_create_game:

``create_game``
***************

.. code-block:: javascript

    {
        // Código de la partida, compuesto por caracteres alfanuméricos, con las
        // letras en mayúsculas.
        "code": "A83D",
    }

.. _msg_found_game:

``found_game``
**************

.. code-block:: javascript

    {
        // Código de la partida, compuesto por caracteres alfanuméricos, con las
        // letras en mayúsculas.
        "code": "A83D",
    }

.. _msg_users_waiting:

``users_waiting``
*****************

Mensaje cuyo contenido es únicamente un entero con el número de usuarios
esperando, incluido el mismo que lo haya recibido.

.. _msg_start_game:

``start_game``
**************

Mensaje sin campos adicionales.

.. _msg_game_owner:

``game_owner``
**************

Mensaje sin campos adicionales.

.. _msg_game_cancelled:

``game_cancelled``
******************

Mensaje sin campos adicionales.

.. _msg_chat:

``chat``
**************

.. code-block:: javascript

    {
        // Mensaje enviado por el jugador
        "msg": "Bona tarda",
        // Nombre de usuario del jugador que envía el mensaje. Será
        // ``[GATOVID]`` si es un mensaje del sistema, para indicar p.ej. que un
        // usuario ha abandonado la partida.
        "owner": "manolet22",
    }

.. _msg_game_update:

``game_update``
***************

Como forma de optimización este tipo de mensaje no tiene por qué incluir todos
los campos; solo se actualizará al frontend con lo que sea necesario.

.. code-block:: javascript

    {
        // Terminación de la partida, opcional.
        "finished": false,
        // Nombre del usuario con el turno actual, opcional.
        "current_turn": "manolo22",
        // Manos de los jugadores, opcional.
        // Solo se sabrá la mano completa del usuario que recibe el mensaje. Los
        // demás únicamente tendrán el número de cartas.
        "hands": {
            // Jugador actual
            "manolo22": {
                "organs": [
                    // TODO
                ],
                "effects": [
                    // TODO
                ],
                "cards": [
                    // TODO
                ],
            },
            // Otro jugador
            "juanma2000": {
                "organs": [
                    // TODO
                ],
                "effects": [
                    // TODO
                ],
                "num_cards": 3,
            },
            // ...
        },
        // Tiempo de juego en minutos, opcional.
        "playtime_mins": 4,
        // Lista de ganadores, opcional.
        // Se incluye la posición de cada jugador, comenzando desde el 1, y las
        // monedas que ha ganado por ello.
        "leaderboard": [
            "manolo22": {
                "position": 1,
                "coins": 50,
            },
            // ...
        ],
    }

.. _game_reference:

Referencia
##########
"""

import functools

from flask import request, session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_socketio import emit, join_room, leave_room

from gatovid.api.game.match import MAX_MATCH_USERS, MM, GameLogicException, PrivateMatch
from gatovid.exts import socket
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
        encontrado oponentes contra los que jugar.

        Una vez encontrada una partida, hará un broadcast de
        :ref:`msg_found_game`.

        Si ya está buscando partida, se devolverá un :ref:`error <errores>`.
    """

    if session.get("game") is not None:
        return {"error": "El usuario ya está en una partida privada"}

    logger.info(f"User {session['user'].name} is waiting for a game")
    try:
        MM.wait_for_game(session["user"])
    except GameLogicException as e:
        return {"error": str(e)}


@socket.on("create_game")
def create_game():
    """
    Creación y unión automática a una partida privada.

    :return: Un mensaje de tipo :ref:`msg_create_game`.

        Si está buscando una partida pública, se devolverá un :ref:`error
        <errores>`.
    """

    if session.get("game") is not None:
        return {"error": "El usuario ya está en una partida privada"}

    try:
        game_code = MM.create_private_game(owner=session["user"])
    except GameLogicException as e:
        return {"error": str(e)}
    join(game_code)
    emit("create_game", {"code": game_code})

    logger.info(f"User {session['user'].name} has created private game {game_code}")


@socket.on("start_game")
@_requires_game()
def start_game():
    """
    Puesta en marcha de una partida privada.

    :return: Un broadcast de :ref:`msg_start_game`.

        Requiere que el usuario esté en una partida y que sea el líder o se
        devolverá un :ref:`error <errores>`. También deben haber al menos 2
        jugadores en total esperando la partida para empezarla.
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

    :param game_code: Código de partida
    :type game_code: ``str``

    :return: Si la partida es privada, un broadcast de :ref:`msg_users_waiting`.

        En cualquier caso, un broadcast de :ref:`msg_chat` indicando que el
        jugador se ha unido a la partida.

        Un jugador no se puede unir a una partida si ya está en otra o si ya
        está llena. En caso contrario se devolverá un :ref:`error <errores>`.
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
    Salir de la partida actual.

    :return:
        * Si la partida no se borra porque quedan jugadores:

          - Un mensaje de tipo :ref:`msg_users_waiting`.
          - Un broadcast de :ref:`msg_chat` indicando que el jugador ha
            abandonado la partida.
          - Si se ha delegado el cargo de líder, el nuevo líder recibirá un
            mensaje de tipo :ref:`msg_game_owner`.
        * Si la partida se borra porque no quedan jugadores:

          - Si ya había terminado, un :ref:`error <errores>`.
          - Si no había terminado y se ha cancelado, un mensaje de tipo
            :ref:`msg_game_cancelled`.

        Requiere que el usuario esté en una partida o se devolverá un
        :ref:`error <errores>`.
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
    logger.info(f"User {session['user'].name} has left the game {game_code}")
    if len(match.users) == 0:
        match.end()
        # Eliminarla del gestor de partidas
        MM.remove_match(game_code)
        return  # La partida ha acabado, no seguir

    emit("users_waiting", len(match.users), room=game_code)

    # Comprobar si hay que delegar el cargo de lider
    if isinstance(match, PrivateMatch):
        if match.owner == session["user"]:
            # Si él es el lider, delegamos el cargo de lider a otro jugador
            match.owner = match.users[0]

            emit(
                "chat",
                {
                    "msg": match.owner.name + " es el nuevo líder",
                    "owner": "[GATOVID]",
                },
                room=game_code,
            )

            # Mensaje solo al nuevo dueño de la sala
            emit("game_owner", room=match.owner.sid)


@socket.on("chat")
@_requires_game(started=True)
def chat(msg):
    """
    Enviar un mensaje al chat de la partida.

    :param msg: Mensaje a enviar
    :type msg: ``str``

    :return: Broadcast de un mensaje :ref:`msg_chat`.

        Si el usuario no está en una partida empezada se devolverá un
        :ref:`error <errores>`.
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
    .. warning:: Este endpoint está en construcción aún.

    Descarta las cartas indicadas de la mano del usuario.

    Requiere que el usuario esté en una partida y que esté empezada o se
    devolverá un :ref:`error <errores>`.

    :return: Un mensaje :ref:`msg_game_update` para cada jugador.

        Si el usuario no está en una partida se devolverá un :ref:`error
        <errores>`.
    """


@socket.on("play_draw")
@_requires_game(started=True)
def play_draw():
    """
    .. warning:: Este endpoint está en construcción aún.

    Roba tantas cartas como sean necesarias para que el usuario tenga 3.

    Requiere que el usuario esté en una partida y que esté empezada o se
    devolverá un :ref:`error <errores>`.

    :return: Un mensaje :ref:`msg_game_update` para cada jugador.

        Si el usuario no está en una partida se devolverá un :ref:`error
        <errores>`.
    """


@socket.on("play_pass")
@_requires_game(started=True)
def play_pass():
    """
    .. warning:: Este endpoint está en construcción aún.

    Pasa el turno del usuario.

    Requiere que el usuario esté en una partida y que esté empezada o se
    devolverá un :ref:`error <errores>`.

    :return: Un mensaje :ref:`msg_game_update` para cada jugador.

        Si el usuario no está en una partida se devolverá un :ref:`error
        <errores>`.
    """


@socket.on("play_card")
@_requires_game(started=True)
def play_card(data):
    """
    .. warning:: Este endpoint está en construcción aún.

    Juega una carta de su mano.

    Requiere que el usuario esté en una partida y que esté empezada o se
    devolverá un :ref:`error <errores>`.

    :return: Un mensaje :ref:`msg_game_update` para cada jugador.

        Si el usuario no está en una partida se devolverá un :ref:`error
        <errores>`.
    """
