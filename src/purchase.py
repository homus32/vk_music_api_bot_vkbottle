import asyncio

from vkbottle import GroupEventType, GroupTypes
from vkbottle.bot import Blueprint, Message
from vkbottle import BaseStateGroup
from vkbottle.modules import json

from config import Groups, Config, redis_db as r
from keyboards import tariff_keyboard, PROMOCODE_KEYBOARD
from keyboards import CONFIRM_KEYBOARD, PURCHASE_KEYBOARD, Menu
from utils import GroupRule, EventPayloadRule, date_to_days
from utils import get_user_promocodes, declension_date
from utils.qiwi_purchase import get_payment_link

bp = Blueprint("purchase")
bp.labeler.auto_rules = (
    GroupRule((Groups.REG_WITH_KEY, Groups.REG_WITHOUT_KEY, Groups.REG_EXPIRED_KEY)),
)


class PurchaseStates(BaseStateGroup):
    PROMOCODE_STATE = 0
    CONFIRM_STATE = 1
    PURCHASE_STATE = 2


@bp.on.private_message(payload={"cmd": "buy"})
async def send_tariff_keyboard(message: Message):
    await message.answer(message="Выберите тариф, который вам по душе", keyboard=tariff_keyboard())


@bp.on.private_message(payload_map={"tariff": int})
async def promocode_state(message: Message):
    tariff_num = message.get_payload_json().get("tariff")

    if tariff_num is None:
        tariff = message.state_peer.payload["tariff"]
    else:
        tariff = Config.pricelist[tariff_num]

    await bp.state_dispenser.set(
        message.peer_id,
        PurchaseStates.PROMOCODE_STATE,
        tariff=tariff,
        cost=tariff[0],
        days=date_to_days(tariff[1])
    )
    tariff_name = "{}₽ -- {} {}".format(tariff[0], str(tariff[1])[:-1], declension_date(tariff[1]))
    msg_text = "Вы выбрали тариф \"{}\".\nЕсли у вас есть промокод на скидку " \
               "то напишите его здесь\n\n" \
               "ПРИМИЧАНИЕ. Если используете промокод, то он у вас сгорит. " \
               "Вы не сможете использовать его ещё раз.".format(tariff_name)
    await message.answer(message=msg_text, keyboard=PROMOCODE_KEYBOARD)


@bp.on.private_message(state=PurchaseStates.PROMOCODE_STATE, payload={"cmd": "no_promocode"})
async def no_promocode(message: Message):
    if message.state_peer.payload.get("promocode") is not None:
        del message.state_peer.payload["promocode"]

    message.state_peer.payload["cost"] = message.state_peer.payload["tariff"][0]
    await message.answer("Ну ладно, нет так нет...")
    await asyncio.sleep(0.5)
    await send_summary(message)


@bp.on.private_message(state=PurchaseStates.PROMOCODE_STATE, payload={"cmd": "return"})
async def return_to_tariff(message: Message):
    await bp.state_dispenser.delete(message.peer_id)
    await send_tariff_keyboard(message)


@bp.on.private_message(state=PurchaseStates.PROMOCODE_STATE)
async def get_promocode(message: Message):
    promocode = message.text
    promocodes = Config.promocode
    cost = message.state_peer.payload["tariff"][0]

    user_promocodes = message.state_peer.payload.get("user_promocodes")

    if user_promocodes is None:
        user_promocodes = get_user_promocodes(message.peer_id)
        message.state_peer.payload.update(user_promocodes=user_promocodes)
        await bp.state_dispenser.set(
            message.peer_id,
            PurchaseStates.PROMOCODE_STATE,
            **message.state_peer.payload
        )

    if promocode not in user_promocodes:
        if promocode in promocodes:
            discount = Config.promocode[promocode]
            cost_discount = int(cost - (cost * (discount / 100)))
            msg_text = "Этот промокод дает вам скидку в {}%, " \
                       "что делает цену на тариф {} рублей.".format(discount, cost_discount)

            await message.answer(message=msg_text)

            if cost_discount < 1:
                cost_discount = 1
                await message.answer("И о боже, ценна настолько низкая, что пришлось сделать "
                                     "её в размере 1 рубля :P")

            message.state_peer.payload.update(
                discount=discount,
                promocode=promocode,
                cost=cost_discount,
            )

            await asyncio.sleep(1)
            await send_summary(message)

        else:
            await message.answer(message="Промокод не найден. Проверьте промокод.")
    else:
        await message.answer("Этим промокодом вы уже воспользовались. Попробуйте другой")


