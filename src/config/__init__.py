import orjson
from redis import Redis


class Config:
    def __getattr__(self, item):
        with open("config/{}.json".format(item)) as f:
            return orjson.loads(f.read())

    @property
    def info_text(self) -> str:
        with open("config/info.txt") as f:
            return f.read()


Config = Config()


class Groups:
    NOT_REG = "0"
    REG_WITHOUT_KEY = "1"
    REG_WITH_KEY = "2"
    REG_EXPIRED_KEY = "3"


GROUPS_STR = {
    Groups.NOT_REG: "незарегистрированный пользователь",
    Groups.REG_WITHOUT_KEY: "зарегистрированный пользователь без ключа",
    Groups.REG_WITH_KEY: "зарегистрированный пользователь с ключом",
    Groups.REG_EXPIRED_KEY: "зарегистрированный пользователь с просроченным ключом"
}

MONTH_NAMES = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря"
}

redis_db = Redis(db=1, unix_socket_path=Config.settings["redis_sock_path"], charset="utf-8", decode_responses=True)

redis_vk_music_db = Redis(db=0, unix_socket_path=Config.settings["redis_sock_path"], charset="utf-8",
                          decode_responses=True)

