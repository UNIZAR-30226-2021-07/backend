"""
Tests para la creación de usuarios y su gestión.
"""

from sqlalchemy.exc import IntegrityError

from gatovid.exts import db
from gatovid.models import Purchase, Stats, User

from .base import GatovidTestClient


class UserTest(GatovidTestClient):
    existing_user = {
        "email": "test_user1@gmail.com",
        "name": "test_user1",
        "password": "whatever1",
    }

    new_user = {
        "name": "someone",
        "email": "someone@gmail.com",
        "password": "12345678",
    }

    existing_user_full = {
        "board": 0,
        "coins": 133,
        "email": "test_user1@gmail.com",
        "name": "test_user1",
        "picture": 0,
        "purchases": [
            {
                "item_id": 1,
                "type": "board",
            },
            {
                "item_id": 2,
                "type": "profile_pic",
            },
        ],
    }

    all_stats = {
        "test_user1": {
            "games": 0,
            "wins": 0,
            "losses": 0,
            "playtime_mins": 1571,
        },
        "test_user2": {
            "games": 13,
            "losses": 3,
            "wins": 10,
            "playtime_mins": 10,
        },
        "test_user3": {
            "games": 124,
            "losses": 121,
            "wins": 3,
            "playtime_mins": 0,
        },
    }

    def test_data(self):
        """
        Test para el endpoint de los datos del usuario.
        """

        token_resp = self.request_token(self.existing_user)
        self.assertRequestOk(token_resp)

        token = token_resp.json["access_token"]

        got = self.request_data(token)
        self.assertRequestOk(got)
        self.assertEqual(got.json, self.existing_user_full)

    def test_stats(self):
        """
        Test para el endpoint de las estadísticas.
        """

        for name, expected in self.all_stats.items():
            got = self.request_stats(name)
            self.assertRequestOk(got)
            self.assertEqual(got.json, expected)

    def test_signup_empty(self):
        """
        Test para valores tanto vacíos como no incluidos en los datos.
        """

        for field in ("name", "email", "password"):
            user = self.new_user.copy()

            user[field] = ""
            resp = self.request_signup(user)
            self.assertRequestErr(resp, 400)

            del user[field]
            resp = self.request_signup(user)
            self.assertRequestErr(resp, 400)

    def test_signup_existing_user(self):
        """
        Los nombres de usuario son únicos.
        """

        user = {
            "name": self.new_user["name"],
            "email": self.existing_user["email"],
            "password": self.new_user["password"],
        }
        resp = self.request_signup(user)
        self.assertRequestErr(resp, 400)

    def test_signup_existing_email(self):
        """
        Los email también son únicos.
        """

        user = {
            "name": self.existing_user["name"],
            "email": self.new_user["email"],
            "password": self.new_user["password"],
        }
        resp = self.request_signup(user)
        self.assertRequestErr(resp, 400)

    def test_signup(self):
        """
        Test básico para la creación de un usuario nuevo.
        """

        resp = self.request_signup(self.new_user)
        self.assertRequestOk(resp)

        # Un segundo intento fallará
        resp = self.request_signup(self.new_user)
        self.assertRequestErr(resp, 400)

    def test_signup_length(self):
        """
        Tests de caja negra de valores límite para la longitud de campos como la
        contraseña o el nombre.
        """

        tests = {
            "password": (User.MIN_PASSWORD_LENGTH, User.MAX_PASSWORD_LENGTH),
            "name": (User.MIN_NAME_LENGTH, User.MAX_NAME_LENGTH),
        }

        unique_id = 0
        for field, values in tests.items():
            min_val, max_val = values
            values = [
                ("", False),
                ("x", False),
                ("x" * (min_val - 1), False),
                ("x" * min_val, True),
                ("x" * (min_val + 1), True),
                ("x" * max_val, True),
                ("x" * (max_val + 1), False),
                ("x" * (max_val * 100), False),
            ]

            for test_value, should_work in values:
                test_user = {
                    "name": f"edge_case{unique_id}",
                    "email": f"edge_case{unique_id}@gmail.com",
                    "password": "whatever",
                }
                test_user[field] = test_value

                resp = self.request_signup(test_user)
                if should_work:
                    self.assertRequestOk(resp)
                else:
                    self.assertRequestErr(resp, 400)

                unique_id += 1

    def test_signup_regex(self):
        """
        Tests de caja negra de particiones de equivalencia para casos especiales
        de las expresiones regulares para el email y nombre.
        """

        tests = {
            "email": [
                ("test@gmail.com", True),
                ("test@some-big-company.com", True),
                ("test.address.here@gmail.com", True),
                ("test@gmail.co.uk", True),
                ("test", False),
                ("test.com", False),
                ("@gmail.com", False),
                ("test@hello@email.com", False),
                ("test@.com", False),
                ("test@gmail", False),
                ("test@gmail.", False),
                ("test@gmail..com", False),
                (" @ . ", False),
            ],
            "name": [
                ("abc_abc_abc", True),
                ("abc abc_abc", False),
                ("           ", False),
                ("ñ→øþłßĸµ¢ð«", False),
            ],
        }

        unique_id = 0
        for field, values in tests.items():
            for value, should_work in values:
                test_user = {
                    "name": f"edge_case{unique_id}",
                    "email": f"edge_case{unique_id}@gmail.com",
                    "password": "whatever",
                }
                test_user[field] = value

                resp = self.request_signup(test_user)
                if should_work:
                    self.assertRequestOk(resp)
                else:
                    self.assertRequestErr(resp, 400)

                unique_id += 1

    def test_user_unique(self):
        """
        Aunque el registro tenga una validación manual de si el usuario ya
        existe, para evitar errores la base de datos también tiene que
        establecer que el nombre de usuario es único.

        Como el email es la clave primaria no hace falta comprobarlo en ese
        caso, pero el nombre es un atributo simple.
        """

        count = User.query.filter_by(name=self.new_user["name"]).count()
        self.assertEqual(count, 0)

        # Primer usuario con ese nombre
        user = User(
            email=self.new_user["email"],
            name=self.new_user["name"],
            password=self.new_user["password"],
        )
        db.session.add(user)
        db.session.commit()

        count = User.query.filter_by(name=self.new_user["name"]).count()
        self.assertEqual(count, 1)

        # Segundo usuario con ese nombre
        user = User(
            email="duplicate" + self.new_user["email"],
            name=self.new_user["name"],
            password=self.new_user["password"],
        )
        with self.assertRaises(IntegrityError):
            db.session.add(user)
            db.session.commit()

        db.session.rollback()

        count = User.query.filter_by(name=self.new_user["name"]).count()
        self.assertEqual(count, 1)

    def test_remove(self):
        """
        Test básico para comprobar que se elimina un usuario.
        """

        signup_resp = self.request_signup(self.new_user)
        self.assertRequestOk(signup_resp)

        token_resp = self.request_token(self.new_user)
        self.assertRequestOk(token_resp)

        # Un inicio de sesión ahora fallará porque ya existe el usuario
        signup_resp = self.request_signup(self.new_user)
        self.assertRequestErr(signup_resp, 400)

        token = token_resp.json["access_token"]
        remove_resp = self.request_remove(token, self.new_user)
        self.assertRequestOk(remove_resp)

        # Un registro ahora funcionará tras eliminar el usuario
        signup_resp = self.request_signup(self.new_user)
        self.assertRequestOk(signup_resp)

    def test_repeated_remove(self):
        """
        Probando si reusando el mismo token se puede borrar dos veces el mismo
        usuario, y si causa problemas en ese caso.
        """

        token_resp = self.request_token(self.existing_user)
        self.assertRequestOk(token_resp)
        token = token_resp.json["access_token"]

        # Primer intento
        remove_resp = self.request_remove(token, self.new_user)
        self.assertRequestOk(remove_resp)

        # Segundo intento
        remove_resp = self.request_remove(token, self.new_user)
        self.assertRequestErr(remove_resp, 401)

    def test_remove_cascade(self):
        """
        Se asegura de que al eliminar un usuario también desaparecen todos sus
        registros relacionados, como estadísticas o compras.
        """

        user_id = self.existing_user["email"]

        # Previamente sí que existen
        stats = Stats.query.filter_by(user_id=user_id).first()
        self.assertIsNotNone(stats)
        purchases = Purchase.query.filter_by(user_id=user_id).first()
        self.assertIsNotNone(purchases)

        # Inicio de sessión
        token_resp = self.request_token(self.existing_user)
        self.assertRequestOk(token_resp)
        token = token_resp.json["access_token"]

        # Y eliminación del usuario
        remove_resp = self.request_remove(token, self.existing_user)
        self.assertRequestOk(remove_resp)

        # Ahora no existen
        stats = Stats.query.filter_by(user_id=user_id).first()
        self.assertIsNone(stats)
        purchases = Purchase.query.filter_by(user_id=user_id).first()
        self.assertIsNone(purchases)

    def test_modify(self):
        """
        Un test básico del correcto correcto del endpoint de modificación de
        usuario.
        """

        token_resp = self.request_token(self.existing_user)
        token = token_resp.json["access_token"]

        payload = {
            "name": self.new_user["name"],
            "password": self.new_user["password"],
            "board": self.existing_user_full["purchases"][0]["item_id"],
            "picture": self.existing_user_full["purchases"][1]["item_id"],
        }
        modify_resp = self.request_modify(token, payload)
        self.assertRequestOk(modify_resp)

        # La nueva contraseña solo se puede comprobar iniciando sesión de nuevo
        # con ella.
        login_info = {
            "email": self.existing_user["email"],
            "name": payload["name"],
            "password": payload["password"],
        }
        token_resp = self.request_token(login_info)
        token = token_resp.json["access_token"]
        self.assertRequestOk(token_resp)

        # El resto de campos se pueden comprobar con la petición de datos del
        # usuario.
        modified = self.request_data(token).json
        for field in ("name", "board", "picture"):
            self.assertEqual(modified[field], payload[field])

    def test_modify_invalid(self):
        """
        Comprueba que la validación también está activa para la modifiación del
        perfil.
        """

        token_resp = self.request_token(self.existing_user)
        token = token_resp.json["access_token"]

        initial = self.request_data(token).json

        payload = {
            "name": "This is an invalid name",
        }
        modify_resp = self.request_modify(token, payload)
        self.assertRequestErr(modify_resp, 400)

        final = self.request_data(token).json
        self.assertEqual(initial, final)

    def test_type_validation(self):
        """
        Comprueba que se devuelve un error esperado (y no un 500) al enviar
        datos con tipo inválido. Se comprueba tanto para un tipo incorrecto
        como para un valor nulo.
        """

        # El email únicamente se puede comprobar en el registro
        for value in (1234, None):
            user = self.new_user.copy()
            user["email"] = value

            signup_resp = self.request_signup(user)
            self.assertRequestErr(signup_resp, 400)

        token_resp = self.request_token(self.existing_user)
        token = token_resp.json["access_token"]

        # Los demás se comprueban con el endpoint de modificar el perfil
        for field in ("board", "coins", "name", "password"):
            # Ninguno de ellos es un booleano
            for value in (True, None):
                user = self.new_user.copy()
                user[field] = value

                modify_resp = self.request_modify(token, user)
                self.assertRequestErr(modify_resp, 400)

    def test_modify_empty(self):
        """
        Prueba casos en los que no se debería cambiar el usuario. Algunos de los
        casos devolverán un error por tratarse de un claro fallo en el cliente.
        """

        # Payload con un booleano que indica si debería tener éxito.
        tests = [
            # Vacío
            ({}, False),
            # El email no se puede cambiar
            ({"email": "test@gmail.com"}, False),
            # Campos inexistentes
            ({"some_field_that_doesnt_exist": 1234}, False),
            # Los mismos valores
            (
                {
                    "name": self.existing_user["name"],
                    "password": self.existing_user["password"],
                },
                True,
            ),
        ]

        token_resp = self.request_token(self.existing_user)
        token = token_resp.json["access_token"]

        for payload, should_succeed in tests:
            initial_user_resp = self.request_data(token)
            self.assertRequestOk(initial_user_resp)

            modify_resp = self.request_modify(token, payload)
            if should_succeed:
                self.assertRequestOk(modify_resp)
            else:
                self.assertRequestErr(modify_resp, 400)

            modified_user_resp = self.request_data(token)
            self.assertEqual(initial_user_resp.json, modified_user_resp.json)
