from datetime import datetime, timedelta

from vkbottle import BaseStateGroup

from admin import COMMAND_SYNTAX, Message, WithoutPayloadRule, parse_text, get_user_by_text, bp
from admin import enum_array
from keyboards import ADMIN_KEYS_KEYBOARD, ADMIN_BACK_BUTTON_KEYBOARD
from config import redis_vk_music_db as r_api, redis_db as r, MONTH_NAMES
from utils.orm import *


class AdminKeys(BaseStateGroup):
    CHANGE_USER_KEY_STATE = 40
    CREATE_IND_KEY = 41
    DEL_IND_KEY = 42


@bp.on.private_message(payload={"admin": "keys"})
async def send_admin_keys_keyboard(message: Message):
    await message.answer(
        "Категория: ключи пользователей и независемые ключи",
        keyboard=ADMIN_KEYS_KEYBOARD
    )


@bp.on.private_message(payload={"admin": "change_key_value"})
async def change_user_key_state(message: Message):
    await bp.state_dispenser.set(message.peer_id, AdminKeys.CHANGE_USER_KEY_STATE)
    await message.answer(
        "Напишите в чат steam или vk IDs или key пользователя. Потом "
        "напишите new_key <new_key>. Если просто написать new_key то ключ "
        "удалится. А если хотите вообще удалить ключ из бд то напишите просто "
        "remove_key" + COMMAND_SYNTAX,
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


@bp.on.private_message(WithoutPayloadRule(), state=AdminKeys.CHANGE_USER_KEY_STATE)
async def get_remove_user(message: Message):
    text = parse_text(message.text)
    new_key = None
    remove_key = False

    if "new_key" in text:
        new_key = text["new_key"]
    else:
        if "remove_key" not in text:
            return "Вы забыли написать new_key"
        else:
            remove_key = True

    with db_session:
        user = get_user_by_text(text)

        if user is not None:
            key = Key.get(id=user.id)
            if key is not None:
                if not remove_key:
                    if new_key is None:
                        r_api.srem("keys", key.key if key.key is not None else "")
                        r.delete("{}_info".format(user.id))
                        key.key = None
                        return "Успешно удален ключ у пользователя {}".format(user.id)
                    else:
                        r_api.srem("keys", key.key if key.key is not None else "")
                        r_api.sadd("keys", new_key)
                        r.delete("{}_info".format(user.id))
                        key.key = str(new_key)
                        return "Успешно изменен ключ у пользователя {}".format(user.id)
                else:
                    r_api.srem("keys", key.key if key.key is not None else "")
                    r.delete("{}_info".format(user.id))
                    Key.delete(key)
                    return "Вы успешно напрочь удалили ключ пользователя {}".format(user.id)
            else:
                return "У пользователя нету ключа."
        else:
            "Пользователь не найден."


@bp.on.private_message(payload={"admin": "del_ind_key"})
async def del_ind_key_state(message: Message):
    with db_session:
        ind_keys = tuple(p.key for p in Independent_key.select())
        keys = enum_array(ind_keys)

    if keys == "":
        keys = "*тут ничего нет, уходи отсюдава*"

    await bp.state_dispenser.set(message.peer_id, AdminKeys.DEL_IND_KEY, keys=ind_keys)
    await message.answer(
        "Выберите индекс из списка, чтобы удалить ключ:\n" + keys,
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


@bp.on.private_message(WithoutPayloadRule(), state=AdminKeys.DEL_IND_KEY)
async def get_del_ind_key(message: Message):
    num = message.text.split()[0]
    keys = message.state_peer.payload["keys"]

    if len(keys) == 0:
        return "Я же сказал, нету ничего здесь..."

    if num.isdigit():
        num = int(num) - 1
        if 0 <= int(num) <= len(keys):
            with db_session:
                key = Independent_key.get(key=keys[num])
                r_api.srem("keys", key.key)
                Independent_key.delete(key)
                return "Удалил. Можно идти назад."
        else:
            return "INDEX OUT OF RANGE. Проверьте цифру"
    else:
        return "Вы ввели не цифру"


@bp.on.private_message(payload={"admin": "create_ind_key"})
async def create_ind_key_state(message: Message):
    await bp.state_dispenser.set(message.peer_id, AdminKeys.CREATE_IND_KEY)
    await message.answer(
        "Напишите в чат key <значение> и days <кол-во дней>. 0 -- значит навсегда" + COMMAND_SYNTAX,
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


@bp.on.private_message(WithoutPayloadRule(), state=AdminKeys.CREATE_IND_KEY)
async def get_create_ind_key(message: Message):
    text = parse_text(message.text)
    key = None
    days = None

    if "key" in text:
        key = text["key"]

    if "days" in text:
        days = text["days"]

        if not isinstance(days, int):
            return "days не является числом. Проверьте значение"

    if key is not None and days is not None:
        with db_session:

            if not Key.exists(key=key) and not Independent_key.exists(key=key):
                if days == 0:
                    days = None
                else:
                    days = datetime.now(timezone_msk) + timedelta(days=days)

                Independent_key(
                    key=key,
                    expiration_date=days
                )

                r_api.sadd("keys", key)
                return "Ключ успешно создан"
            else:
                return "Ключ уже создан!"
    else:
        return "Вы не указали key или days"


@bp.on.private_message(payload={"admin": "ind_keys_list"})
async def send_ind_keys_list(_):
    msg_text = "Вот список всех независимых ключей:\n"

    with db_session:
        for num, key in enumerate(Independent_key.select()):

            if key.expiration_date is None:
                expiration_date = "никогда"
            else:
                date = key.expiration_date
                expiration_date = "{} {}, {} года. В {}:{}:{} по МСК ".format(
                    date.day,
                    MONTH_NAMES[date.month],
                    date.year,
                    date.hour,
                    date.minute,
                    date.second
                )

                if datetime.now(timezone_msk) >= date:
                    expiration_date += "(уже просрочен)"

            msg_text += "{}. {} -- {}\n".format(num + 1, key.key, expiration_date)

    return msg_text


@bp.on.private_message(state_group=AdminKeys, payload={"admin": "back"})
async def back_to_admin_keys_keyboard(message: Message):
    await bp.state_dispenser.delete(message.peer_id)
    await send_admin_keys_keyboard(message)
