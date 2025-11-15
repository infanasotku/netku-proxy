from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode


def get_bot(token: str):
    return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
