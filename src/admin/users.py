from datetime import datetime
from dateutil.parser import parse
from vkbottle import BaseStateGroup

from admin import COMMAND_SYNTAX, Message, WithoutPayloadRule, parse_text, get_user_by_text, bp
from keyboards import ADMIN_USER_KEYBOARD, ADMIN_BACK_BUTTON_KEYBOARD
from config import redis_vk_music_db as r_api, redis_db as r, GROUPS_STR, MONTH_NAMES
from utils import get_user_info as db_get_user_info, get_user_promocodes
from utils.orm import *


class AdminUser(BaseStateGroup):
    DEL_USER_STATE = 20
    REG_USER_STATE = 21
    CHANGE_USER_STATE = 22
    INFO_USER_STATE = 23


@bp.on.private_message(payload={"admin": "user"})
async def send_admin_user_keyboard(message: Message):
    await message.answer(
        "Категория: пользователи",
        keyboard=ADMIN_USER_KEYBOARD
    )


@bp.on.private_message(payload={"admin": "remove_user"})
async def del_user_state(message: Message):
    await bp.state_dispenser.set(message.peer_id, AdminUser.DEL_USER_STATE)
    await message.answer(
        "Напишите в чат steam или vk IDs или key пользователя" + COMMAND_SYNTAX,
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


@bp.on.private_message(WithoutPayloadRule(), state=AdminUser.DEL_USER_STATE)
async def get_remove_user(message: Message):
    text = parse_text(message.text)

    with db_session:
        user = get_user_by_text(text)

        if user is not None:
            key = Key.get(id=user)

            if key is not None and key.key is not None:
                r_api.srem("keys", key.key)

            r.delete("{}_info".format(user.id))
            User.delete(user)

            return "Пользователь с vk_id {} успешно удален!".format(user.id)
        else:
            return "Пользоавтель не найден"


@bp.on.private_message(payload={"admin": "reg_user"})
async def reg_user_state(message: Message):
    await bp.state_dispenser.set(message.peer_id, AdminUser.REG_USER_STATE)
    await message.answer(
        "Напишите в чат vk и steam IDs нового пользователя" + COMMAND_SYNTAX,
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


@bp.on.private_message(WithoutPayloadRule(), state=AdminUser.REG_USER_STATE)
async def get_reg_user(message: Message):
    text = parse_text(message.text)
    vk = None
    steam = None

    if "vk" in text and isinstance(text["vk"], int):
        vk = text["vk"]

    if "steam" in text and isinstance(text["steam"], int):
        steam = text["steam"]

    if vk is not None and steam is not None:

        with db_session:
            if not User.exists(id=vk) and not User.exists(steamid64=steam):
                if isinstance(steam, int) and str(steam).startswith("7656119"):
                    if isinstance(vk, int):
                        User(id=vk, steamid64=steam)

                        r.delete("{}_info".format(vk))
                        return "Пользователь успешно создан!"
                    else:
                        return "Неверно указан vk ID. Проверьте его"
                else:
                    return "SteamID64 неверный! Проверьте его."
            else:
                return "Этот пользователь уже создан!"
    else:
        return "Вы что-то не указали"


@bp.on.private_message(payload={"admin": "change_info_user"})
async def change_user_state(message: Message):
    await bp.state_dispenser.set(message.peer_id, AdminUser.CHANGE_USER_STATE)
    await message.answer(
        "Напишите в чат vk или steam IDs или key пользователя. "
        "Потом напишите new_steam или new_vk или одновременно new_steam "
        "и new_vk. Пример: vk 360089815 new_steam 76561198801143366" + COMMAND_SYNTAX,
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


@bp.on.private_message(WithoutPayloadRule(), state=AdminUser.CHANGE_USER_STATE)
async def get_change_user(message: Message):
    text = parse_text(message.text)
    new_steam = None
    new_vk = None

    if "new_steam" in text:
        new_steam = text["new_steam"]

    if "new_vk" in text:
        new_vk = text["new_vk"]

    if new_steam is None and new_vk is None:
        return "Вы не указали new_vk или new_steam"

    with db_session:
        user = get_user_by_text(text)

        if user is not None:

            msg_text = "Пользователь с vk_old {} успешно обновился на "

            if new_steam is not None:
                old_id = int(user.id)

                if new_vk is not None:
                    if isinstance(new_vk, int):
                        user.id = new_vk
                        msg_text += "vk: {} ".format(new_vk)
                    else:
                        return "Неверно указан new_vk"

                if new_steam is not None:
                    if isinstance(new_steam, int) and str(new_steam).startswith("7656119"):
                        user.steamid64 = new_steam
                        msg_text += "steam: {} ".format(new_steam)
                    else:
                        return "Неверно указан new_steam"

            r.delete("{}_info".format(old_id))
            return msg_text.format(old_id)
        else:
            return "Пользоавтель не найден"


@bp.on.private_message(payload={"admin": "user_info"})
async def info_user_state(message: Message):
    await bp.state_dispenser.set(message.peer_id, AdminUser.INFO_USER_STATE)
    await message.answer(
        "Напишите в чат vk или steam IDs или key" + COMMAND_SYNTAX,
        keyboard=ADMIN_BACK_BUTTON_KEYBOARD
    )


@bp.on.private_message(WithoutPayloadRule(), state=AdminUser.INFO_USER_STATE)
async def get_info_user(message: Message):
    text = parse_text(message.text)

    with db_session:
        user = get_user_by_text(text)

        if user is not None:
            msg_text = ""
            db_info = db_get_user_info(int(user.id))

            group = GROUPS_STR[db_info["group"]]
            is_admin = "да" if db_info.get("admin") else "нет"
            steam_id = (
                "https://steamcommunity.com/profiles/" + db_info["steam_id"]
                if db_info.get("steam_id") else "неизвестно"
            )

            create_date = db_info.get("create_date", "не создан")

            user_info = """
            Информация о пользователе:\nГруппа пользователя: {}\nСоздан: {}\nSteam: {}\nАдмин: {}
            """.format(group, create_date, steam_id, is_admin)

            msg_text += user_info

            if int(db_info["group"]) > 1:
                key = db_info["key"] if db_info.get("key") else "отсутствует"

                if db_info.get("endless"):
                    expiration_date = "никогда"
                else:
                    date = parse(db_info["expiration_date"])
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

                promocodes = get_user_promocodes(user.id)
                key_info = """
                        Информация о ключе:\nКлюч: {}\nИстекает: {}\nИспользованные промокоды: {}
                    """.format(key, expiration_date, promocodes)

                msg_text += key_info

            return msg_text
        else:
            return "Пользоавтель не найден"


@bp.on.private_message(state_group=AdminUser, payload={"admin": "back"})
async def back_to_admin_user_keyboard(message: Message):
    await bp.state_dispenser.delete(message.peer_id)
    await send_admin_user_keyboard(message)
