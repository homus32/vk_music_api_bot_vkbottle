from datetime import datetime, timedelta
from vkbottle import BaseStateGroup

from keyboards import ADMIN_TERM_CONTROL_KEYBOARD, ADMIN_CHANGE_PROMOCODES_KEYBOARD
from keyboards import ADMIN_BACK_BUTTON_KEYBOARD
from admin import COMMAND_SYNTAX, WithoutPayloadRule, Message, parse_text, get_user_by_text, bp
from admin import enum_array
from config import redis_vk_music_db as r_api, redis_db as r, Config
from utils import get_user_promocodes
from utils.orm import *


class AdminTerm(BaseStateGroup):
    SET_TARIFF_STATE = 30
    EXTEND_TARIFF_STATE = 31
    PROMOCODE_STATE = 32
    PROMOCODE_ADD_STATE = 33
    PROMOCODE_DEL_STATE = 34


def isdigit(num: str):
    if num.isdigit() or num[1:].isdigit():
        return True
    return False


@bp.on.private_message(payload={"admin": "term_control"})
async def send_admin_term_keyboard(message: Message):
    await message.answer(
        "Категория: тарифы и промокоды",
        keyboard=ADMIN_TERM_CONTROL_KEYBOARD
    )


@bp.on.private_message(payload={"admin": "set_user_tariff"})
async def set_user_tariff_state(message: Message):
    await bp.state_dispenser.set(message.peer_id, AdminTerm.SET_TARIFF_STATE)
    await message.answer(
        "Напишите steam или vk IDs и days <кол-во дней>. 0 -- значит навсегда. "
        "-<кол-во дней> сделать пользователю просроченный ключ на кол-во дней" + COMMAND_SYNTAX,
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


@bp.on.private_message(WithoutPayloadRule(), state=AdminTerm.SET_TARIFF_STATE)
async def get_user_set_tariff(message: Message):
    text = parse_text(message.text)

    with db_session:
        user = get_user_by_text(text)
        if user is not None:

            if "days" in text and isdigit(str(text["days"])):
                days = int(text["days"])

                if not Key.exists(id=user.id):
                    Key(id=user.id, key=None, expiration_date=None)

                key = Key[user.id]

                if days == 0:
                    key.expiration_date = None
                else:
                    key.expiration_date = datetime.now(timezone_msk) + timedelta(days=days)

                    if days < 0 and key.key is not None:
                        r_api.srem("keys", key.key)

                r.delete("{}_info".format(user.id))
                return "Тариф пользователя {} изменен!".format(user.id)

            else:
                return "Кол-во дней указано неправильно. Проверьте значение."
        else:
            return "Пользователь не найден"


@bp.on.private_message(payload={"admin": "extend_user_tariff"})
async def extend_user_tariff_state(message: Message):
    await bp.state_dispenser.set(message.peer_id, AdminTerm.EXTEND_TARIFF_STATE)
    await message.answer(
        "Напишите steam или vk IDs и days <кол-во дней>." + COMMAND_SYNTAX,
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


@bp.on.private_message(WithoutPayloadRule(), state=AdminTerm.EXTEND_TARIFF_STATE)
async def get_extend_user_tariff(message: Message):
    text = parse_text(message.text)

    with db_session:
        user = get_user_by_text(text)
        if user is not None:

            if "days" in text and isinstance(text["days"], int):
                days = text["days"]

                key = Key.get(id=user.id)

                if key is not None:
                    if key.expiration_date is not None:
                        key.expiration_date += timedelta(days=days)
                        r.delete("{}_info".format(user.id))

                        return "Операция прошла успешно! " \
                               "Вы добавили {} day(s) пользователю {}".format(days, user.id)
                    else:
                        return "У этого пользователя вечный ключ!"
                else:
                    return "У этого пользователя нету ключа."
            else:
                return "Кол-во дней указано неправильно. Проверьте значение."
        else:
            return "Пользователь не найден"


@bp.on.private_message(payload={"admin": "change_user_promocodes"})
async def change_user_promocodes_state(message: Message):
    await bp.state_dispenser.set(message.peer_id, AdminTerm.PROMOCODE_STATE)
    await message.answer(
        "Напишите steam или vk IDs или key" + COMMAND_SYNTAX,
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


@bp.on.private_message(WithoutPayloadRule(), state=AdminTerm.PROMOCODE_STATE)
async def get_user_for_promocode(message: Message):
    text = parse_text(message.text)

    with db_session:
        user = get_user_by_text(text)
        if user is not None:
            await bp.state_dispenser.set(message.peer_id, AdminTerm.PROMOCODE_STATE, user=user)
            await message.answer(
                "Выберите дейсвие из клавиатуры",
                keyboard=ADMIN_CHANGE_PROMOCODES_KEYBOARD
            )
        else:
            return "Пользователь не найден."


@bp.on.private_message(state=AdminTerm.PROMOCODE_STATE, payload={"admin": "add_prom_mode"})
async def add_prom_state(message: Message):
    payload = message.state_peer.payload
    payload.update(promocodes=Config.promocode)

    await bp.state_dispenser.set(message.peer_id, AdminTerm.PROMOCODE_ADD_STATE, **payload)
    promocodes = enum_array(payload["promocodes"])

    if promocodes == "":
        promocodes = "*пусто, тут нечего добавлять*"

    await message.answer(
        message="Выберите, какой промокод добавить пользователю.\n" + promocodes
                + "\nНапишите цифру в чат",
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


@bp.on.private_message(state=AdminTerm.PROMOCODE_STATE, payload={"admin": "del_prom_mode"})
async def del_prom_state(message: Message):
    payload = message.state_peer.payload
    payload.update(promocodes=get_user_promocodes(payload["user"].id))

    await bp.state_dispenser.set(message.peer_id, AdminTerm.PROMOCODE_DEL_STATE, **payload)
    promocodes = enum_array(payload["promocodes"])

    if promocodes == "":
        promocodes = "*пусто, тут нечего удалять*"

    await message.answer(
        message="Выберите, какой промокод удалить пользователю.\n" + promocodes
                + "\nНапишите цифру в чат",
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


def prom_check(message: Message):
    num = message.text.split()[0]
    promocodes = message.state_peer.payload["promocodes"]
    if isinstance(promocodes, dict):
        promocodes = tuple(message.state_peer.payload["promocodes"].keys())

    user = message.state_peer.payload["user"]

    if num.isdigit():
        num = int(num) - 1
        if 0 <= int(num) <= len(promocodes):
            return promocodes[num], user
        else:
            return "INDEX OUT OF RANGE. Проверьте цифру"
    else:
        return "Вы ввели не цифру"


@bp.on.private_message(WithoutPayloadRule(), state=AdminTerm.PROMOCODE_ADD_STATE)
async def get_prom_add(message: Message):
    check = prom_check(message)
    if isinstance(check, tuple):
        with db_session:
            promocode, user = check

            if not Promocode.exists(user=user.id, promocode=promocode):
                Promocode(user=user.id, promocode=promocode)
                return "Успешно добавил промокод {} пользователю {}".format(promocode, user.id)
            else:
                return "Этот промокод уже есть у пользователя"
    else:
        return check


@bp.on.private_message(WithoutPayloadRule(), state=AdminTerm.PROMOCODE_DEL_STATE)
async def get_prom_del(message: Message):
    check = prom_check(message)
    if isinstance(check, tuple):
        with db_session:
            promocode, user = check
            db_promocode = Promocode.get(user=user.id, promocode=promocode)
            Promocode.delete(db_promocode)
            return "Успешно удален промокод {} у пользователя {}".format(promocode, user.id)
    else:
        return check


@bp.on.private_message(state_group=AdminTerm, payload={"admin": "back"})
async def back_to_admin_term_keyboard(message: Message):
    await bp.state_dispenser.delete(message.peer_id)
    await send_admin_term_keyboard(message)

