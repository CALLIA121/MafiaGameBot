import json
import random
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import db
from config import fprint, MAX_PLAYERS

# ------------------------ Инициализация бота -----------------------
API_TOKEN = 'YOUR_BOT_TOKEN'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ------------------------ Константы и утилиты -----------------------
PHASE_TIMEOUTS = {'night': 60, 'day': 120}
ROLES = {
    1: {'title': 'Мирный житель', 'emoji': '👨🌾'},
    2: {'title': 'Мафия', 'emoji': '🔫'},
    3: {'title': 'Доктор', 'emoji': '🩺'},
    4: {'title': 'Комиссар', 'emoji': '🕵️'}
}

async def send_to_group(chat_id, text):
    await bot.send_message(chat_id, f"👮♂️ Ведущий: {text}")

async def get_game_data(chat_id):
    data = db.getData(3, 'Night, AtNight', f"!ChatID = {chat_id}")
    return {
        'night': data[0][0],
        'actions': json.loads(data[0][1]) if data[0][1] else {'killed': -1, 'healed': -1}
    }

async def update_game_data(chat_id, data):
    db.writeData(3, 'AtNight', json.dumps(data), f"!ChatID = {chat_id}")

# ------------------------ Обработчики команд ------------------------
@dp.message_handler(commands=['startgame'])
async def start_game(message: types.Message):
    chat_id = message.chat.id
    players = db.getData(1, 'ID', f"!inGame = {chat_id} AND Alive = 1")
    
    if len(players) < 4:
        await send_to_group(chat_id, "❌ Недостаточно игроков для начала игры (минимум 4)")
        return
    
    # Распределение ролей
    roles = [2] + [3,4] + [1]*(len(players)-3)
    random.shuffle(roles)
    
    for i, player_id in enumerate(players):
        role_id = roles[i]
        db.writeData(1, 'role', role_id, player_id)
        try:
            role_info = ROLES[role_id]
            await bot.send_message(
                player_id,
                f"🎭 Ваша роль: {role_info['emoji']} {role_info['title']}\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"{db.getData(2, 'About', role_id)[0]}"
            )
            if role_id == 2:  # Мафия
                await send_mafia_actions(player_id, chat_id)
            elif role_id == 3:  # Доктор
                await send_doctor_actions(player_id, chat_id)
        except Exception as e:
            fprint(f"Ошибка отправки роли: {e}")
    
    await send_to_group(chat_id, "🌙 Ночь наступает! У игроков есть 2 минуты на действия!")
    await night_phase(chat_id)

async def send_mafia_actions(user_id, chat_id):
    players = db.getData(1, 'ID', f"!inGame = {chat_id} AND Alive = 1 AND role != 2")
    markup = InlineKeyboardMarkup()
    for player in players:
        markup.add(InlineKeyboardButton(
            f"👤 {db.getData(1, 'Nickname', player)[0]}",
            callback_data=f"kill_{player}"
        ))
    await bot.send_message(user_id, "🔫 Выберите жертву:", reply_markup=markup)

async def send_doctor_actions(user_id, chat_id):
    players = db.getData(1, 'ID', f"!inGame = {chat_id} AND Alive = 1")
    markup = InlineKeyboardMarkup()
    for player in players:
        markup.add(InlineKeyboardButton(
            f"👤 {db.getData(1, 'Nickname', player)[0]}",
            callback_data=f"heal_{player}"
        ))
    await bot.send_message(user_id, "🩺 Выберите кого вылечить:", reply_markup=markup)

# ------------------------ Фазы игры --------------------------------
async def night_phase(chat_id):
    db.writeData(3, 'Night', (await get_game_data(chat_id))['night'] + 1, f"!ChatID = {chat_id}")
    await asyncio.sleep(PHASE_TIMEOUTS['night'])
    
    game_data = await get_game_data(chat_id)
    killed = game_data['actions']['killed']
    healed = game_data['actions']['healed']
    
    if healed != killed and killed != -1:
        db.writeData(1, 'Alive', 0, killed)
        await send_to_group(chat_id, f"☀️ Утро! Было совершено убийство! Жертва: {db.getData(1, 'Nickname', killed)[0]}")
    else:
        await send_to_group(chat_id, "☀️ Утро! Прошла спокойная ночь без происшествий!")
    
    await day_phase(chat_id)

async def day_phase(chat_id):
    alive_players = db.getData(1, 'ID', f"!inGame = {chat_id} AND Alive = 1")
    markup = InlineKeyboardMarkup()
    for player in alive_players:
        markup.add(InlineKeyboardButton(
            f"👤 {db.getData(1, 'Nickname', player)[0]}",
            callback_data=f"vote_{player}"
        ))
    
    await send_to_group(chat_id, "🗳️ Начинаем дневное голосование! Выберите игрока для исключения:", reply_markup=markup)
    await asyncio.sleep(PHASE_TIMEOUTS['day'])
    
    # Логика подсчета голосов
    votes = {}
    messages = await bot.get_chat(chat_id).get_messages()
    for msg in messages:
        if msg.reply_markup:
            for btn in msg.reply_markup.inline_keyboard:
                if btn[0].callback_data.startswith('vote_'):
                    user_id = int(btn[0].callback_data.split('_')[1])
                    votes[user_id] = votes.get(user_id, 0) + 1
    
    if votes:
        excluded = max(votes, key=votes.get)
        db.writeData(1, 'Alive', 0, excluded)
        await send_to_group(chat_id, f"⚖️ Игрок {db.getData(1, 'Nickname', excluded)[0]} исключен!")
    else:
        await send_to_group(chat_id, "🔄 Никто не получил большинства голосов")
    
    await check_win_condition(chat_id)

# ------------------------ Обработчики действий ----------------------
@dp.callback_query_handler(lambda c: c.data.startswith('kill_'))
async def process_kill(callback: CallbackQuery):
    killer_id = callback.from_user.id
    victim_id = int(callback.data.split('_')[1])
    chat_id = db.getData(1, 'inGame', killer_id)[0]
    
    game_data = await get_game_data(chat_id)
    game_data['actions']['killed'] = victim_id
    await update_game_data(chat_id, game_data)
    await callback.answer("✅ Выбор сохранен!")

@dp.callback_query_handler(lambda c: c.data.startswith('heal_'))
async def process_heal(callback: CallbackQuery):
    doctor_id = callback.from_user.id
    patient_id = int(callback.data.split('_')[1])
    chat_id = db.getData(1, 'inGame', doctor_id)[0]
    
    game_data = await get_game_data(chat_id)
    game_data['actions']['healed'] = patient_id
    await update_game_data(chat_id, game_data)
    await callback.answer("✅ Выбор сохранен!")

# ------------------------ Проверка победы --------------------------
async def check_win_condition(chat_id):
    mafia = db.getData(1, 'ID', f"!inGame = {chat_id} AND Alive = 1 AND role = 2")
    civilians = db.getData(1, 'ID', f"!inGame = {chat_id} AND Alive = 1 AND role != 2")
    
    if len(mafia) == 0:
        await send_to_group(chat_id, "🎉 Мирные жители победили!")
        await end_game(chat_id)
    elif len(mafia) >= len(civilians):
        await send_to_group(chat_id, "🎉 Мафия победила!")
        await end_game(chat_id)
    else:
        await night_phase(chat_id)

async def end_game(chat_id):
    db.writeData(3, 'Night', 1, f"!ChatID = {chat_id}")
    db.writeData(3, 'AtNight', '{"killed":-1,"healed":-1}', f"!ChatID = {chat_id}")
    db.writeData(1, 'inGame', -1, f"!inGame = {chat_id}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)