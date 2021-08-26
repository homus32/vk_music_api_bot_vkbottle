from vkbottle.bot import Message, Blueprint
from vkbottle import BaseStateGroup

from utils import WithoutStateRule, GroupRule, password_valid, generate_password
from utils.orm import *

from keyboards import KEY_PANEL_CHANGE_KEYBOARD, key_panel, TO_MENU_KEYBOARD, VOID_KEYBOARD
from config import Config, Groups, redis_db as r, redis_vk_music_db as r_api

bp = Blueprint("user_key_control")
bp.labeler.auto_rules = (
    GroupRule(Groups.REG_WITH_KEY),
)


class KeyChange(BaseStateGroup):
    CHOICE_PANEL_STATE = 10
    GET_KEY_STATE = 11


@bp.on.private_message(WithoutStateRule(), payload={"cmd": "key_panel"})
async def send_key_keyboard(message: Message):
    db_info = r.hgetall("{}_info".format(message.peer_id))

    await message.answer(
        "Вот, панель управления ключом",
        keyboard=key_panel(db_info)
    )


@bp.on.private_message(payload={"cmd": "change_key"})
async def send_key_change_keyboard(message: Message):
    await bp.state_dispenser.set(message.peer_id, KeyChange.CHOICE_PANEL_STATE)
    await message.answer(
        "Как будем делать ключ?",
        keyboard=KEY_PANEL_CHANGE_KEYBOARD
    )


@bp.on.private_message(state=KeyChange.CHOICE_PANEL_STATE, payload={"cmd": "key_back"})
async def back_to_key_keyboard(message: Message):
    await bp.state_dispenser.delete(message.peer_id)
    await send_key_keyboard(message)


@bp.on.private_message(state=KeyChange.CHOICE_PANEL_STATE, payload={"cmd": "key_random_value"})
async def generate_random_password(message: Message):
    while True:
        password = generate_password()
        is_created = await set_password(message, password)

        if not is_created:
            await message.answer(
                "Ого! Сгенерированный пароль уже есть в базе данных! А ты везучий хуй... "
                "Сгенерирую ещё раз пароль..."
            )
        else:
            break

    await bp.state_dispenser.delete(message.peer_id)
    await message.answer(
        "Пароль успешно сгенерирован! Его значение -- {}.".format(password),
        keyboard=TO_MENU_KEYBOARD
    )


@bp.on.private_message(state=KeyChange.CHOICE_PANEL_STATE, payload={"cmd": "my_key_value"})
async def print_key_mode(message: Message):
    await bp.state_dispenser.set(message.peer_id, KeyChange.GET_KEY_STATE)
    await message.answer(
        "Хорошо. Правила просты -- в пароле не должно быть русских букв и пробелов. "
        "Но позволяется в пароле иметь такие символов -- \"!#*^_.\". Ну и цифры тоже.\n"
        "Теперь, напиши в чат свой пароль.",
        keyboard=VOID_KEYBOARD
    )


@bp.on.private_message(state=KeyChange.GET_KEY_STATE)
async def get_key(message: Message):
    password = message.text

    if password_valid(password):
        is_created = await set_password(message, password)

        if is_created:
            await bp.state_dispenser.delete(message.peer_id)
            r_api.sadd("keys", password)
            r.delete("{}_info".format(message.peer_id))

            await message.answer(
                "Атлишна. Вы установили пароль! Его значение -- {}".format(password),
                keyboard=TO_MENU_KEYBOARD
            )

        else:
            return "Этот пароль уже занят... Его поменяют (если он не публичный)... " \
                   "Но придумай-ка себе другой пароль"

    else:
        return "В вашем пароле запрещенные символы. Придумайте другой"


@bp.on.private_message(payload={"cmd": "delete_key"})
async def delete_key(message: Message):

    with db_session:
        key = str(Key[message.peer_id].key)
        Key[message.peer_id].key = None

    r_api.srem("keys", key)
    r.delete("{}_info".format(message.peer_id))

    await message.answer(
        "Ваш ключ успешно удален! Пересоздать можете через Меню",
        keyboard=TO_MENU_KEYBOARD
    )


async def set_password(message: Message, password):
    with db_session:

        if not Independent_key.exists(key=password):
            user_key = Key.get(id=message.peer_id)
            old_key = user_key.key

            if not Key.exists(key=password):
                user_key.key = password
            else:
                stolen_key_user = Key.get(key=password)
                stolen_key_user.key = None
                user_key.key = password
                if stolen_key_user.id.id != message.peer_id:
                    await message.answer(
                        message="ВНИМАНИЕ!!! Ваш пароль смогли подобрать. Ради безопасности бот "
                                "удалил ключ. Вам придется создать его по-новому через Меню"
                    )

            r_api.srem("keys", str(old_key))
            r_api.sadd("keys", password)
            r.delete("{}_info".format(message.peer_id))
        else:
            for uid in Config.admin:
                await bp.api.messages.send(
                    message="ВНИМАНИЕ!!! Независемый ключ со значением {} подобрали!"
                            " Пересоздайте его. P: {}".format(password, message.get_payload_json()),
                    peer_id=uid,
                    random_id=0
                )
            return False

        return True
