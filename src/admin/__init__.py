from vkbottle.bot import Blueprint, Message
# noinspection PyUnresolvedReferences
from src.utils import WithoutStateRule, WithoutPayloadRule, AdminRule
from src.keyboards import ADMIN_PANEL_KEYBOARD
from src.utils.orm import *

bp = Blueprint("admin_commands")
bp.labeler.auto_rules = (
    AdminRule(),
)

COMMAND_SYNTAX = "\n\nСинтаксис: ключ значение и т.д\nНапример: " \
                 "vk 1 steam 76561197960287930"


def get_index(l: list, index, default=None):
    try:
        return l[index]
    except IndexError:
        return default


def parse_text(text: str):
    split_text = text.split()
    pack_text = [split_text[n:n + 2] for n in range(0, len(split_text), 2)]
    answer = {}

    for pack in pack_text:
        k = get_index(pack, 0).lower()
        v: str = get_index(pack, 1)
        answer[k] = int(v) if v is not None and v.isdigit() else v

    return answer


def get_user_by_text(text: dict):
    if "vk" in text and isinstance(text["vk"], int):
        return User.get(id=text["vk"])
    elif "steam" in text and isinstance(text["steam"], int):
        return User.get(steamid64=text["steam"])
    elif "key" in text:
        key = Key.get(key=text["key"])
        if key is not None:
            return key.id


def enum_array(l):
    return "\n".join(
        "{}. {}".format(num + 1, prom)
        for num, prom in enumerate(l)
    )


@bp.on.private_message(WithoutStateRule(), payload={"cmd": "admin_panel"})
async def send_admin_panel(message: Message):
    await message.answer("Держи админ панельку!", keyboard=ADMIN_PANEL_KEYBOARD)


if True:
    import admin.keys
    import admin.term_control
    import admin.users

