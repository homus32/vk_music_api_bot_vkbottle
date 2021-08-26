from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from pony.orm import *

from config import Config

db = Database()
db.bind(provider='postgres', user='user', password=Config.settings["pgsql_password"],
        host='localhost', database='example_db')

timezone_msk = timezone(timedelta(hours=3))


class User(db.Entity):
    id = PrimaryKey(int)
    steamid64 = Required(Decimal, precision=24, scale=1, unique=True)
    create_date = Optional(date)
    keys = Set('Key', cascade_delete=True)
    promocodes = Set('Promocode', cascade_delete=True)


class Key(db.Entity):
    id = PrimaryKey(User)
    key = Optional(str, 50, nullable=True)
    expiration_date = Optional(datetime, volatile=True)


# noinspection PyPep8Naming
class Independent_key(db.Entity):
    key = Required(str, 50, nullable=False)
    expiration_date = Optional(datetime, volatile=True)


class Promocode(db.Entity):
    id = PrimaryKey(int, auto=True)
    user = Required(User)
    promocode = Required(str, 50)


db.generate_mapping()

__all__ = (
    "db",
    "db_session",
    "User",
    "Key",
    "Independent_key",
    "Promocode",
    "timezone_msk",
)
