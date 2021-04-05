import json
from typing import Dict
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

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

    def assertRequestFailed(self, data):
        self.assertIn("error", data)

    def assertRequestOk(self, data):
        self.assertNotIn("error", data)


class GatovidTestClient(BaseTestCase):
    """
    Clase para realizar tests, extendida con un cliente HTTP para realizar
    peticiones desde cualquier test de forma sencilla.
    """

    def request(
        self,
        url: str,
        data: Dict[str, str] = None,
        headers: Dict[str, str] = None,
        method: str = "GET",
    ) -> Dict[str, str]:
        """
        Petición genérica al API de Gatovid
        """

        if method == "GET":
            # Se añaden los parámetros de `data` a los de la URL
            if data is not None:
                url_parts = list(urlparse(url))
                query = dict(parse_qsl(url_parts[4]))
                query.update(data)
                url_parts[4] = urlencode(query)
                url = urlunparse(url_parts)

            response = self.client.get(url, headers=headers)
        elif method == "POST":
            response = self.client.post(url, data=data, headers=headers)
        else:
            raise Exception("not supported")

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

    def request_stats(self, name: str) -> Dict[str, str]:
        return self.request("/data/user_stats", data={"name": name})

    def request_data(self, token: str) -> Dict[str, str]:
        return self.request("/data/user_data", headers=self.auth_headers(token))
