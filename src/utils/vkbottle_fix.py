from typing import Any, Callable, List, Set, Tuple, Union, Dict

from vkbottle_types.events import GroupEventType

from vkbottle.dispatch.abc import ABCView
from vkbottle.dispatch.handlers import FromFuncHandler
from vkbottle.dispatch.rules import ABCRule
from vkbottle.dispatch.views.bot import HandlerBasement
from vkbottle.dispatch.return_manager.bot import BotMessageReturnHandler

from vkbottle.tools.dev_tools.utils import convert_shorten_filter

from vkbottle.framework.bot.labeler.abc import EventName, LabeledHandler
from vkbottle.framework.bot.labeler.default import BotLabeler

from vkbottle.modules import logger
from vkbottle.api.abc import ABCAPI
from vkbottle import BaseMiddleware, MiddlewareResponse
from vkbottle.dispatch.dispenser.abc import ABCStateDispenser

ShortenRule = Union[ABCRule, Tuple[ABCRule, ...], Set[ABCRule]]


def raw_event(
        self,
        event: Union[EventName, List[EventName]],
        dataclass: Callable = dict,
        *rules: ShortenRule,
        blocking: bool = True,
        **custom_rules,
) -> LabeledHandler:
    if not isinstance(event, list):
        event = [event]

    def decorator(func):
        for e in event:

            if isinstance(e, str):
                e = GroupEventType(e)

            event_handlers = self.raw_event_view.handlers.get(e)

            handler_basement = HandlerBasement(
                dataclass,
                FromFuncHandler(
                    func,
                    *map(convert_shorten_filter, rules),
                    *self.auto_rules,
                    *self.get_custom_rules(custom_rules),
                    blocking=blocking,
                ),
            )

            if not event_handlers:
                self.raw_event_view.handlers[e] = [handler_basement]
            else:
                self.raw_event_view.handlers[e].append(handler_basement)
        return func

    return decorator


class RawEventView(ABCView):
    def __init__(self):
        self.handlers: Dict[GroupEventType, List[HandlerBasement]] = {}
        self.middlewares: List["BaseMiddleware"] = []
        self.handler_return_manager = BotMessageReturnHandler()

    async def process_event(self, event: dict) -> bool:
        if GroupEventType(event["type"]) in self.handlers:
            return True

    async def handle_event(
        self, event: dict, ctx_api: "ABCAPI", state_dispenser: "ABCStateDispenser"
    ) -> Any:
        logger.debug("Handling event ({}) with message view".format(event.get("event_id")))

        handler_basements = self.handlers[GroupEventType(event["type"])]
        context_variables = {}

        event_model = handler_basements[0].dataclass(**event)

        if isinstance(event_model, dict):
            event_model["ctx_api"] = ctx_api
        else:
            setattr(event_model, "unprepared_ctx_api", ctx_api)

        for middleware in self.middlewares:
            response = await middleware.pre(event_model)
            if response == MiddlewareResponse(False):
                return

            elif isinstance(response, dict):
                context_variables.update(response)

        handler_responses = []
        handlers = []

        for handler_basement in handler_basements:

            result = await handler_basement.handler.filter(event_model)
            logger.debug("Handler {} returned {}".format(handler_basement.handler, result))

            if result is False:
                continue

            elif isinstance(result, dict):
                context_variables.update(result)

            handler_response = await handler_basement.handler.handle(
                event_model, **context_variables
            )
            handler_responses.append(handler_response)
            handlers.append(handler_basement.handler)

            return_handler = self.handler_return_manager.get_handler(handler_response)

            if return_handler is not None:
                await return_handler(
                    self.handler_return_manager, handler_response, event_model, context_variables,
                )

            if handler_basement.handler.blocking:
                break

        for middleware in self.middlewares:
            await middleware.post(
                event_model, self, handler_responses, handlers
            )


def load(self, labeler: "BotLabeler"):
    self.message_view.handlers.extend(labeler.message_view.handlers)
    self.message_view.middlewares.extend(labeler.message_view.middlewares)

    for event, hd in labeler.raw_event_view.handlers.items():
        if self.raw_event_view.handlers.get(event) is None:
            self.raw_event_view.handlers[event] = []

        self.raw_event_view.handlers[event].extend(hd)

    self.raw_event_view.middlewares.extend(labeler.raw_event_view.middlewares)


def set_fixed_event_view(labeler: BotLabeler):
    labeler.raw_event_view = RawEventView()


BotLabeler.load = load
BotLabeler.raw_event = raw_event
