from vkbottle import Keyboard, KeyboardButtonColor as Color, Text
from src.config import Groups


class Menu:
    def __init__(self, user_info: dict):
        self.endless = user_info.get("endless")
        self.is_admin = user_info.get("admin")
        self.group = user_info["group"]

        self.menu = {
            Groups.NOT_REG: self.not_reg,
            Groups.REG_WITHOUT_KEY: self.reg_without_key,
            Groups.REG_WITH_KEY: self.reg_with_key,
            Groups.REG_EXPIRED_KEY: self.reg_expired_key
        }

        self.keyboard = Keyboard()

    def not_reg(self):
        self.keyboard.add(Text("Регистрация", {"cmd": "registration"}), color=Color.POSITIVE)

    def reg_with_key(self):
        if not self.endless:
            self.keyboard.add(Text("Продлить ключ", {"cmd": "buy"}), color=Color.POSITIVE)
            self.keyboard.row()

        self.keyboard.add(
            Text("Панель управления ключом", {"cmd": "key_panel"}),
            color=Color.PRIMARY
        )

    def reg_without_key(self):
        self.keyboard.add(Text("Купить ключ", {"cmd": "buy"}), color=Color.POSITIVE)

    def reg_expired_key(self):
        self.keyboard.add(Text("Продлить ключ", {"cmd": "buy"}), color=Color.POSITIVE)

    def admin(self):
        (
            self.keyboard
            .row()
                .add(Text("Админ панель", {"cmd": "admin_panel"}), color=Color.NEGATIVE)
        )

    def get(self) -> Keyboard:
        keyboard = (
            self.keyboard
                .add(Text("Информация", {"cmd": "info"}))
                .add(Text("Прайс-лист", {"cmd": "price_list"}))
                .row()
        )

        self.menu[self.group]()

        if self.is_admin:
            self.admin()

        return keyboard
