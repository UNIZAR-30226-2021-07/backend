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

        req = self.request_token(self.user_data)
        self.assertRequestOk(req)
        self.assertIn("access_token", req)

    def test_authorized(self):
        """
        Test a un endpoint protegido con un token válido.
        """

        req = self.request_token(self.user_data)
        self.assertRequestOk(req)
        self.assertIn("access_token", req)

        req = self.token_use(req["access_token"])

        self.assertRequestOk(req)
        self.assertIn("email", req)
        self.assertEqual(req["email"], self.user_data["email"])

    def test_unauthorized(self):
        """
        Test a un endpoint protegido con un token inválido.
        """

        req = self.token_use("a9sd8f7as9d8f")
        self.assertRequestFailed(req)

    def test_revoked(self):
        """
        Test a un endpoint protegido con un token revocado.
        """

        req = self.request_token(self.user_data)
        self.assertRequestOk(req)
        self.assertIn("access_token", req)

        self.revoke_token(req["access_token"])

        req = self.token_use(req["access_token"])
        self.assertRequestFailed(req)
