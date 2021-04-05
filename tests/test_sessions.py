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

        resp = self.request_token(self.user_data)
        self.assertRequestOk(resp)
        self.assertIn("access_token", resp.json)

    def test_authorized(self):
        """
        Test a un endpoint protegido con un token válido.
        """

        resp = self.request_token(self.user_data)
        self.assertRequestOk(resp)
        self.assertIn("access_token", resp.json)

        resp = self.token_use(resp.json["access_token"])

        self.assertRequestOk(resp)
        self.assertIn("email", resp.json)
        self.assertEqual(resp.json["email"], self.user_data["email"])

    def test_unauthorized(self):
        """
        Test a un endpoint protegido con un token inválido.
        """

        req = self.token_use("a9sd8f7as9d8f")
        self.assertRequestErr(req)

    def test_revoked(self):
        """
        Test a un endpoint protegido con un token revocado.
        """

        resp = self.request_token(self.user_data)
        self.assertRequestOk(resp)
        self.assertIn("access_token", resp.json)

        self.revoke_token(resp.json["access_token"])

        resp = self.token_use(resp.json["access_token"])
        self.assertRequestErr(resp)
