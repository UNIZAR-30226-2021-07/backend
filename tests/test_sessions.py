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
        """
        Test básico para la creación de un token.
        """

        data = self.request_token(self.user_data)

        self.assertNotIn("error", data)
        self.assertIn("access_token", data)

        self.token = data["access_token"]

    def test_authorized(self):
        """
        Test a un endpoint protegido con un token válido.
        """

        data = self.request_token(self.user_data)
        self.assertIn("access_token", data)

        data = self.token_use(data["access_token"])

        self.assertNotIn("error", data)
        self.assertIn("email", data)
        self.assertEqual(data["email"], self.user_data["email"])

    def test_unauthorized(self):
        """
        Test a un endpoint protegido con un token inválido.
        """

        data = self.token_use("a9sd8f7as9d8f")
        self.assertIn("error", data)

    def test_revoked(self):
        """
        Test a un endpoint protegido con un token revocado.
        """

        data = self.request_token(self.user_data)
        self.assertIn("access_token", data)

        self.revoke_token(data["access_token"])

        data = self.token_use(data["access_token"])
        self.assertIn("error", data)
