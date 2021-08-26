from vkbottle import Keyboard, KeyboardButtonColor, Text, Callback
from src.utils import declension_date
from src.config import Config

AT_A_TIME = 2

CONFIRM_KEYBOARD = (
    Keyboard()
    .add(Text("Да", {"confirm": "yes"}), color=KeyboardButtonColor.POSITIVE)
    .row()
    .add(Text("Нет", {"confirm": "no"}), color=KeyboardButtonColor.NEGATIVE)
).get_json()

PURCHASE_KEYBOARD = (
    Keyboard()
    .add(Callback("Купить (та самая зеленая кнопка)", {"link": "qiwi_buy"}),
         color=KeyboardButtonColor.POSITIVE)
    .row()
    .add(Text("Отмена", {"cmd": "cancel"}))
).get_json()

PROMOCODE_KEYBOARD = (
    Keyboard()
    .add(Text("У меня нет промокода", {"cmd": "no_promocode"}), color=KeyboardButtonColor.PRIMARY)
    .row()
    .add(Text("Назад", {"cmd": "return"}))
).get_json()


def tariff_keyboard():
    keyboard = Keyboard()
    price_list = Config.pricelist
    pack_price_list = [price_list[n:n + AT_A_TIME] for n in range(0, len(price_list), AT_A_TIME)]

    for pack_num, pack in enumerate(pack_price_list):
        pack_num = pack_num * AT_A_TIME

        for tariff_num, (cost, term) in enumerate(pack):
            tariff_num = tariff_num + pack_num

            keyboard.add(
                Text(
                    "{}₽ -- {} {}".format(
                        cost,
                        str(term)[:-1],
                        declension_date(term)
                    ),
                    {"tariff": tariff_num}
                ),
                color=KeyboardButtonColor.POSITIVE
            )

        keyboard.row()

    keyboard.add(Text("В меню", {"cmd": "menu"}))
    return keyboard.get_json()


__all__ = (
    "CONFIRM_KEYBOARD",
    "PURCHASE_KEYBOARD",
    "PROMOCODE_KEYBOARD",
    "tariff_keyboard",
)
