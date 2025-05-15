import json
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import db
import aiogram.utils.exceptions as aigramExceptions
from config import fprint, MAX_PLAYERS, TOKEN

# ------------------------ Инициализация бота -----------------------
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

db.connectTo('bot.db')

# ------------------------ Состояния регистрации --------------------


class Registration(StatesGroup):
    nickname = State()


# ------------------------ Константы и утилиты -----------------------
PHASE_TIMEOUTS = {'night': 60, 'day': 60}
ROLES = {
    1: {'title': 'Мирный житель', 'emoji': '👨🌾', 'color': '#27ae60', 'about': 'Ваша цель - выжить и выявить всех членов мафии путем голосования.'},
    2: {'title': 'Мафия', 'emoji': '🔫', 'color': '#c0392b', 'about': 'Ночью вы устраняете мирных жителей, днем стараетесь не попасться.'},
    3: {'title': 'Доктор', 'emoji': '🩺', 'color': '#2980b9', 'about': 'Каждую ночь вы можете выбрать одного игрока для лечения.'},
    4: {'title': 'Комиссар', 'emoji': '🕵️', 'color': '#8e44ad', 'about': 'Ночью вы можете проверить роль одного игрока.'}
}


async def send_to_group(chat_id, text, reply_markup=None):
    await bot.send_message(chat_id, f"👮 Ведущий: {text}", reply_markup=reply_markup)


async def get_game_data(chat_id):
    data = db.getData(3, ('Night', 'AtNight', 'MessageID'),
                      f"!ChatID = {chat_id}", All=True)
    return {
        'night': data[0][0],
        'actions': json.loads(data[0][1]) if data[0][1] else {'killed': -1, 'healed': -1},
        'message_id': data[0][2]
    }


async def update_game_data(chat_id, data):
    db.writeData(3, 'AtNight', (json.dumps(data)), f"!ChatID = {chat_id}")

# ------------------------ Обработчики команд ------------------------


@dp.message_handler(commands=['start'], chat_type=types.ChatType.PRIVATE)
async def cmd_start_private(message: types.Message):
    user_id = message.from_user.id
    if db.getData(1, 'ID', user_id, All=True):
        await message.answer("✅ Вы уже зарегистрированы!")
        return

    await message.answer("📝 Введите ваш игровой никнейм (3-20 символов, только буквы и цифры):")
    await Registration.nickname.set()


@dp.message_handler(commands=['start'], chat_type=[types.ChatType.GROUP, types.ChatType.SUPERGROUP])
async def cmd_start_group(message: types.Message):
    user_id = message.from_user.id
    if not db.getData(1, 'ID', user_id, All=True):
        await message.reply("⚠️ Для участия в игре нужно зарегистрироваться!\nПерейдите в личные сообщения с ботом и напишите /start")


@dp.message_handler(state=Registration.nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    nickname = message.text.strip()

    if not (3 <= len(nickname) <= 20):
        await message.answer("❌ Никнейм должен быть от 3 до 20 символов!")
        return

    if not nickname.isalnum():
        await message.answer("❌ Можно использовать только буквы и цифры!")
        return

    if db.getData(1, 'ID', f"!Nickname = '{nickname}'", All=True):
        await message.answer("❌ Этот никнейм уже занят!")
        return

    user_id = message.from_user.id
    db.writeData(1, ('ID', 'Nickname', 'inGame', 'Alive', 'role'),
                 (user_id, nickname, -1, 0, -1), qvest=None)

    await message.answer(f"🎉 Регистрация завершена, {nickname}!\nТеперь вы можете участвовать в играх!")
    await state.finish()


@dp.message_handler(commands=['startgame'])
async def cmd_start_game(message: types.Message):
    chat_id = message.chat.id

    if db.getData(3, 'ChatID', f"!ChatID = {chat_id}", All=True) != []:
        await send_to_group(chat_id, "❌ В этом чате уже есть активная игра!\nЕё можно завершить и начать новый набор используйте /endgame")
        return

    creator_id = message.from_user.id
    if not db.getData(1, 'ID', creator_id, All=True):
        await message.reply("❌ Сначала зарегистрируйтесь через /start в ЛС!")
        return

    db.writeData(3, ('ChatID', 'Night', 'AtNight', 'MessageID', 'CreatorID'),
                 (chat_id, 1, '{"killed":-1,"healed":-1}', -1, creator_id))

    db.writeData(1, ('inGame', 'Alive', 'role'), (chat_id, 1, -1), creator_id)

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎮 Присоединиться",
                             callback_data=f"join_{chat_id}"),
        InlineKeyboardButton("🚀 Начать игру", callback_data=f"start_{chat_id}")
    )

    players = db.getData(
        1, 'Nickname', f"!inGame = {chat_id} AND Alive = 1", All=True)
    players_list = "\n".join(
        [f"👉 {name}" for name in players]) if players else ""

    msg = await bot.send_message(
        chat_id,
        f"🎉 Начинаем новую игру в Мафию!\n"
        f"👥 Игроков: {len(players)}/{MAX_PLAYERS}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"Участники:\n{players_list}",
        reply_markup=markup
    )

    db.writeData(3, 'MessageID', msg.message_id, f"!ChatID = {chat_id}")


