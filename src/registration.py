from vkbottle.bot import Blueprint, Message
from vkbottle import GroupEventType, GroupTypes
from vkbottle.modules import json

from config import Groups
from utils import WithoutStateRule, GroupRule, EventPayloadRule, steam_auth
from keyboards import REGISTRATION_KEYBOARD

bp = Blueprint("registration")


@bp.on.private_message(WithoutStateRule(), GroupRule(Groups.NOT_REG), payload={"cmd": "registration"})
async def registration(message: Message):
    msg_text = """
    Окей, чтобы зарегестрироватся тебе надо авторизоватся в Steam.\n
    Это безопасная авторизация. Я получу лишь твой SteamID64.\n
    Но время авторизации ограниченно, у вас будет 5 минут на логин в ваш аккаунт.\n
    После этого времени авторизация будет не действительна, и бот не сможет вас зарегестрировать.\n
    """

    await message.answer(message=msg_text, keyboard=REGISTRATION_KEYBOARD)


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    GroupTypes.MessageEvent,
    GroupRule(Groups.NOT_REG),
    EventPayloadRule({"link": "registration"}),
)
async def send_registration_link(event: GroupTypes.MessageEvent):

    steam = steam_auth.SteamAuth(bp.api, event.object.user_id)
    link = await steam.get_link()

    # noinspection PyTypeChecker
    await bp.api.messages.send_message_event_answer(
        event_id=event.object.event_id,
        user_id=str(event.object.user_id),
        peer_id=str(event.object.peer_id),
        event_data=json.dumps({"type": "open_link", "link": link}).decode(),
    )
