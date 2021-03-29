"""
Tests para la administración de tokens JWT y sus sesiones.
"""

from .base import GatovidTestClient


class SessionsTest(GatovidTestClient):
    user_data = {
        "email": "test_user1@gmail.com",
        "password": "whatever1",
    }

    def test_create_token(self):
        data = self.request_token(self.user_data)

        self.assertFalse("error" in data)
        self.assertTrue("access_token" in data)

        self.token = data["access_token"]

    def test_authorized(self):
        data = self.request_token(self.user_data)
        self.assertTrue("access_token" in data)

        data = self.token_use(data["access_token"])

        self.assertFalse("error" in data)
        self.assertTrue("email" in data)
        self.assertEqual(data["email"], self.user_data["email"])

    def test_unauthorized(self):
        data = self.token_use("a9sd8f7as9d8f")
        self.assertTrue("error" in data)

    def test_revoked(self):
        data = self.request_token(self.user_data)
        self.assertTrue("access_token" in data)

        self.revoke_token(data["access_token"])

        data = self.token_use(data["access_token"])
        self.assertTrue("error" in data)