@dp.message_handler(commands=['endgame'])
async def cmd_end_game(message: types.Message):
    chat_id = message.chat.id
    msg_id = db.getData(3, 'MessageID', f"!ChatID = {chat_id}")

    if not msg_id:
        await send_to_group(chat_id, "❌ В этом чате не запущена игра!\nЕё можно начать используя /startgame")
        return

    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception as e:
        pass

    await end_game(chat_id)

# ------------------------ Callback обработчики ----------------------


@dp.callback_query_handler(lambda c: c.data.startswith('join_'))
async def process_join(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[1])
    user_id = callback.from_user.id

    if not db.getData(1, 'ID', user_id, All=True):
        await callback.answer("❌ Сначала зарегистрируйтесь через /start в ЛС!", show_alert=True)
        return

    players = db.getData(
        1, 'Nickname', f"!inGame = {chat_id} AND Alive = 1", All=True)
    if len(players) >= MAX_PLAYERS:
        await callback.answer("❌ Достигнут максимум игроков!")
        return

    current_game = db.getData(1, 'inGame', user_id, All=True)
    if current_game and current_game[0] not in [-1, chat_id]:
        await callback.answer("❌ Вы уже в другой игре!")
        return

    db.writeData(1, ('inGame', 'Alive', 'role', 'Checked'),
                 (chat_id, 1, -1, 0), user_id)
    await callback.answer("✅ Вы успешно присоединились!")
    players = db.getData(
        1, 'Nickname', f"!inGame = {chat_id} AND Alive = 1", All=True)
    players_list = "\n".join(
        [f"👉 {name}" for name in players]) if players else ""

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎮 Присоединиться",
                             callback_data=f"join_{chat_id}"),
        InlineKeyboardButton("🚀 Начать игру", callback_data=f"start_{chat_id}")
    )

    await callback.message.edit_text(
        text=f"🎉 Начинаем новую игру в Мафию!\n"
        f"👥 Игроков: {len(players)}/{MAX_PLAYERS}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"Участники:\n{players_list}",
        reply_markup=markup,
    )


@dp.callback_query_handler(lambda c: c.data.startswith('start_'))
async def process_start(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[1])
    user_id = callback.from_user.id

    creator = db.getData(
        3, 'CreatorID', f"!ChatID = {chat_id}")
    if user_id != creator:
        await callback.answer("❌ Только создатель игры может её начать!")
        return

    players = db.getData(
        1, 'ID', f"!inGame = {chat_id} AND Alive = 1", All=True)
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
    except Exception as e:
        fprint(f"Ошибка изменения сообщения: {e}")

    await start_game_logic(chat_id)

# ------------------------ Игровая логика ----------------------------


async def start_game_logic(chat_id):
    players = db.getData(
        1, 'ID', f"!inGame = {chat_id} AND Alive = 1", All=True)
    players = [p for p in players]

    roles = [2, 3, 4] + [1]*(len(players)-3)
    random.shuffle(roles)
    random.shuffle(players)

    for i in range(len(players)):
        role_id = roles[i]
        player_id = players[i]
        db.writeData(1, 'role', (role_id), f"!ID = {player_id}")
        try:
            role_info = ROLES[role_id]
            await bot.send_message(
                player_id,
                f"🎭 Ваша роль: {role_info['emoji']} {role_info['title']}\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"{role_info['about']}"
            )
        except Exception as e:
            fprint(f"Ошибка отправки роли: {e}")

    await night_phase(chat_id)


