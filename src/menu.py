from datetime import datetime
from dateutil import parser

from vkbottle.bot import Message, Blueprint, rules

from config import Config, GROUPS_STR, MONTH_NAMES, redis_db as r
from utils import timezone_msk, WithoutStateRule, declension_date
from keyboards import Menu

bp = Blueprint("menu")


@bp.on.private_message(
    WithoutStateRule(),
    (
        rules.LevensteinRule("Меню", 2),
        rules.PayloadRule({"cmd": "menu"})
    )
)
async def menu(message: Message):
    user_info_key = "{}_info".format(message.peer_id)
    db_info = r.hgetall(user_info_key)
    keyboard = Menu(db_info).get()
    await message.answer(message="Увот. Меню", keyboard=keyboard.get_json())


@bp.on.private_message(WithoutStateRule(), rules.LevensteinRule("Начать", 2))
async def start(message: Message):
    db_info = r.hgetall("{}_info".format(message.peer_id))
    keyboard = Menu(db_info).get()

    user_info = await bp.api.users.get(user_id=message.peer_id)
    msg_text = "Привет, {}! Рад, что вы зашли сюда... Ваша текущая группа: {}. ".format(
        user_info[0].first_name,
        GROUPS_STR[db_info["group"]]
    )

    if db_info.get("admin"):
        msg_text += "А ещё вы админ..."

    await message.answer(message=msg_text, keyboard=keyboard.get_json())
    await message.answer(message=str(Config.info_text))


@bp.on.private_message(WithoutStateRule(), payload={"cmd": "info"})
async def send_info(message: Message):
    info = str(Config.info_text)
    db_info = r.hgetall("{}_info".format(message.peer_id))
    keyboard = Menu(db_info).get()

    group = GROUPS_STR[db_info["group"]]
    is_admin = "да" if db_info.get("admin") else "нет"
    steam_id = (
        "https://steamcommunity.com/profiles/" + db_info["steam_id"]
        if db_info.get("steam_id") else "неизвестно"
    )

    user_info = """
\n&#128125; Информация о вас:
Группа пользователя: {}
Steam: {}
Админ: {}
    """.format(group, steam_id, is_admin)

    info += user_info
    if int(db_info["group"]) > 1:
        key = db_info["key"] if db_info.get("key") else "отсутствует"

        if db_info.get("endless"):
            expiration_date = "никогда"
        else:
            date = parser.parse(db_info["expiration_date"])
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

        key_info = """
&#128273; Информация о ключе:
Ключ: {}
Истекает: {}
        """.format(key, expiration_date)

        info += key_info

    await message.answer(message=info, keyboard=keyboard.get_json())


@bp.on.private_message(payload={"cmd": "price_list"})
async def price_list(message: Message):
    msg_text = "Доступные тарифы:\n"

    for num, (coast, term) in enumerate(Config.pricelist):
        msg_text += "{}. {} рублей -- {} {}\n".format(
            num + 1,
            coast,
            str(term)[:-1],
            declension_date(term)
        )

    await message.answer(message=msg_text)
