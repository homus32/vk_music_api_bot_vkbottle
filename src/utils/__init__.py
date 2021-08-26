from datetime import datetime
from typing import Union

from vkbottle.bot import rules, Message
from vkbottle import GroupTypes
from random import choice, randint
from string import ascii_letters, digits

from config import Groups, Config, redis_db as r
from .orm import *

ALLOWED_CHARS = ascii_letters + digits + "!#*^_."


def get_user_info(user_id):
    info = {
        "group": Groups.NOT_REG,
    }

    with db_session:
        db_user_info = User.get(id=user_id)

        if db_user_info is not None:
            info["steam_id"] = str(int(db_user_info.steamid64))
            info["create_date"] = db_user_info.create_date.isoformat()

            db_key_info = Key.get(id=user_id)

            if db_key_info is not None:

                if (
                        db_key_info.expiration_date is not None
                        and
                        datetime.now(timezone_msk) >= db_key_info.expiration_date
                ):
                    info["group"] = Groups.REG_EXPIRED_KEY
                else:
                    info["group"] = Groups.REG_WITH_KEY

                if db_key_info.expiration_date is None:
                    info["endless"] = 1
                else:
                    info["expiration_date"] = db_key_info.expiration_date.isoformat()

                if db_key_info.key is not None:
                    info["key"] = db_key_info.key
            else:
                info["group"] = Groups.REG_WITHOUT_KEY

    if user_id in Config.admin:
        info["admin"] = 1

    return info


def get_user_promocodes(user_id):
    with db_session:
        return tuple(p.promocode for p in Promocode.select(lambda p: p.user == User[user_id]))


class WithoutStateRule(rules.ABCMessageRule):

    async def check(self, message: Message):
        if message.state_peer is None:
            return True
        return False


class WithoutPayloadRule(rules.ABCMessageRule):

    async def check(self, message: Message):
        return message.get_payload_json() is None


class GroupRule(rules.ABCMessageRule):

    def __init__(self, group_id):
        if isinstance(group_id, str) or isinstance(group_id, int):
            group_id = (group_id,)

        self.group = group_id

    async def check(self, message: Union[Message, GroupTypes.MessageEvent]):
        try:
            user_id = message.peer_id
        except AttributeError:
            user_id = message.object.peer_id

        db_info = r.hgetall("{}_info".format(user_id))

        return db_info.get("group") in self.group


class AdminRule(rules.ABCMessageRule):

    async def check(self, message: Message):
        db_info = r.hgetall("{}_info".format(message.peer_id))
        return True if db_info.get("admin") is not None else False


class EventPayloadRule(rules.ABCMessageRule):

    def __init__(self, payload):
        if isinstance(payload, dict):
            payload = [payload]
        self.payload = payload

    async def check(self, event):
        return event.object.payload in self.payload


def declension_date(date):
    if date == 0:
        return "навсегда"

    num = int(date[-2:-1])
    date_type = date[-1]

    dates = {
        "d": ["день", "дня", "дней"],
        "m": ["месяц", "месяца", "месяцев"],
        "y": ["год", "года", "лет"]
    }

    if num == 1:
        return dates[date_type][0]

    elif 2 <= num <= 4:
        return dates[date_type][1]

    return dates[date_type][2]


def generate_password():
    password = ""
    for i in range(randint(12, 21)):
        password += choice(ALLOWED_CHARS)

    return password


def password_valid(password):
    if len(password) > 50:
        return False

    for char in password:
        if char not in ALLOWED_CHARS:
            return False

    return True


def date_to_days(date):
    if date == 0:
        return 0

    num = int(date[:-1])
    date_type = date[-1]

    if date_type == "d":
        return num

    elif date_type == "m":
        return num * 31

    elif date_type == "y":
        return num * 365
