"""
Módulo para la inicialización de la base de datos, y la inserción de datos de
prueba.
"""

from sqlalchemy.exc import IntegrityError

from gatovid.app import app
from gatovid.exts import db
from gatovid.models import PurchasableType, Purchase, Stats, User
from gatovid.util import get_logger

logger = get_logger(__name__)


# Usuarios genéricos creados para por ejemplo hacer tests de matchmaking, donde
# se necesitan al menos 6 en total.
NUM_GENERIC_USERS = 10
GENERIC_USERS_EMAIL = "generic_user{0}@gmail.com"
GENERIC_USERS_NAME = "genuser{0}"
GENERIC_USERS_PASSWORD = "12341234"


def db_reset():
    """
    Resetea la base de datos desde cero para poder insertar filas nuevas.
    """

    logger.info("Cleaning database...")
    with app.app_context():
        db.session.commit()
        db.session.remove()
        db.drop_all()
        db.create_all()
    logger.info("Done cleaning database")


def db_test_data():
    """
    Añade datos iniciales a algunas tablas.
    """

    with app.app_context():
        # Se insertan tanto los usuarios personalizados como los genéricos
        users = [
            User(
                email="test_user1@gmail.com",
                name="test_user1",
                password="whatever1",
                coins=133,
            ),
            User(
                email="test_user2@gmail.com",
                name="test_user2",
                password="whatever2",
                coins=10,
            ),
            User(email="test_user3@gmail.com", name="test_user3", password="whatever3"),
        ]
        for i in range(NUM_GENERIC_USERS):
            users.append(
                User(
                    email=GENERIC_USERS_EMAIL.format(i),
                    name=GENERIC_USERS_NAME.format(i),
                    password=GENERIC_USERS_PASSWORD,
                )
            )

        for user in users:
            db.session.add(user)
        db.session.commit()

        # Estadísticas iniciales para cada usuario
        stats = [
            Stats(user_id=users[0].email, playtime_mins=1571),
            Stats(user_id=users[1].email, losses=3, wins=10, playtime_mins=10),
            Stats(user_id=users[2].email, losses=121, wins=3),
        ]
        for stat in stats:
            db.session.add(stat)
        for stat in [
            Stats(user_id=GENERIC_USERS_EMAIL.format(i))
            for i in range(NUM_GENERIC_USERS)
        ]:
            db.session.add(stat)
        db.session.commit()

        # Compras iniciales para cada usuario personalizado
        purchases = [
            # Compras de ítems por defecto
            Purchase(item_id=0, user_id=users[0].email, type=PurchasableType.BOARD),
            Purchase(
                item_id=0, user_id=users[0].email, type=PurchasableType.PROFILE_PIC
            ),
            Purchase(item_id=0, user_id=users[1].email, type=PurchasableType.BOARD),
            Purchase(
                item_id=0, user_id=users[1].email, type=PurchasableType.PROFILE_PIC
            ),
            Purchase(item_id=0, user_id=users[2].email, type=PurchasableType.BOARD),
            Purchase(
                item_id=0, user_id=users[2].email, type=PurchasableType.PROFILE_PIC
            ),
            # Otras compras
            Purchase(item_id=1, user_id=users[0].email, type=PurchasableType.BOARD),
            Purchase(
                item_id=2, user_id=users[0].email, type=PurchasableType.PROFILE_PIC
            ),
            Purchase(item_id=3, user_id=users[1].email, type=PurchasableType.BOARD),
        ]
        for purchase in purchases:
            db.session.add(purchase)
        db.session.commit()


def db_init():
    try:
        logger.info("Generating fake data...")
        db_test_data()
        logger.info("Generation of fake data done")
    except IntegrityError:
        logger.info("Generation of fake data skipped, initialization already done")
