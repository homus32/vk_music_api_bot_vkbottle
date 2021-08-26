from hashlib import sha256
from hmac import new
from uuid import uuid4
from datetime import datetime, timedelta

import aiohttp
from aiohttp import web
from vkbottle import API, Bot
from vkbottle.modules import logger, json

from src.utils.orm import *
from src.utils import declension_date
from src.config import Config, redis_db as r
from src.keyboards import TO_MENU_KEYBOARD


SECRET_KEY = Config.settings["qiwi"]
api: API
bot: Bot


async def get_payment_link(user_id, purchase_info):
    headers = {
        "Authorization": "Bearer {}".format(SECRET_KEY),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    term = (
        str(purchase_info["tariff"][1])[:-1] + " "
        if str(purchase_info["tariff"][1])[:-1] != "" else ""
    )

    tariff_name = term + declension_date(purchase_info["tariff"][1])
    expiration_date = (
            datetime.now(timezone_msk).replace(microsecond=0) + timedelta(hours=6)
    ).isoformat()
    data = {
        "amount": {
            "currency": "RUB",
            "value": str(purchase_info["cost"]) + ".00"
        },
        "comment": "Покупка тарифа \"{}\" у Example Bot Бота".format(tariff_name),
        "expirationDateTime": expiration_date,
        "customFields": {
            "themeCode": "Name-VyvDLlgxJt",
            "service": "example_bot",
            "vk": str(user_id),
            "days": str(purchase_info["days"]),
            "promocode": purchase_info.get("promocode", "")
        }
    }

    uuid = uuid4()

    async with aiohttp.ClientSession() as s:

        async with s.put(
                "https://api.qiwi.com/partner/bill/v1/bills/{}".format(uuid),
                json=data,
                headers=headers
        ) as resp:
            resp_json = await resp.json()

            if resp_json.get("payUrl") is not None:
                logger.info(resp_json)
                r.delete("{}_payment".format(user_id))
                return resp_json["payUrl"]

            else:
                error_msg = "Payment Error!! uuid: {}; vk: {};\nPayload: {}\nData: {}".format(
                    uuid,
                    user_id,
                    purchase_info,
                    resp_json
                )

                logger.error(error_msg)

                try:
                    await bot.state_dispenser.delete(peer_id=user_id)
                except KeyError:
                    pass

                await api.messages.send(
                    message="!!! Произошла ошибка выдачи ссылки. Обратитесь администратору. !!!",
                    peer_id=user_id,
                    random_id=0,
                    keyboard=TO_MENU_KEYBOARD
                )

                return None


@logger.catch
async def receive_payment(request: web.Request):
    headers = request.headers
    body = (await request.json()).get("bill", {})

    invoice_parameters = "{}|{}|{}|{}|{}".format(
        body.get("amount", {}).get("currency"),
        body.get("amount", {}).get("value"),
        body.get("billId"),
        body.get("siteId"),
        body.get("status", {}).get("value"),
    )

    if new(
            SECRET_KEY.encode(),
            invoice_parameters.encode(),
            sha256
    ).hexdigest() == headers.get("X-Api-Signature-SHA256"):
        if body.get("status", {}).get("value") == "PAID":

            if body.get("customFields", {}).get("service") == "example_bot":
                vk = int(body["customFields"]["vk"])
                days = int(body["customFields"]["days"])
                days = days if days != 0 else None

                promocode = body["customFields"].get("promocode", "")

                with db_session:
                    user_key = Key.get(id=vk)
                    if user_key is not None:

                        if days is not None:
                            if user_key.expiration_date <= datetime.now(timezone_msk):
                                user_key.expiration_date = datetime.now(timezone_msk) \
                                                           + timedelta(days=days)
                            else:
                                user_key.expiration_date += timedelta(days=days)
                        else:
                            user_key.expiration_date = days

                    else:

                        if days is not None:
                            Key(
                                id=vk,
                                key=None,
                                expiration_date=datetime.now(timezone_msk) + timedelta(days=days)
                            )
                        else:
                            Key(id=vk, key=None, expiration_date=None)

                    if promocode != "":
                        Promocode(user=vk, promocode=promocode)

                try:
                    await bot.state_dispenser.delete(peer_id=vk)
                except KeyError:
                    pass

                r.delete("{}_info".format(vk))
                logger.info(
                    "New key purchase! vk: {}; days: {}; promocode: {}; billId: {}".format(
                        vk,
                        days,
                        promocode,
                        body.get("billId")
                    )
                )

                await api.messages.send(
                    message="Спасибо за покупку! Если ты первый раз купил то, тебе "
                            "надо зайти в меню и тыкнуть на \"Панель управления ключем\" "
                            "и создать его. Если будут проблемы -- напиши админу",
                    peer_id=vk,
                    random_id=0,
                    keyboard=TO_MENU_KEYBOARD
                )

    return web.Response(body=json.dumps({"code": "0"}).decode(), content_type="application/json")


async def start_serving(main_bot: Bot):
    global api
    global bot

    api = main_bot.api
    bot = main_bot

    app = web.Application()
    app.add_routes([web.post('/', receive_payment)])

    # noinspection PyProtectedMember
    await web._run_app(app, port=4145, host="localhost", print=lambda x: None)
