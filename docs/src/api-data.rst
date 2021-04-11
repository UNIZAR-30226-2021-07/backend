.. currentmodule:: gatovid.api.data

API de Datos
============

Errores y Validación
####################

Existen varios tipos de errores que pueden devolverse desde la API de datos:

1. :ref:`error_validacion` (400): la petición al servidor es inválida porque se
   le ha pasado uno o más parámetros inválidos, o su estructura no es la
   esperada.
2. :ref:`error_autenticacion` (401): un token ha sido usado de forma inválida:

3. Error interno (500-599): una excepción inesperada y que ha causado una
   terminación del servidor. No tendrá ningún mensaje que lo acompañe.

.. _error_validacion:

Errores de Validación
*********************

Todos los endpoints validan los parámetros que se le pasan. Generalmente, se
comprueba lo siguiente:

* Que su valor no sea nulo.
* Que el tipo sea el adecuado. Esto será importante solo cuando la variable sea
  algo distinto a una cadena.
* Comprobaciones lógicas

Casos específicos
-----------------

.. currentmodule:: gatovid.models

El correo electrónico tiene que cumplir la siguiente expresión regular:

.. autoattribute:: gatovid.models.User.EMAIL_REGEX

Y el nombre la siguiente:

.. autoattribute:: gatovid.models.User.NAME_REGEX

La longitud de la contraseña tendrá que estar entre los dos valores siguientes:

.. autoattribute:: gatovid.models.User.MIN_PASSWORD_LENGTH
.. autoattribute:: gatovid.models.User.MAX_PASSWORD_LENGTH

También puede deberse a otros errores lógicos, como que se intente asignar a un
usuario una foto de perfil o tapete que no haya comprado.

Cliente Básico
**************

Dadas las restricciones anteriores, se describe a continuación cómo sería un
cliente básico para acceder a la API de datos, que permite entender de forma
sencilla el flujo de control de manejo de errores:

.. uml::
    :align: center

    @startuml
    !pragma useVerticalIf on

    start

    :Hacer petición;

    if (¿se produjo un error?) then (sí)
        if (error == 400) then (sí)
            if (de quién es el fallo?) then (del usuario)
                :Se le muestra el mensaje
                de error del campo `error`;
            else (del frontend)
                stop

                note right
                    Debug en el cliente y
                    solucionarlo, ya que no
                    es esperado que suceda.
                    Se puede usar el campo
                    `error` para ello.
                end note
            endif
        elseif (error == 401) then (sí)
            :Refrescar el token;

            stop

            note right
                Reintentar petición
            end note
        elseif (error >= 500 && error <= 599) then (sí)
            :Error en el backend;

            stop

            note right
                Debug en el backend y
                solucionarlo, que será
                donde se encuentre más
                información.
            end note
        endif
    else (no)
        :Se puede usar el valor devuelto;
    endif

    stop

    @enduml

Referencia
##########

.. automodule:: gatovid.api.data
    :members:
        login,
        logout,
        modify_user,
        protected,
        remove_user,
        signup,
        test,
        user_data,
        user_stats,
