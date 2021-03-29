"""
Tests para la creación de usuarios y su gestión.
"""

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
        user = {
            "name": "someone",
            "email": "someone@gmail.com",
            "password": "12345678",
        }
        data = self.request_signup(user)
        self.assertFalse("error" in data)

    def test_remove(self):
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
