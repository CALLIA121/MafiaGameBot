import asyncio
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import Bot, Dispatcher, types

import config as s
import db

from config import fprint

fprint('HELLO', type='BANER C6')

# -------------------------- Обнуление ----------------------------
connect = None
cursor = None
Succes = db.connectTo(s.DB_PATH)
if not Succes:
    fprint('КРИТИЧЕСКАЯ ОШИБКА: ', type='T1 C1', end='')
    fprint('Не удалось подключиться к базе данных.')
    exit(0)


# bot settings
API_TOKEN = s.TOKEN
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