async def send_mafia_actions(user_id, chat_id):
    players = db.getData(1, ('ID', 'Nickname'),
                         f"!inGame = {chat_id} AND Alive = 1 AND role != 2",
                         All=True)
    markup = InlineKeyboardMarkup()
    for player_id, nickname in players:
        markup.add(InlineKeyboardButton(
            f"👤 {nickname}",
            callback_data=f"kill_{player_id}"
        ))
    await bot.send_message(user_id, "🔫 Выберите жертву:", reply_markup=markup)


async def send_doctor_actions(user_id, chat_id):
    players = db.getData(1, ('ID', 'Nickname'),
                         f"!inGame = {chat_id} AND Alive = 1",
                         All=True)
    markup = InlineKeyboardMarkup()
    for player_id, nickname in players:
        markup.add(InlineKeyboardButton(
            f"👤 {nickname}",
            callback_data=f"heal_{player_id}"
        ))
    await bot.send_message(user_id, "🩺 Выберите кого вылечить:", reply_markup=markup)


async def send_sherif_actions(user_id, chat_id):
    players = db.getData(1, ('ID', 'Nickname', 'role', 'Checked'),
                         f"!inGame = {chat_id} AND Alive = 1 AND Role != 4",
                         All=True)
    markup = InlineKeyboardMarkup()
    ch = {
        1: '👤',
        2: '🔫',
        3: '🩺',
        0: '😶‍🌫️'
    }
    for player_id, nickname, role, checked in players:
        emoji = ch[0] if not checked else ch.get(role, '❓')
        markup.add(InlineKeyboardButton(
            f"{emoji} {nickname}",
            callback_data=f"check_{player_id}"
        ))
    await bot.send_message(user_id,
                           "🔍 Выберите, чью роль хотите узнать:\n"
                           "😶‍🌫️ - неизвестный\n"
                           "🔫 - мафия\n"
                           "🩺 - доктор\n"
                           "👤 - мирный",
                           reply_markup=markup)


async def night_phase(chat_id):
    await send_to_group(chat_id, "🌙 Ночь наступает! У игроков есть 2 минуты на действия!")
    mafia = db.getData(1, 'ID',
                       f"!inGame = {chat_id} AND Alive = 1 AND role = 2")
    if mafia:
        await send_mafia_actions(mafia, chat_id)

    doctor = db.getData(1, 'ID',
                        f"!inGame = {chat_id} AND Alive = 1 AND role = 3")

    if doctor:
        await send_doctor_actions(doctor, chat_id)

    sherifs = db.getData(1, 'ID',
                         f"!inGame = {chat_id} AND Alive = 1 AND role = 4")
    if sherifs:
        await send_sherif_actions(sherifs, chat_id)

    fprint('------------------------------------------- Запуск таймера', type='T1 C5')
    await asyncio.sleep(PHASE_TIMEOUTS['night'])
    fprint('------------------------------------------- Окончание таймера', type='T1 C5')

    game_data = await get_game_data(chat_id)
    killed = game_data['actions']['killed']
    healed = game_data['actions']['healed']

    if killed != -1 and killed != healed:
        db.writeData(1, 'Alive', (0), f"!ID = {killed}")
        await send_to_group(chat_id, f"☀️ Утро! Было совершено убийство! Жертва: {db.getData(1, 'Nickname', killed)}")
    else:
        await send_to_group(chat_id, "☀️ Утро! Прошла спокойная ночь без происшествий!")

    await day_phase(chat_id)


async def day_phase(chat_id):
    alive_players = db.getData(1, ('ID', 'Nickname'),
                               f"!inGame = {chat_id} AND Alive = 1",
                               All=True)
    markup = InlineKeyboardMarkup()
    voites = {

    }
    nicknames = {

    }
    for player_id, nickname in alive_players:
        voites[player_id] = 0
        nicknames[player_id] = nickname
        markup.add(InlineKeyboardButton(
            f"👤 {nickname}",
            callback_data=f"vote_{player_id}"
        ))

    db.writeData(3, 'voites', json.dumps(voites), f"!ChatID = {chat_id}")
    db.writeData(
        1, 'Voit', 0, f'!ID IN ({", ".join(map(str, voites.keys()))})')
    await send_to_group(chat_id, "🗳️ Начинаем дневное голосование! Выберите игрока для исключения:", reply_markup=markup)

    await asyncio.sleep(PHASE_TIMEOUTS['day'])
    voites = json.loads(db.getData(3, 'voites', f"!ChatID = {chat_id}"))
    sorted_votes = sorted(
        voites.items(), key=lambda item: item[1], reverse=True)
    if len(sorted_votes) > 1 and sorted_votes[0][1] == sorted_votes[1][1]:
        excluded = None
    else:
        excluded = sorted_votes[0][0]

    stat = ''

    for id in list(voites.keys()):
        stat = f'{stat}\n{nicknames[int(id)]} - {voites[str(id)]}'

    if excluded:
        db.writeData(1, 'Alive', (0), f"!ID = {excluded}")
        await send_to_group(chat_id, f"⚖️ Игрок {db.getData(1, 'Nickname', excluded)} исключен!\n Распределение голосов: {stat}")
    else:
        await send_to_group(chat_id, f"🔄 Никто не получил большинства голосов\n Распределение голосов: {stat}")

    await check_win_condition(chat_id)


