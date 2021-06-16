from math import ceil
from os import getenv
import random
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler
import boto3
from botocore.exceptions import (
    ConnectTimeoutError, ConnectionClosedError, 
    ConnectionError, NoCredentialsError, NoCredentialsError)
from pylunar import MoonInfo
from markovify import NewlineText
from telebot import TeleBot, apihelper
from telebot.types import KeyboardButton, Message, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

from typing import List
from utils import searcher, ending_decider, QuotesModel


AWS_KEY_ID = getenv('AWS_KEY_ID', None)
AWS_SECRET = getenv('AWS_SECRET', None)
TOKEN = getenv('BOT_TOKEN', getenv('LAYER_BOT_TOKEN'))

MOSCOW_LOCATION = ((55, 45, 21), (-37, 37, 2))
MOON_PHASE_TEXT_EMOJI = {
    'NEW_MOON': ('новолуние', '🌑'),
    'WAXING_CRESCENT': ('молодая луна', '🌒'),
    'FIRST_QUARTER': ('первая четверть', '🌓'),
    'WAXING_GIBBOUS': ('прибывающая луна', '🌔'),
    'FULL_MOON': ('полнолуние', '🌕'),
    'WANING_GIBBOUS': ('убывающая луна', '🌖'),
    'LAST_QUARTER': ('последняя четверть', '🌗'),
    'WANING_CRESCENT': ('старая луна', '🌘')
}

COMMANDS_MESSAGE = ("/advice (Случайная примета) - Баба Нина одарит Вас мудростью случайной\n"
                    "/badvice (Сгенерировать примету) - Баба Нина придумает примету\n"
                    "/sub (Подписка) - Баба Нина будет одаривать Вас мудростью каждый третий день\n"
                    "/unsub (Отписка) - Отказаться от мудростей бабы Нины каждые 3 дня\n"
                    "/help (Команды) - Какие услуги могу оказать тебе\n"
                    "/search (Поиск) - Поиск по приметам")

INFO_MESSAGE = ('Сказавши мне "Сгенерировать примету" (/badvice), получишь мудрость чудную ☝️\n\n'
                'Их мне дух древний 👻 подсказывает, а я тебе пишу.\n\n'
                'Дух говорит, что эти мудрости из нейронной сети 🧠 LSTM берет\n\n'
                'А что это за зверь такой, LSTM, можно в ваших Интернетах 🌐 посмотреть по кнопке 👇')

MAIN_MARKUP = ReplyKeyboardMarkup(resize_keyboard=True)
MAIN_MARKUP.row(KeyboardButton('Случайная примета 🔀'),
                KeyboardButton('Генерация приметы 🎲'))
MAIN_MARKUP.row(KeyboardButton('Команды 📄'),
                KeyboardButton('Поиск 🔍'))
MAIN_MARKUP.row(KeyboardButton('Подписка 📥'),
                KeyboardButton('Отписка 📤'))

FOUND_QUOTES_MARKUP = ReplyKeyboardMarkup(resize_keyboard=True)
FOUND_QUOTES_MARKUP.row(KeyboardButton("Еще примету ⏭️"),
                        KeyboardButton("Достаточно 🛑"))

slepaya = TeleBot(TOKEN)

quotes_markof = open('quotes.txt').read()
quotes = quotes_markof.splitlines()

scheduler = BackgroundScheduler()

# Load model and generate one quote to warm it up
model = QuotesModel()
model.generate_next()
print('[LOGS] Ready!')

@slepaya.message_handler(commands=['start'])
def send_welcome(message: Message):
    cid = message.chat.id
    print(f"LOGS: [START] {cid}({message.from_user.username})")
    slepaya.send_message(cid, f"Здравствуй, {message.from_user.first_name}")
    sleep(0.5)
    slepaya.send_message(cid, "Ничего не говори 🤐, знаю...")
    sleep(0.6)
    slepaya.send_message(cid, "За советом тебя ко мне отправили ☝️",
                         reply_markup=MAIN_MARKUP)


