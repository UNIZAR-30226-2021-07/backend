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

    def test_signup_empty(self):
        user = {"name": self.new_user["name"]}
        data = self.request_signup(user)
        self.assertTrue("error" in data)

    def test_signup_existing_user(self):
        user = {
            "name": self.new_user["name"],
            "email": self.existing_user["email"],
            "password": self.new_user["password"],
        }
        data = self.request_signup(user)
        self.assertTrue("error" in data)

    def test_signup_existing_email(self):
        user = {
            "name": self.existing_user["name"],
            "email": self.new_user["email"],
            "password": self.new_user["password"],
        }
        data = self.request_signup(user)
        self.assertTrue("error" in data)

    def test_signup(self):
        """
        Test básico para la creación de un usuario nuevo.
        """

        data = self.request_signup(self.new_user)
        self.assertFalse("error" in data)

        # Un segundo intento fallará
        data = self.request_signup(self.new_user)
        self.assertTrue("error" in data)

    def test_unique(self):
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
        self.assertFalse("error" in signup_data)

        token_data = self.request_token(self.new_user)
        self.assertFalse("error" in token_data)

        # Un inicio de sesión ahora fallará porque ya existe el usuario
        signup_data = self.request_signup(self.new_user)
        self.assertTrue("error" in signup_data)

        remove_data = self.request_remove(token_data["access_token"], self.new_user)
        self.assertFalse("error" in remove_data)

        # Un registro ahora funcionará tras eliminar el usuario
        signup_data = self.request_signup(self.new_user)
        self.assertFalse("error" in signup_data)

    def test_repeated_remove(self):
        """
        Probando si reusando el mismo token se puede borrar dos veces el mismo
        usuario, y si causa problemas en ese caso.
        """

        token_data = self.request_token(self.existing_user)
        self.assertFalse("error" in token_data)

        # Primer intento
        remove_data = self.request_remove(token_data["access_token"], self.new_user)
        self.assertFalse("error" in remove_data)

        # Segundo intento
        remove_data = self.request_remove(token_data["access_token"], self.new_user)
        self.assertTrue("error" in remove_data)

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
        self.assertFalse("error" in token_data)

        # Y eliminación del usuario
        remove_data = self.request_remove(
            token_data["access_token"], self.existing_user
        )
        self.assertFalse("error" in remove_data)

        # Ahora no existen
        stats = Stats.query.filter_by(user_id=user_id).first()
        self.assertIsNone(stats)
        purchases = Purchase.query.filter_by(user_id=user_id).first()
        self.assertIsNone(purchases)