async def check_win_condition(chat_id):
    mafia = db.getData(1, 'ID',
                       f"!inGame = {chat_id} AND Alive = 1 AND role = 2",
                       All=True)
    civilians = db.getData(1, 'ID',
                           f"!inGame = {chat_id} AND Alive = 1 AND role != 2",
                           All=True)

    if not mafia:
        await send_to_group(chat_id, "🎉 Мирные жители победили!")
        await end_game(chat_id)
    elif len(mafia) >= len(civilians):
        await send_to_group(chat_id, "🎉 Мафия победила!")
        await end_game(chat_id)
    else:
        await night_phase(chat_id)


async def check_game(chat_id):
    return bool(db.getData(3, 'ID', f"!ChatID = {chat_id}", All=True))


async def end_game(chat_id):
    players = db.getData(1, ('Nickname', 'role'),
                         f"!inGame = {chat_id}",
                         All=True)
    stat = '\n'
    for nickname, role in players:
        stat = f'{stat}\n{nickname} - {ROLES[role]["title"]}{ROLES[role]["emoji"]}'
    await send_to_group(chat_id, f"🏁 Игра завершена! Спасибо за участие!\n Роли игрков: {stat}")
    db.writeData(1, ('inGame', 'Alive', 'role', 'Checked'),
                 (-1, 1, -1, 0),
                 f"!inGame = {chat_id}")
    db.DeleteData(3, f"!ChatID = {chat_id}")


@dp.callback_query_handler(lambda c: c.data.startswith('kill_'))
async def process_kill(callback: CallbackQuery):
    victim_id = int(callback.data.split('_')[1])
    chat_id = db.getData(1, 'inGame', callback.from_user.id)

    game_data = await get_game_data(chat_id)
    game_data['actions']['killed'] = victim_id
    await update_game_data(chat_id, game_data['actions'])
    await callback.message.edit_text("✅ Жертва выбрана!")


@dp.callback_query_handler(lambda c: c.data.startswith('vote_'))
async def process_kill(callback: CallbackQuery):
    victim_id = int(callback.data.split('_')[1])
    chat_id = db.getData(1, 'inGame', callback.from_user.id)

    aboutPlayer = db.getData(1, ('Voit', 'Alive'), callback.from_user.id)

    if aboutPlayer[0] == 0:
        if int(aboutPlayer[1]) == 1:
            votes = json.loads(db.getData(3, 'voites', f"!ChatID = {chat_id}"))
            votes[str(victim_id)] += 1
            await callback.answer('Твой голос принят ✅')
            db.writeData(3, 'voites', json.dumps(
                votes), f'!ChatID = {chat_id}')
            db.writeData(1, 'voit', 1, callback.from_user.id)
        else:
            await callback.answer('Мертвые - не голосуют ❌')
    else:
        await callback.answer('Ты уже голосовал ❌')


@dp.callback_query_handler(lambda c: c.data.startswith('heal_'))
async def process_heal(callback: CallbackQuery):
    patient_id = int(callback.data.split('_')[1])
    chat_id = db.getData(1, 'inGame', callback.from_user.id)

    game_data = await get_game_data(chat_id)
    game_data['actions']['healed'] = patient_id
    await update_game_data(chat_id, game_data['actions'])
    await callback.message.edit_text("✅ Пациент выбран!")


@dp.callback_query_handler(lambda c: c.data.startswith('check_'))
async def process_check(callback: CallbackQuery):
    checked_id = int(callback.data.split('_')[1])
    role = db.getData(1, 'role', checked_id)
    role_name = ROLES[role]['title']
    db.writeData(1, 'Checked', (1), f"!ID = {checked_id}")
    await callback.message.edit_text(f"Роль игрока: {role_name}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
