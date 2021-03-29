"""
Tests para la creación de usuarios y su gestión.
"""

import json

from .base import BaseTestCase


def request_signup(client, data):
    response = client.post("/data/signup", data=data)
    return json.loads(response.data.decode())


class UserTest(BaseTestCase):
    existing_user = {
        "email": "test_user1@gmail.com",
        "name": "test_user1",
        "password": "whatever1",
    }

    def test_signup_empty(self):
        user = {
            "username": "someone",
        }
        data = request_signup(self.client, user)
        self.assertTrue("error" in data)

    def test_signup_existing_user(self):
        user = {
            "username": "someone",
            "email": self.existing_user["email"],
            "password": "12345678",
        }
        data = request_signup(self.client, user)
        self.assertTrue("error" in data)

    def test_signup_existing_email(self):
        user = {
            "username": self.existing_user["name"],
            "email": "someone@gmail.com",
            "password": "12345678",
        }
        data = request_signup(self.client, user)
        self.assertTrue("error" in data)

    def test_working(self):
        user = {
            "username": "someone",
            "email": "someone@gmail.com",
            "password": "12345678",
        }
        data = request_signup(self.client, user)
        self.assertFalse("error" in data)
