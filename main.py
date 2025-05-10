import json
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import db
from config import fprint, MAX_PLAYERS

# ------------------------ Инициализация бота -----------------------
API_TOKEN = 'YOUR_BOT_TOKEN'
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ------------------------ Константы и утилиты -----------------------
PHASE_TIMEOUTS = {'night': 60, 'day': 120}
ROLES = {
    1: {'title': 'Мирный житель', 'emoji': '👨🌾', 'color': '#27ae60'},
    2: {'title': 'Мафия', 'emoji': '🔫', 'color': '#c0392b'},
    3: {'title': 'Доктор', 'emoji': '🩺', 'color': '#2980b9'},
    4: {'title': 'Комиссар', 'emoji': '🕵️', 'color': '#8e44ad'}
}


async def send_to_group(chat_id, text):
    await bot.send_message(chat_id, f"👮♂️ Ведущий: {text}")


async def get_game_data(chat_id):
    data = db.getData(3, 'Night, AtNight, MessageID', f"!ChatID = {chat_id}")
    return {
        'night': data[0][0],
        'actions': json.loads(data[0][1]) if data[0][1] else {'killed': -1, 'healed': -1},
        'message_id': data[0][2]
    }


async def update_game_data(chat_id, data):
    db.writeData(3, 'AtNight', json.dumps(data), f"!ChatID = {chat_id}")

# ------------------------ Обработчики команд ------------------------


@dp.message_handler(commands=['startgame'])
async def cmd_start_game(message: types.Message):
    chat_id = message.chat.id

    if db.getData(3, 'ChatID', f"!ChatID = {chat_id}"):
        await send_to_group(chat_id, "❌ В этом чате уже есть активная игра!")
        return

    creator_id = message.from_user.id
    db.writeData(3, 'ChatID, Night, AtNight, MessageID',
                 (chat_id, 1, '{"killed":-1,"healed":-1}', -1), qvest=None)

    db.writeData(1, 'inGame, Alive, role',
                 (chat_id, 1, -1), f"!ID = {creator_id}")

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎮 Присоединиться",
                             callback_data=f"join_{chat_id}"),
        InlineKeyboardButton("🚀 Начать игру", callback_data=f"start_{chat_id}")
    )

    players = db.getData(1, 'Nickname', f"!inGame = {chat_id} AND Alive = 1")
    players_list = "\n".join([f"👉 {name[0]}" for name in players])

    msg = await bot.send_message(
        chat_id,
        f"🎉 Начинаем новую игру в Мафию!\n"
        f"👥 Игроков: {len(players)}/{MAX_PLAYERS}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"Участники:\n{players_list}",
        reply_markup=markup
    )

    db.writeData(3, 'MessageID', msg.message_id, f"!ChatID = {chat_id}")


async def update_game_lobby(chat_id):
    players = db.getData(1, 'Nickname', f"!inGame = {chat_id} AND Alive = 1")
    game_data = await get_game_data(chat_id)

    players_list = "\n".join([f"👉 {name[0]}" for name in players])
    new_text = (
        f"🎉 Начинаем новую игру в Мафию!\n"
        f"👥 Игроков: {len(players)}/{MAX_PLAYERS}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"Участники:\n{players_list}"
    )

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎮 Присоединиться",
                             callback_data=f"join_{chat_id}"),
        InlineKeyboardButton("🚀 Начать игру", callback_data=f"start_{chat_id}")
    )

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=game_data['message_id'],
            text=new_text,
            reply_markup=markup
        )
    except Exception as e:
        fprint(f"Ошибка обновления лобби: {e}")

# ------------------------ Callback обработчики ----------------------


@dp.callback_query_handler(lambda c: c.data.startswith('join_'))
async def process_join(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[1])
    user_id = callback.from_user.id

    current_players = db.getData(1, 'ID', f"!inGame = {chat_id} AND Alive = 1")
    if len(current_players) >= MAX_PLAYERS:
        await callback.answer("❌ Достигнут максимум игроков!")
        return

    current_game = db.getData(1, 'inGame', user_id)[0]
    if current_game != -1 and current_game != chat_id:
        await callback.answer("❌ Вы уже в другой игре!")
        return

    if not db.getData(1, 'ID', user_id):
        db.writeData(1, 'ID, Nickname, inGame, Alive, role',
                     (user_id, callback.from_user.full_name, chat_id, 1, -1), qvest=None)
    else:
        db.writeData(1, 'inGame, Alive, role',
                     (chat_id, 1, -1), f"!ID = {user_id}")

    await callback.answer("✅ Вы успешно присоединились!")
    await update_game_lobby(chat_id)


