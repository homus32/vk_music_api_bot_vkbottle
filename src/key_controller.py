import asyncio

from datetime import datetime
from vkbottle import API
from vkbottle.modules import logger

from config import redis_vk_music_db as r_api, redis_db as r
from utils.orm import *

in_key_remover = set()
end_key_sent_notify = set()


async def key_remove_timer(seconds, key: Key, api: API):
    await asyncio.sleep(seconds)

    await api.messages.send(
        message="Срок вашего ключа закончился. Ваш ключ больше не активен."
                "Напоминаю, продлить ключ можно через меню.",
        peer_id=int(key.id.id),
        random_id=0
    )

    if key.key is not None:
        r_api.srem("keys", key.key)

    r.delete("{}_info".format(int(key.id.id)))
    in_key_remover.discard(int(key.id.id))
    end_key_sent_notify.discard(int(key.id.id))


async def action_with_keys(api: API):

    while True:
        keys_to_redis = set()

        try:
            with db_session:
                for key in Key.select():
                    if key.expiration_date is not None:
                        delta = key.expiration_date - datetime.now(timezone_msk)
                        minutes = round(delta.total_seconds() / 60)

                        if minutes <= 0:
                            continue

                        elif minutes <= 10:
                            if int(key.id.id) not in in_key_remover:
                                in_key_remover.add(int(key.id.id))
                                asyncio.create_task(key_remove_timer(delta.seconds, key, api))

                        elif minutes <= 60:
                            if int(key.id.id) not in end_key_sent_notify:
                                end_key_sent_notify.add(int(key.id.id))

                                await api.messages.send(
                                    message="Уведомление. Срок вашего ключа истекает. "
                                            "Продлите срок, чтобы "
                                            "ключ не отключался. Сделать это можно через \"Меню\"",
                                    peer_id=int(key.id.id),
                                    random_id=0

                                )

                    if key.key is not None:
                        keys_to_redis.add(key.key)

                for key in Independent_key.select():
                    if key.expiration_date is not None:
                        delta = key.expiration_date - datetime.now(timezone_msk)
                        minutes = round(delta.seconds / 60)

                        if minutes <= 0:
                            Independent_key.delete(key)
                            continue

                    keys_to_redis.add(key.key)

            if len(keys_to_redis) != 0:
                r_api.delete("keys")
                r_api.sadd("keys", *keys_to_redis)

        except Exception as error:
            logger.exception(error)

        await asyncio.sleep(300)
