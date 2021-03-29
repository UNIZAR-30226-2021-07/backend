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
            "username": "someone",
        }
        data = self.request_signup(user)
        self.assertTrue("error" in data)

    def test_signup_existing_user(self):
        user = {
            "username": "someone",
            "email": self.existing_user["email"],
            "password": "12345678",
        }
        data = self.request_signup(user)
        self.assertTrue("error" in data)

    def test_signup_existing_email(self):
        user = {
            "username": self.existing_user["name"],
            "email": "someone@gmail.com",
            "password": "12345678",
        }
        data = self.request_signup(user)
        self.assertTrue("error" in data)

    def test_signup(self):
        user = {
            "username": "someone",
            "email": "someone@gmail.com",
            "password": "12345678",
        }
        data = self.request_signup(user)
        self.assertFalse("error" in data)

    def test_remove(self):
        user = {
            "username": "someone",
            "email": "someone@gmail.com",
            "password": "12345678",
        }
        data = self.request_signup(user)
        self.assertFalse("error" in data)
