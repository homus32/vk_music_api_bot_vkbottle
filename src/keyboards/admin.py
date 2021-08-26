from vkbottle import Keyboard, Text

ADMIN_PANEL_KEYBOARD = (
    Keyboard()
    .add(Text("Пользователи", {"admin": "user"}))
    .add(Text("Тарифы и промокоды", {"admin": "term_control"}))
    .row()
    .add(Text("Независемые ключи и ключи пользователей", {"admin": "keys"}))
    .row()
    .add(Text("В меню", {"cmd": "menu"}))
).get_json()

ADMIN_USER_KEYBOARD = (
    Keyboard()
    .add(Text("Удаль. польз.", {"admin": "remove_user"}))
    .add(Text("Зарег. польз.", {"admin": "reg_user"}))
    .row()
    .add(Text("Измен. инф. о польз.", {"admin": "change_info_user"}))
    .add(Text("Инф. о польз.", {"admin": "user_info"}))
    .row()
    .add(Text("Назад", {"cmd": "admin_panel"}))
).get_json()

ADMIN_TERM_CONTROL_KEYBOARD = (
    Keyboard()
    .add(Text("Изм. тариф у поль.", {"admin": "set_user_tariff"}))
    .add(Text("Прод. тариф у поль.", {"admin": "extend_user_tariff"}))
    .row()
    .add(Text("Изменить промокоды у польз.", {"admin": "change_user_promocodes"}))
    .row()
    .add(Text("Назад", {"cmd": "admin_panel"}))

).get_json()

ADMIN_CHANGE_PROMOCODES_KEYBOARD = (
    Keyboard()
    .add(Text("Добавить промокод пользоавтелю", {"admin": "add_prom_mode"}))
    .row()
    .add(Text("Удалить промокод у пользователя", {"admin": "del_prom_mode"}))
    .row()
    .add(Text("Назад", {"admin": "back"}))
).get_json()

ADMIN_KEYS_KEYBOARD = (
    Keyboard()
    .add(Text("Изменить ключ у поль.", {"admin": "change_key_value"}))
    .add(Text("Удал. независ. ключ", {"admin": "del_ind_key"}))
    .row()
    .add(Text("Созд. независ. ключ", {"admin": "create_ind_key"}))
    .add(Text("Список независ. ключей", {"admin": "ind_keys_list"}))
    .row()
    .add(Text("Назад", {"cmd": "admin_panel"}))

).get_json()

ADMIN_BACK_BUTTON_KEYBOARD = Keyboard().add(Text("Назад", {"admin": "back"})).get_json()
