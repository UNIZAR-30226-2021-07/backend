"""
Tests para la creación de usuarios y su gestión.
"""

from gatovid.models import Purchase, Stats

from .base import GatovidTestClient


class UserTest(GatovidTestClient):
    existing_user = {
        "email": "test_user1@gmail.com",
        "name": "test_user1",
        "password": "whatever1",
    }

    def test_signup_empty(self):
        user = {
            "name": "someone",
        }
        data = self.request_signup(user)
        self.assertTrue("error" in data)

    def test_signup_existing_user(self):
        user = {
            "name": "someone",
            "email": self.existing_user["email"],
            "password": "12345678",
        }
        data = self.request_signup(user)
        self.assertTrue("error" in data)

    def test_signup_existing_email(self):
        user = {
            "name": self.existing_user["name"],
            "email": "someone@gmail.com",
            "password": "12345678",
        }
        data = self.request_signup(user)
        self.assertTrue("error" in data)

    def test_signup(self):
        """
        Test básico para la creación de un usuario nuevo.
        """

        user = {
            "name": "someone",
            "email": "someone@gmail.com",
            "password": "12345678",
        }
        data = self.request_signup(user)
        self.assertFalse("error" in data)

        # Un segundo intento fallará
        data = self.request_signup(user)
        self.assertTrue("error" in data)

    def test_remove(self):
        """
        Test básico para comprobar que se elimina un usuario.
        """

        user = {
            "name": "someone",
            "email": "someone@gmail.com",
            "password": "12345678",
        }
        signup_data = self.request_signup(user)
        self.assertFalse("error" in signup_data)

        token_data = self.request_token(user)
        self.assertFalse("error" in token_data)

        # Un inicio de sesión ahora fallará porque ya existe el usuario
        signup_data = self.request_signup(user)
        self.assertTrue("error" in signup_data)

        remove_data = self.request_remove(token_data["access_token"], user)
        self.assertFalse("error" in remove_data)

        # Un inicio de sesión ahora funcionará tras eliminar el usuario
        signup_data = self.request_signup(user)
        self.assertFalse("error" in signup_data)

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

        token_data = self.request_token(self.existing_user)
        self.assertFalse("error" in token_data)

        remove_data = self.request_remove(
            token_data["access_token"], self.existing_user
        )
        self.assertFalse("error" in remove_data)

        # Ahora no existen
        stats = Stats.query.filter_by(user_id=user_id).first()
        self.assertIsNone(stats)
        purchases = Purchase.query.filter_by(user_id=user_id).first()
        self.assertIsNone(purchases)