@slepaya.message_handler(commands=['sub'])
def subscribe(message: Message):
    cid = message.chat.id
    item = {'chat_id': str(cid)}
    dynamo_db = boto3.resource('dynamodb', aws_access_key_id=AWS_KEY_ID,
                               aws_secret_access_key=AWS_SECRET, region_name='eu-north-1')

    table = dynamo_db.Table('users')

    try:
        # User is subbed -> do nothing
        table.get_item(Key=item)['Item']
        slepaya.send_message(cid, "Моя внучка тебя уже записывала",
                             reply_markup=MAIN_MARKUP)
    except KeyError:
        # User is not subbed -> add to dynamo db
        slepaya.send_message(cid, "Что-ж, ладно, внучка моя запишет тебя")
        sleep(0.4)
        slepaya.send_message(cid, "Раз в 3 дня в 9:33 по часам московским " +
                                  "буду советом тебя одаривать")

        table.put_item(Item=item)
        print(f"LOGS: [SUB] {cid}({message.from_user.username})")

        slepaya.send_message(cid, "Ну все, ступай с миром")
        slepaya.send_message(cid, "Советом тебя не обделю",
                             reply_markup=MAIN_MARKUP)
    except (ConnectTimeoutError, ConnectionClosedError, ConnectionError, NoCredentialsError, NoCredentialsError):
        slepaya.send_message(cid, "Ой-ой-ой, что-то не могу найти тетрадку со своими подписчиками")


@slepaya.message_handler(regexp=r'Подписка')
def subscribe_reg(message: Message):
    subscribe(message)


@slepaya.message_handler(commands=['unsub'])
def unsubscribe(message: Message):
    cid = message.chat.id
    name = message.from_user.first_name
    item = {'chat_id': str(cid)}
    
    dynamo_db = boto3.resource('dynamodb', aws_access_key_id=AWS_KEY_ID,
                               aws_secret_access_key=AWS_SECRET, region_name='eu-north-1')
    
    table = dynamo_db.Table('users')

    try:
        # User is subbed -> unsubscribe
        table.get_item(Key=item)['Item']

        slepaya.send_message(cid, f"Ох, ох, {name}, что-ж делать-то...")
        sleep(0.8)
        slepaya.send_message(cid, "Ладно, сейчас попрошу внучку " +
                             "тебя убрать из списка")
        table.delete_item(Key=item)
        print(f"LOGS: [UNSUB] {cid}({message.from_user.username})")
        sleep(0.9)
        slepaya.send_message(cid, "Внучка выписала тебя из тетрадки")
        slepaya.send_message(cid, "Помни одно - ты всегда ко мне " +
                             "можешь обратиться", reply_markup=MAIN_MARKUP)
    except KeyError:
        # User is not subbed -> do nothing
        slepaya.send_message(cid, "А тебя еще не записывали")
        slepaya.send_message(cid, "Могу попросить мою внучку тебя записать")
        slepaya.send_message(cid, "/sub (Подписаться)", reply_markup=MAIN_MARKUP)
    except (ConnectTimeoutError, ConnectionClosedError, ConnectionError, NoCredentialsError, NoCredentialsError):
        slepaya.send_message(cid, "Ой-ой-ой, что-то не могу найти тетрадку со своими подписчиками",
                             reply_markup=MAIN_MARKUP)



@slepaya.message_handler(regexp=r'Отписка')
def unsubscribe_reg(message: Message):
    unsubscribe(message)


@slepaya.message_handler(commands=['advice'])
def send_random_quote(message: Message):
    quote = random.choice(quotes)
    cid = message.chat.id
    slepaya.send_message(cid, quote, reply_markup=MAIN_MARKUP)
    print(f"LOGS: [ADVICE] {cid}({message.from_user.username})")