async def send_summary(message: Message):
    payload = message.state_peer.payload
    msg_text = "Сводка:\n" \
               "Тариф \"{}{}\".\n" \
               "Со стоимостью {} рублей.\n" \
               "{}" \
               "&#128073; Финальная стоимость -- {} рублей &#128072;\n\n" \
               "Все правильно?"

    have_promocode = payload.get("promocode") is not None
    promocode_text = ""

    if have_promocode:
        promocode_text = "&#128200; Скидка в размере {}% по промокоду \"{}\" " \
                         "сбрасывает цену на {} рублей " \
                         "что делает из неё {} рублей\n".format(
                            payload["discount"],
                            payload["promocode"],
                            int(int(payload["tariff"][0]) * (int(payload["discount"]) / 100)),
                            payload["cost"]
                            )

    term = str(payload["tariff"][1])[:-1] + " " if str(payload["tariff"][1])[:-1] != "" else ""
    msg_text = msg_text.format(
        term,
        declension_date(payload["tariff"][1]),
        payload["tariff"][0],
        promocode_text,
        payload["cost"]

    )

    await bp.state_dispenser.set(message.peer_id, PurchaseStates.CONFIRM_STATE, **payload)
    await message.answer(message=msg_text, keyboard=CONFIRM_KEYBOARD)


@bp.on.private_message(state=PurchaseStates.CONFIRM_STATE, payload={"confirm": "yes"})
async def confirm_yes(message: Message):
    await message.answer("Okay.")
    payload = message.state_peer.payload

    if payload.get("user_promocodes") is not None:
        del payload["user_promocodes"]

    r_key = "{}_payment".format(message.peer_id)
    r.set(r_key, str(payload))
    r.expire(r_key, 21600)
    await bp.state_dispenser.set(message.peer_id, PurchaseStates.PURCHASE_STATE, **payload)
    await asyncio.sleep(0.5)

    msg_text = "Чтобы купить, вам осталось нажать на одну зеленую кнопку\n" \
               "Оплата происходит через QIWI, он может брать комиссию\n" \
               "Имейте это в виду.\n\n" \
               "После оплаты бот автоматически выдаст/продлит ключ."

    await message.answer(msg_text, keyboard=PURCHASE_KEYBOARD)


@bp.on.private_message(state=PurchaseStates.CONFIRM_STATE, payload={"confirm": "no"})
async def confirm_no(message: Message):
    await promocode_state(message)


@bp.on.private_message(state=PurchaseStates.PURCHASE_STATE, payload={"cmd": "cancel"})
async def purchase_cancel(message: Message):
    await message.answer("Вы уверены?", keyboard=CONFIRM_KEYBOARD)


@bp.on.private_message(state=PurchaseStates.PURCHASE_STATE, payload={"confirm": "yes"})
async def purchase_confirm_yes(message: Message):
    await bp.state_dispenser.delete(message.peer_id)
    user_info_key = "{}_info".format(message.peer_id)
    db_info = r.hgetall(user_info_key)
    keyboard = Menu(db_info).get()
    await message.answer("Жаль. Верну вас в меню", keyboard=keyboard.get_json())


@bp.on.private_message(state=PurchaseStates.PURCHASE_STATE, payload={"confirm": "no"})
async def purchase_confirm_no(message: Message):
    await confirm_yes(message)


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    GroupTypes.MessageEvent,
    EventPayloadRule({"link": "qiwi_buy"}),
)
async def send_qiwi_link(event: GroupTypes.MessageEvent):

    payment_info_raw = r.get("{}_payment".format(event.object.peer_id))

    if payment_info_raw is not None:

        payment_info = eval(payment_info_raw)
        link = await get_payment_link(event.object.peer_id, payment_info)

        if link is None:
            # noinspection PyTypeChecker
            await bp.api.messages.send_message_event_answer(
                event_id=event.object.event_id,
                user_id=str(event.object.user_id),
                peer_id=str(event.object.peer_id),
            )

        else:
            # noinspection PyTypeChecker
            await bp.api.messages.send_message_event_answer(
                event_id=event.object.event_id,
                user_id=str(event.object.user_id),
                peer_id=str(event.object.peer_id),
                event_data=json.dumps({"type": "open_link", "link": link}).decode(),
            )
    else:
        await bp.api.messages.send(
            message="Покупка удаленна или закончился срок жизни! Либо вы нажали на зеленую кнопку "
                    "либо слишком долго на неё не нажимали. Если это ошибка -- обратитесть админу",
            peer_id=event.object.peer_id,
            random_id=0
        )

        # noinspection PyTypeChecker
        await bp.api.messages.send_message_event_answer(
            event_id=event.object.event_id,
            user_id=str(event.object.user_id),
            peer_id=str(event.object.peer_id),
        )
