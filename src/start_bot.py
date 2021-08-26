import sys
import uvloop

from utils import vkbottle_fix
from vkbottle import BaseMiddleware, MiddlewareResponse, GroupTypes, GroupEventType
from vkbottle.bot import Bot
from vkbottle.modules import logger

from config import Config, redis_db as r, redis_vk_music_db as r_api
from utils import get_user_info

from key_controller import action_with_keys
from utils.qiwi_purchase import start_serving
from utils.orm import *

bot = Bot(Config.settings["token"])
vkbottle_fix.set_fixed_event_view(bot.labeler)


class UserRecognize(BaseMiddleware):

    async def pre(self, event):

        try:
            user_id = event.peer_id
        except:
            user_id = event.object.user_id

        user_info_key = "{}_info".format(user_id)
        redis_user_info = r.hgetall(user_info_key)

        if len(redis_user_info) == 0:
            info = get_user_info(user_id)
            r.hset(user_info_key, mapping=info)
            r.expire(user_info_key, 300)


class AntiSpam(BaseMiddleware):

    async def pre(self, event):
        user_id = event.peer_id
        spam_key = "{}_spam".format(user_id)
        msg_count = r.incr(spam_key)

        if msg_count == 1:
            r.expire(spam_key, 2)
        elif msg_count > 2:
            return MiddlewareResponse(False)

        return MiddlewareResponse(True)


@bot.on.raw_event(GroupEventType.USER_BLOCK, GroupTypes.UserBlock)
async def on_user_block(event: GroupTypes.UserBlock):
    with db_session:
        user_id = event.object.user_id
        if Key.exists(id=user_id):
            key = Key[user_id].key
            if key is not None:
                r_api.srem("keys", key)

            Key.delete(Key[user_id])


if __name__ == '__main__':

    from menu import bp as menu_bp
    from registration import bp as registration_bp
    from purchase import bp as purchase_bp
    from user_key_control import bp as key_control_bp
    from admin import bp as admin_commands_bp

    bot_blueprints = (
        menu_bp,
        registration_bp,
        purchase_bp,
        key_control_bp,
        admin_commands_bp,
    )

    logger.remove()
    logger.add(sys.stdout, level="INFO")

    bot.labeler.message_view.register_middleware(UserRecognize())
    bot.labeler.message_view.register_middleware(AntiSpam())
    bot.labeler.raw_event_view.register_middleware(UserRecognize())

    bot.loop_wrapper.add_task(action_with_keys(bot.api))
    bot.loop_wrapper.add_task(start_serving(bot))

    for bp in bot_blueprints:
        bp.load(bot)

    uvloop.install()
    bot.run_forever()