@slepaya.message_handler(regexp=r'Случайная примета')
def send_random_quote_reg(message: Message):
    send_random_quote(message)


@slepaya.message_handler(commands=['badvice'])
def send_generated_quote(message: Message):
    cid = message.chat.id
    # text = generate_quote('quotes.txt')
    # text = NewlineText(quotes_markof).make_sentence()
    code, text = model.translate_generated(t=random.randint(22, 40), words=random.randint(8, 9))
    if code == 200:
        slepaya.send_message(cid, text.capitalize()+'...', reply_markup=MAIN_MARKUP)
        print(f"LOGS: [BADVICE] {cid}({message.from_user.username})")
    else:
        print(f"LOGS [BADVICE_EXCEPTION]: {code}: {text}")
        slepaya.send_message(cid, "Что-то потеряла я связь с духом. Может @cognomen поможет", reply_markup=MAIN_MARKUP)


@slepaya.message_handler(regexp=r'Генерация приметы')
def send_generated_quote_reg(message: Message):
    send_generated_quote(message)


@slepaya.message_handler(commands=['help'])
def send_help(message: Message):
    cid = message.chat.id
    lstm_button = InlineKeyboardMarkup()
    lstm_button.add(InlineKeyboardButton(text="LSTM Wiki",
                                         url="https://ru.wikipedia.org/wiki/Долгая_краткосрочная_память"))
    slepaya.send_message(cid, "Вот что жду от тебя услышать")
    sleep(0.6)
    slepaya.send_message(cid, text=COMMANDS_MESSAGE, reply_markup=MAIN_MARKUP)
    sleep(0.5)
    slepaya.send_message(cid, text=INFO_MESSAGE, reply_markup=lstm_button)


@slepaya.message_handler(regexp=r'Команды')
def send_help_reg(message: Message):
    send_help(message)


@slepaya.message_handler(commands=['testnotif'])
def test_notification(message: Message):
    cid = message.chat.id

    if message.from_user.username == 'cognomen':
        # Forming lunar day message
        moon_info = MoonInfo(*MOSCOW_LOCATION)
        moon_age, moon_phase = ceil(moon_info.age()), moon_info.phase_name()
        lunar_msg = (f"{random.choice(['За окном', 'На дворе', 'Сегодня', 'Теперича', 'Ныне'])} "
                    f"{moon_age} {random.choice(['лунные сутки', 'лунный день'])}, "
                    f"{' '.join(MOON_PHASE_TEXT_EMOJI.get(moon_phase, ['','']))}")

        # Forming 2nd message
        mes = ['вот что', 'скажу', 'тебе', 'сегодня']
        random.shuffle(mes)
        mes = ' '.join(mes).capitalize()

        quote = random.choice(quotes)

        final_msg = f"""{lunar_msg}\n\n{mes}\n\n{quote}"""
        slepaya.send_message(cid, final_msg)

    else:
        slepaya.send_message(cid, text="Куда лезешь?? Туда тебе нельзя")


@slepaya.message_handler(commands=['search'])
def start_search(message: Message):
    serch_markup = ReplyKeyboardMarkup(resize_keyboard=True,
                                       one_time_keyboard=True)
    serch_markup.add('Отмена')
    msg = slepaya.send_message(message.chat.id, "Напиши мне поисковый запрос...",
                               reply_markup=serch_markup)
    slepaya.register_next_step_handler(msg, search_procedure)


@slepaya.message_handler(regexp=r'Поиск')
def start_search_reg(message: Message):
    start_search(message)


