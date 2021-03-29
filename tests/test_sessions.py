"""
Tests para la administración de tokens JWT y sus sesiones.
"""

import json

from .base import BaseTestCase


def request_token(client, data):
    response = client.post("/data/login", data=data)
    return json.loads(response.data.decode())


def revoke_token(client, token):
    response = client.post(
        "/data/logout",
        headers={"Authorization": "Bearer " + token},
    )
    return json.loads(response.data.decode())


def token_use(client, token):
    response = client.post(
        "/data/protected_test",
        headers={"Authorization": "Bearer " + token},
    )
    return json.loads(response.data.decode())


class SessionsTest(BaseTestCase):
    user_data = {
        "email": "test_user1@gmail.com",
        "password": "whatever1",
    }

    def test_create_token(self):
        data = request_token(self.client, self.user_data)

        self.assertFalse("error" in data)
        self.assertTrue("access_token" in data)

        self.token = data["access_token"]

    def test_authorized(self):
        data = request_token(self.client, self.user_data)
        self.assertTrue("access_token" in data)

        data = token_use(self.client, data["access_token"])

        self.assertFalse("error" in data)
        self.assertTrue("email" in data)
        self.assertEqual(data["email"], self.user_data["email"])

    def test_unauthorized(self):
        data = token_use(self.client, "a9sd8f7as9d8f")
        self.assertTrue("error" in data)

    def test_revoked(self):
        data = request_token(self.client, self.user_data)
        self.assertTrue("access_token" in data)

        revoke_token(self.client, data["access_token"])

        data = token_use(self.client, data["access_token"])
        self.assertTrue("error" in data)
