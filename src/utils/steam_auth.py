from urllib.parse import urlencode
from datetime import datetime
import asyncio
import hashlib


from vkbottle.api import API
from vkbottle.modules import logger
from aiohttp import web
import aiohttp

from config import redis_db as r, Config
from keyboards import TO_MENU_KEYBOARD
from .orm import *

PASSWORD = Config.settings["steam_link_encryption_password"]


class SteamAuth:

    server = None
    bot_api: API = None

    RESP_URI = "https://example.com/steam_auth"
    STEAM_LOGIN_URI = "https://steamcommunity.com/openid/login"

    def __init__(self, api: API, user_id):
        self.__class__.bot_api = api
        self.user_id = user_id

    def get_link_state(self):
        return hashlib.md5((PASSWORD + str(self.user_id)).encode()).hexdigest()

    def create_link(self):
        state = {
            "state": self.get_link_state(),
        }
        resp_uri_with_state = "{}?{}".format(self.RESP_URI, urlencode(state))

        auth_params = {
            'openid.ns': 'http://specs.openid.net/auth/2.0',
            'openid.mode': 'checkid_setup',
            'openid.return_to': resp_uri_with_state,
            'openid.realm': resp_uri_with_state,
            'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select'
        }

        return "{}?{}".format(self.STEAM_LOGIN_URI, urlencode(auth_params))

    async def get_link(self):
        steam_auth_key = "steam_auth_{}".format(self.get_link_state())

        if not bool(r.exists(steam_auth_key)):
            r.set(steam_auth_key, self.user_id)
            r.expire(steam_auth_key, 300)

        if self.__class__.server is None or self.__class__.server.done():
            self.__class__.server = asyncio.create_task(start_serving())

        return self.create_link()


async def check_data(query):
    query["openid.mode"] = "check_authentication"
    req_url = "{}?{}".format(SteamAuth.STEAM_LOGIN_URI, urlencode(query))

    async with aiohttp.ClientSession() as s:
        async with s.get(req_url) as resp:
            data = (await resp.read()).decode()

            if "is_valid:true" in data:
                return True

            return False


async def receive_steamid(request: web.Request):
    query = dict(request.query)

    if query.get("state") is None:
        return web.Response(text="Invalid URI")

    key = "steam_auth_{}".format(str(query["state"]))
    user_id = r.get(key)

    if user_id is None:
        return web.Response(text="Invalid URI. Please, try to register again")

    del query["state"]

    is_valid = await check_data(query)

    if not is_valid:
        r.delete(key)
        return web.Response(text="Invalid URI. Steam authorization timeout. Try to register again")

    steamid64 = int(query['openid.claimed_id'].split("/")[-1])

    with db_session:
        if User.exists(steamid64=steamid64):
            await SteamAuth.bot_api.messages.send(
                message="&#128128; Регистрация провалилась!\n\n"
                        "Этот steamid уже зарегестрирован!\n"
                        "Обратитесь админам, если это ошибка",
                peer_id=user_id,
                random_id=0
            )
            r.delete(key)
            return web.Response(text="Registration Failed. This steamid is already registered")

        User(id=user_id, steamid64=steamid64, create_date=datetime.now(timezone_msk))

    body = """
        <script type="text/javascript">window.close();</script>
        Authorization was successful <br>
        Please, close window, if window don't close automatically
    """

    r.delete("{}_info".format(user_id))

    await SteamAuth.bot_api.messages.send(
        message="&#9989; Регистрация прошла успешно!",
        peer_id=user_id,
        keyboard=TO_MENU_KEYBOARD,
        random_id=0
    )

    logger.info("New user registered! SteamID: {}; VK: {}".format(steamid64, user_id))
    r.delete(key)

    return web.Response(body=body, content_type="text/html")


async def check_steam_auth_keys():
    while True:
        await asyncio.sleep(30)
        all_keys = r.keys("steam_auth_*")

        if len(all_keys) == 0:
            SteamAuth.server.cancel()
            break


async def start_serving():
    app = web.Application()
    app.add_routes([web.get('/', receive_steamid)])
    asyncio.create_task(check_steam_auth_keys())

    # noinspection PyProtectedMember
    await web._run_app(app, port=5145, host="localhost", print=lambda x: None)