def search_procedure(message: Message):
    cid = message.chat.id
    
    if message.text == 'Отмена':
        slepaya.send_message(cid, 'Ну на нет и суда нет', reply_markup=MAIN_MARKUP)
        return
    
    slepaya.reply_to(message, "Ищу в письменах моих по этому запросу, подожди")
    print(f"LOGS: [SEARCH] {cid}({message.from_user.username}): {message.text}")
    indices = searcher(message.text, quotes, cutoff=90)

    if indices:
        l = len(indices)
        if l == 1:
            slepaya.send_message(cid, "Нашлась всего 1 примета")
            sleep(0.5)
            slepaya.send_message(cid, quotes[indices[0]],
                                 reply_markup=MAIN_MARKUP)
            return
        else:
            random.shuffle(indices)
            last_index = indices.pop()
            slepaya.send_message(cid, quotes[last_index])
            sleep(0.5)
            msg = slepaya.send_message(cid, f"Нашла еще {l-1} {ending_decider(l, 'примет')}",
                                       reply_markup=FOUND_QUOTES_MARKUP)
            slepaya.register_next_step_handler(msg, send_other_found_quotes, indices)
            return
    else:
        slepaya.send_message(cid, "Такого мудреного слова нет в моих мудростях",
                             reply_markup=MAIN_MARKUP)
        return


def send_other_found_quotes(message: Message, indices: List[int]):
    cid = message.chat.id
    
    if not indices:
        slepaya.send_message(cid, "А примет больше не осталось",
                             reply_markup=MAIN_MARKUP)
        return
    if message.text.startswith("Достаточно"):
        slepaya.send_message(cid, "Хорошо", reply_markup=MAIN_MARKUP)
        return
    elif message.text.startswith('Еще примету'):
        msg = slepaya.send_message(cid, quotes[indices[0]],
                                   reply_markup=FOUND_QUOTES_MARKUP)
        slepaya.register_next_step_handler(msg, send_other_found_quotes, indices[1:])
        return


@slepaya.message_handler(func=lambda message: True)
def reply_to_others(message: Message):
    slepaya.reply_to(message, "Ишь ты - за словом в карман не лезешь",
                     reply_markup=MAIN_MARKUP)


@scheduler.scheduled_job("interval", start_date='2021-2-16 06:33:00',
                         hours=72, id='notifications')
def send_notifications():
    dynamo_db = boto3.resource('dynamodb',
                               aws_access_key_id=AWS_KEY_ID,
                               aws_secret_access_key=AWS_SECRET,
                               region_name='eu-north-1')
    table = dynamo_db.Table('users')
    ids = (i['chat_id'] for i in table.scan()['Items'])
    
    # Forming lunar day message
    moon_info = MoonInfo(*MOSCOW_LOCATION)
    moon_age, moon_phase = ceil(moon_info.age()), moon_info.phase_name()
    lunar_msg = (f"{random.choice(['За окном', 'На дворе', 'Сегодня', 'Теперича', 'Ныне'])} "
                f"{moon_age} {random.choice(['лунные сутки', 'лунный день'])}, "
                f"{' '.join(MOON_PHASE_TEXT_EMOJI.get(moon_phase, ['','']))}")

    # Forming 2nd message
    mes = ['вот что', 'скажу', 'тебе', 'сегодня']
    random.shuffle(mes)
    mes = ' '.join(mes).capitalize()

    send_counter, total_counter = 0, 0

    for c_id in ids:
        # Picking random quote for each user
        quote = random.choice(quotes)

        try:
            final_msg = f"""{lunar_msg}\n\n{mes}\n\n{quote}"""
            slepaya.send_message(c_id, final_msg)
            print(f"LOGS: [NOTIFICATIONS] send_notifications to {c_id}")
            send_counter += 1
            sleep(0.05)

        except apihelper.ApiTelegramException as e:
            err_desc = e.result_json['description']
            print(f"LOGS: [NOTIFICATIONS_EXCEPTION] {err_desc} {c_id}")

        finally:
            total_counter += 1

    print(f"LOGS: [NOTIFICATIONS_STAT] Send to {send_counter}/{total_counter}")


scheduler.start()

slepaya.enable_save_next_step_handlers(delay=2)
slepaya.load_next_step_handlers
slepaya.polling(none_stop=True)
