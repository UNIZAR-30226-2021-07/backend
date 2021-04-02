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

    def test_data(self):
        """
        Test para el endpoint de los datos del usuario.
        """

        expected = {
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

        token_data = self.request_token(self.existing_user)
        self.assertNotIn("error", token_data)

        token = token_data["access_token"]

        got = self.request_data(token)

        self.assertEqual(got, expected)

    def test_stats(self):
        """
        Test para el endpoint de las estadísticas.
        """

        test_stats = {
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

        for name, expected in test_stats.items():
            got = self.request_stats(name)
            self.assertEqual(got, expected)

    def test_signup_empty(self):
        """
        Test para valores tanto vacíos como no incluidos en los datos.
        """

        for field in ("name", "email", "password"):
            user = self.new_user.copy()

            user[field] = ""
            data = self.request_signup(user)
            self.assertIn("error", data)

            del user[field]
            data = self.request_signup(user)
            self.assertIn("error", data)

    def test_signup_existing_user(self):
        """
        Los nombres de usuario son únicos.
        """

        user = {
            "name": self.new_user["name"],
            "email": self.existing_user["email"],
            "password": self.new_user["password"],
        }
        data = self.request_signup(user)
        self.assertIn("error", data)

    def test_signup_existing_email(self):
        """
        Los email también son únicos.
        """

        user = {
            "name": self.existing_user["name"],
            "email": self.new_user["email"],
            "password": self.new_user["password"],
        }
        data = self.request_signup(user)
        self.assertIn("error", data)

    def test_signup(self):
        """
        Test básico para la creación de un usuario nuevo.
        """

        data = self.request_signup(self.new_user)
        self.assertNotIn("error", data)

        # Un segundo intento fallará
        data = self.request_signup(self.new_user)
        self.assertIn("error", data)

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

                data = self.request_signup(test_user)
                if should_work:
                    self.assertNotIn("error", data)
                else:
                    self.assertIn("error", data)

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

                data = self.request_signup(test_user)
                if should_work:
                    self.assertNotIn("error", data)
                else:
                    self.assertIn("error", data)

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

        signup_data = self.request_signup(self.new_user)
        self.assertNotIn("error", signup_data)

        token_data = self.request_token(self.new_user)
        self.assertNotIn("error", token_data)

        # Un inicio de sesión ahora fallará porque ya existe el usuario
        signup_data = self.request_signup(self.new_user)
        self.assertIn("error", signup_data)

        remove_data = self.request_remove(token_data["access_token"], self.new_user)
        self.assertNotIn("error", remove_data)

        # Un registro ahora funcionará tras eliminar el usuario
        signup_data = self.request_signup(self.new_user)
        self.assertNotIn("error", signup_data)

    def test_repeated_remove(self):
        """
        Probando si reusando el mismo token se puede borrar dos veces el mismo
        usuario, y si causa problemas en ese caso.
        """

        token_data = self.request_token(self.existing_user)
        self.assertNotIn("error", token_data)

        # Primer intento
        remove_data = self.request_remove(token_data["access_token"], self.new_user)
        self.assertNotIn("error", remove_data)

        # Segundo intento
        remove_data = self.request_remove(token_data["access_token"], self.new_user)
        self.assertIn("error", remove_data)

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
        token_data = self.request_token(self.existing_user)
        self.assertNotIn("error", token_data)

        # Y eliminación del usuario
        remove_data = self.request_remove(
            token_data["access_token"], self.existing_user
        )
        self.assertNotIn("error", remove_data)

        # Ahora no existen
        stats = Stats.query.filter_by(user_id=user_id).first()
        self.assertIsNone(stats)
        purchases = Purchase.query.filter_by(user_id=user_id).first()
        self.assertIsNone(purchases)
