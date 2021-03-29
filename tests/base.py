import json

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

    def request_token(self, data):
        response = self.client.post("/data/login", data=data)
        return json.loads(response.data.decode())

    def revoke_token(self, token):
        response = self.client.post(
            "/data/logout",
            headers={"Authorization": "Bearer " + token},
        )
        return json.loads(response.data.decode())

    def token_use(self, token):
        response = self.client.post(
            "/data/protected_test",
            headers={"Authorization": "Bearer " + token},
        )
        return json.loads(response.data.decode())

    def request_signup(self, data):
        response = self.client.post("/data/signup", data=data)
        return json.loads(response.data.decode())
