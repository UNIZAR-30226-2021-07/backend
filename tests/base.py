from flask_testing import TestCase

from gatovid.app import app
from gatovid.create_db import db_reset, db_test_data
from gatovid.exts import db


class BaseTestCase(TestCase):
    """ Base Tests """

    def create_app(self):
        app.config.from_object('gatovid.config.TestingConfig')
        return app

    def setUp(self):
        db_reset()
        db_test_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
