from vkbottle import Keyboard, KeyboardButtonColor as Color, Text

KEY_PANEL_CREATE_KEYBOARD = (
    Keyboard()
    .add(Text("Создать ключ", {"cmd": "change_key"}), color=Color.POSITIVE)
    .row()
    .add(Text("В меню", {"cmd": "menu"}))
).get_json()

KEY_PANEL_KEYBOARD = (
    Keyboard()
    .add(Text("Изменить ключ", {"cmd": "change_key"}), color=Color.POSITIVE)
    .add(Text("Удалить ключ", {"cmd": "delete_key"}), color=Color.NEGATIVE)
    .row()
    .add(Text("В меню", {"cmd": "menu"}))
).get_json()

KEY_PANEL_CHANGE_KEYBOARD = (
    Keyboard()
    .add(Text("Свой ключ", {"cmd": "my_key_value"}), color=Color.PRIMARY)
    .add(Text("Сила рандома", {"cmd": "key_random_value"}), color=Color.PRIMARY)
    .row()
    .add(Text("Назад", {"cmd": "key_back"}))
).get_json()


def key_panel(db_info):
    if db_info.get("key"):
        return KEY_PANEL_KEYBOARD
    else:
        return KEY_PANEL_CREATE_KEYBOARD


__all__ = (
    "KEY_PANEL_CREATE_KEYBOARD",
    "KEY_PANEL_CHANGE_KEYBOARD",
    "KEY_PANEL_KEYBOARD",
    "key_panel",
)
