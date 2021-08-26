from vkbottle import Keyboard, KeyboardButtonColor, Callback, Text

from .menu import Menu
from .purchase import *
from .key_control import *
from .admin import *

REGISTRATION_KEYBOARD = (
    Keyboard()
    .add(
        Callback("Авторизироваться в Steam", payload={"link": "registration"}),
        color=KeyboardButtonColor.POSITIVE
    )
    .row()
    .add(Text("В меню", payload={"cmd": "menu"}))
).get_json()

TO_MENU_KEYBOARD = Keyboard().add(Text("В меню", {"cmd": "menu"})).get_json()

VOID_KEYBOARD = Keyboard().get_json()
