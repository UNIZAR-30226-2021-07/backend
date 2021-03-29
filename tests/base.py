import json
from typing import Dict

from flask_testing import TestCase

from gatovid.app import app
from gatovid.create_db import db_reset, db_test_data
from gatovid.exts import db


class BaseTestCase(TestCase):
    """
    Clase básica para realizar tests con Flask y la base de datos.
    """

    def create_app(self):
        app.config.from_object("gatovid.config.TestingConfig")
        return app

    def setUp(self):
        db_reset()
        db_test_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()


class GatovidTestClient(BaseTestCase):
    """
    Clase para realizar tests, extendida con un cliente HTTP para realizar
    peticiones desde cualquier test de forma sencilla.
    """

    def request(
        self, url: str, data: Dict[str, str] = None, headers: Dict[str, str] = None
    ) -> Dict[str, str]:
        """
        Petición genérica
        """

        response = self.client.post(url, data=data, headers=headers)
        return json.loads(response.data.decode())

    def auth_headers(self, token: str) -> Dict[str, str]:
        return {"Authorization": "Bearer " + token}

    def request_token(self, data: Dict[str, str]) -> Dict[str, str]:
        return self.request("/data/login", data=data)

    def revoke_token(self, token: str) -> Dict[str, str]:
        return self.request("/data/logout", headers=self.auth_headers(token))

    def token_use(self, token: str) -> Dict[str, str]:
        return self.request("/data/protected_test", headers=self.auth_headers(token))

    def request_signup(self, data: Dict[str, str]) -> Dict[str, str]:
        return self.request("/data/signup", data=data)

    def request_remove(self, token: str, data: Dict[str, str]) -> Dict[str, str]:
        return self.request(
            "/data/remove_user", data=data, headers=self.auth_headers(token)
        )