@dp.callback_query_handler(lambda c: c.data.startswith('start_'))
async def process_start(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[1])
    user_id = callback.from_user.id

    creator = db.getData(1, 'ID', f"!inGame = {chat_id} AND Alive = 1")[0][0]
    if user_id != creator:
        await callback.answer("❌ Только создатель игры может её начать!")
        return

    players = db.getData(1, 'ID', f"!inGame = {chat_id} AND Alive = 1")
    if len(players) < 4:
        await callback.answer("❌ Недостаточно игроков (минимум 4)!")
        return

    game_data = await get_game_data(chat_id)
    try:
        await bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=game_data['message_id'],
            reply_markup=None
        )
    except:
        pass

    await start_game_logic(chat_id)

# ------------------------ Игровая логика ----------------------------


async def start_game_logic(chat_id):
    players = db.getData(1, 'ID', f"!inGame = {chat_id} AND Alive = 1")

    roles = [2] + [3, 4] + [1]*(len(players)-3)
    random.shuffle(roles)

    for i, player_id in enumerate(players):
        role_id = roles[i]
        db.writeData(1, 'role', role_id, f"!ID = {player_id}")
        try:
            role_info = ROLES[role_id]
            await bot.send_message(
                player_id,
                f"🎭 Ваша роль: {role_info['emoji']} {role_info['title']}\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"{db.getData(2, 'About', role_id)[0]}"
            )
            if role_id == 2:
                await send_mafia_actions(player_id, chat_id)
            elif role_id == 3:
                await send_doctor_actions(player_id, chat_id)
        except Exception as e:
            fprint(f"Ошибка отправки роли: {e}")

    await send_to_group(chat_id, "🌙 Ночь наступает! У игроков есть 2 минуты на действия!")
    await night_phase(chat_id)


async def send_mafia_actions(user_id, chat_id):
    players = db.getData(
        1, 'ID', f"!inGame = {chat_id} AND Alive = 1 AND role != 2")
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


async def night_phase(chat_id):
    db.writeData(3, 'Night', (await get_game_data(chat_id))['night'] + 1, f"!ChatID = {chat_id}")
    await asyncio.sleep(PHASE_TIMEOUTS['night'])

    game_data = await get_game_data(chat_id)
    killed = game_data['actions']['killed']
    healed = game_data['actions']['healed']

    if healed != killed and killed != -1:
        db.writeData(1, 'Alive', 0, f"!ID = {killed}")
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
        db.writeData(1, 'Alive', 0, f"!ID = {excluded}")
        await send_to_group(chat_id, f"⚖️ Игрок {db.getData(1, 'Nickname', excluded)[0]} исключен!")
    else:
        await send_to_group(chat_id, "🔄 Никто не получил большинства голосов")

    await check_win_condition(chat_id)


@dp.callback_query_handler(lambda c: c.data.startswith('kill_'))
async def process_kill(callback: CallbackQuery):
    victim_id = int(callback.data.split('_')[1])
    chat_id = db.getData(1, 'inGame', callback.from_user.id)[0]

    game_data = await get_game_data(chat_id)
    game_data['actions']['killed'] = victim_id
    await update_game_data(chat_id, game_data)
    await callback.answer("✅ Жертва выбрана!")


@dp.callback_query_handler(lambda c: c.data.startswith('heal_'))
async def process_heal(callback: CallbackQuery):
    patient_id = int(callback.data.split('_')[1])
    chat_id = db.getData(1, 'inGame', callback.from_user.id)[0]

    game_data = await get_game_data(chat_id)
    game_data['actions']['healed'] = patient_id
    await update_game_data(chat_id, game_data)
    await callback.answer("✅ Пациент выбран!")


async def check_win_condition(chat_id):
    mafia = db.getData(
        1, 'ID', f"!inGame = {chat_id} AND Alive = 1 AND role = 2")
    civilians = db.getData(
        1, 'ID', f"!inGame = {chat_id} AND Alive = 1 AND role != 2")

    if len(mafia) == 0:
        await send_to_group(chat_id, "🎉 Мирные жители победили!")
        await end_game(chat_id)
    elif len(mafia) >= len(civilians):
        await send_to_group(chat_id, "🎉 Мафия победила!")
        await end_game(chat_id)
    else:
        await night_phase(chat_id)


async def end_game(chat_id):
    db.writeData(3, 'Night, AtNight',
                 (1, '{"killed":-1,"healed":-1}'), f"!ChatID = {chat_id}")
    db.writeData(1, 'inGame, Alive, role', (-1, 0, -1), f"!inGame = {chat_id}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
