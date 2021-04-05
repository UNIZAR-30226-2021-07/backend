Autenticación
=============

La autenticación usada es mediante JWTs, que dan la posibilidad de usar un mismo
método para ambos APIs disponibles. Se puede ver discusión en detalle sobre la
toma de esta decisión y detalles de implementación en `GitHub
<https://github.com/UNIZAR-30226-2021-07/documentacion/issues/18>`_.

Funcionamiento
##############

La siguiente explicación puede ayudar a entender cómo funciona la autenticación
en el backend:

1. Cuando un usuario se registra, se guarda en la BBDD.
2. Login se basa en comprobar que el usuario esta en la BBDD y la contraseña
   coincide con un hash que hay guardado (para no guardar contraseñas en la
   bbdd, por si se filtrase).
3. Cuando te has loggeado, te da un token que tiene codificado en él:

  1. Identidad: el email en este caso
  2. Fecha de expiracion
  3. Resto de datos para el cifrado

  Va cifrado de tal manera que solo el servidor lo puede desencriptar y, como la
  información va metida en el token, no hace falta una base de datos de tokens.

4. El logout es más complicado porque como los tokens no están en memoria hay
   que prohibirlos de alguna forma. Para eso ponemos una tabla en la BBDD de
   tokens prohibidos y, cuando se hace logout se prohibe entrar con ese token.

.. _error_autenticacion:

Errores de Autenticación
########################

Un error de autenticación se puede deber a una de las siguientes tres razones:

1. El token es inválido: el valor simplemente no es un token.
2. El token está expirado: los tokens son temporales, y expiran en
   aproximadamente una hora por defecto. Esto implica una mayor seguridad,
   pero por tanto será necesario hacer un login cada vez que suceda.
3. El token ha sido revocado anteriormente: el token ha sido revocado
   manualmente. Por ejemplo se ha hecho logout, o se ha borrado su cuenta.
