.. currentmodule:: gatovid.api.game

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

Códigos de Partida
******************

Una partida se representa por una combinación de 4 caracteres alfanuméricos,
excluyendo aquellas combinaciones consideradas ambigüas [#f1]_ [#f2]_:

* 'O', '0'
* 'I', '1'
* 'B', '8'
* '2', 'Z'

Resultando en el siguiente set de caracteres, con el que se siguen teniendo
:math:`28^4 = 614.656` combinaciones, suficiente para lo que se necesita.

.. autoattribute:: gatovid.api.game.match.CODE_ALLOWED_CHARS

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

        opt hay 2 usuarios
            Frontend -> Frontend: start_timer(TIME_UNTIL_START)
        end
    end

    Frontend <-- Backend: found_game("8XA1")
    Frontend -> Frontend: start_timer(TIME_UNTIL_START)

    loop hasta que acabe el timer o todos los usuarios se hayan unido
        Frontend -> Backend: join("8XA1")
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

Abandono de la Partida
######################

Se describe a continuación la funcionalidad de abandono y reconexión a las
partidas:

El botón de abandonar es pulsado:

- **Pública**: el jugador es eliminado y no se puede volver; el jugador es
  reemplazado por la IA.

  El cliente tendrá que llamar a ``leave`` manualmente para ello.
- **Privada**: el jugador es eliminado y no se puede volver; las cartas del
  jugador van a la baraja.

  El cliente tendrá que llamar a ``leave`` manualmente para ello.

Desconexión por error o botón de reanudar más tarde pulsado:

- **Pública**: no se puede volver a jugar, se abandonará la partida
  automáticamente.
- **Privada**: se puede volver a la partida y no habrá pasado nada porque en
  partidas privadas no se eliminan jugadores AFK.

  Para volver únicamente hace falta llamar a ``join`` con el código de partida
  previo, y el cliente recibirá un :ref:`msg_start_game` seguido de un
  :ref:`msg_game_update` con el estado completo de la partida.

.. warning::
    Notar que una desconexión puede causar que se cancele una partida, en cuyo
    caso se enviará un mensaje de :ref:`msg_game_cancelled` a todos los
    participantes de esta. Es importante que el cliente salga de la partida
    manualmente con ``leave`` una vez reciba dicho mensaje, o no podrá unirse
    correctamente a otras partidas.

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

.. _msg_stop_searching:

``stop_searching``
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
        // Terminación de la partida.
        "finished": false,
        // Lista de ganadores. Se incluye la posición de cada jugador, y las
        // monedas que ha ganado por ello.
        //
        // Se mandará para indicar la terminación de la partida y la de un
        // jugador individual, en cuyo caso `position` y `coins` serán nulos.
        "leaderboard": {
            "manolo22": {
                "position": 1,
                "coins": 50,
            },
            // ...
        },
        // Tiempo de juego en minutos.
        "playtime_mins": 4,
        // Nombre del usuario con el turno actual.
        "current_turn": "manolo22",
        // Información de los jugadores, enviada al inicio de la partida o
        // cuando alguien abandone (y posiblemente sea reemplazado por la IA).
        //
        // Notar que el nombre de usuario no cambiará durante la partida. En el
        // caso de que un usuario sea reemplazado por la IA el cliente le podría
        // mostrar el nombre al usuario añadiendo "[BOT]" al final, o usar un
        // icono indicativo, pero esto toma lugar en el frontend.
        //
        // IMPORTANTE: es posible que el mismo usuario que recibe el mensaje no
        // aparezca en esta lista, lo que significa que ha sido eliminado de la
        // partida por estar AFK o porque ha pulsado el botón de abandono. En
        // caso de no encontrarse a sí mismo en este campo, el usuario tendrá
        // que llamar al endpoint "leave" para abandonar la partida manualmente.
        "players": [
            {
                "name": "marcuspkz",
                // Verdadero si el usuario ha sido reemplazado por la IA.
                // Opcional.
                "is_ai": false,
                // La foto puede cambiar si ha sido reemplazado por la IA.
                // Opcional.
                "picture": 4,
                // El jugador que reciba el mensaje tendrá su tablero.
                // Opcional.
                "board": 2,
            },
            // ...
        ],
        // Mano del jugador actual (solo él tendrá esa información).
        "hand": [
            {"card_type": "organ", "color": "red"},
            {"card_type": "virus", "color": "green"},
            {"card_type": "treatment", "treatment_type": "infection"},
        ],
        // Los cuerpos de los jugadores.
        "bodies": {
            // Pila del jugador, siempre de longitud 4.
            "marcuspkz": [
                {
                    // Puede ser nulo si no hay nada en esa posición.
                    "organ": {
                        "card_type": "organ",
                        "color": "red"
                    }
                    // Puede estar vacío si no hay modificadores.
                    "modifiers": [
                        {"card_type": "virus", "color": "red"},
                        // ...
                    ]
                },
                // ....
            ],
            // ...
        },
    }

.. _game_reference:

Referencia
##########

.. automodule:: gatovid.api.game
    :members:
        chat,
        create_game,
        join,
        leave,
        pause_game,
        play_card,
        play_discard,
        play_pass,
        search_game,
        stop_searching,
        start_game,

---

.. rubric:: Anotaciones

.. [#f1] https://ux.stackexchange.com/a/53345
.. [#f2] https://sam-rogers.medium.com/an-unambigious-id-code-character-set-b0fc63f3c0d7
