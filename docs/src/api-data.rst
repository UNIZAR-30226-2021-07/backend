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
cliente básico para acceder a la API de datos:

1. Hacer petición
2. Comprobar si hay un error

  1. Si no hay error se puede usar el valor devuelto
  2. Si hay error:

    1. Si es 401, será necesario refrescar el token y volver al punto 1.
    2. Si el código es 400:

      1. Si es fallo del usuario se le muestra el mensaje de error del campo
         `error`.
      2. Si es fallo del programador, tendrá que hacerse debug en el cliente y
         solucionarlo, ya que no es esperado que suceda. Se puede usar el
         campo `error` para ello.

    3. Si es 500, tendrá que hacerse debug en el backend y solucionarlo, que
       será donde se encuentre más información. En este caso no se puede usar el
       campo `error`, por tanto.

Endpoints
#########

.. currentmodule:: gatovid.api.data

.. autofunction:: signup
.. autofunction:: login
.. autofunction:: logout
.. autofunction:: remove_user
.. autofunction:: modify_user
.. autofunction:: user_data
.. autofunction:: user_stats
.. autofunction:: test
.. autofunction:: protected
