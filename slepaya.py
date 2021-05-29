from math import ceil
from os import getenv
import random
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler
import boto3
from pylunar import MoonInfo
from markovify import NewlineText
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton


AWS_KEY_ID = getenv('AWS_KEY_ID', None)
AWS_SECRET = getenv('AWS_SECRET', None)
TOKEN = getenv('BOT_TOKEN', None)

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

slepaya = telebot.TeleBot(TOKEN)

markup = ReplyKeyboardMarkup(resize_keyboard=True)

markup.row(KeyboardButton('Верный совет'),
           KeyboardButton('Чудной совет'),
           KeyboardButton('Команды'))
markup.row(KeyboardButton('Подписаться'),
           KeyboardButton('Отписаться'),
           KeyboardButton('Справка'))


quotes_markof = open('quotes.txt').read()
quotes = quotes_markof.splitlines()

scheduler = BackgroundScheduler()


@slepaya.message_handler(commands=['start'])
def send_welcome(message: telebot.types.Message):
    cid = message.chat.id
    print(f"LOGS: [START] {cid} - {message.from_user.username}")
    slepaya.send_message(cid, f"Здравствуй, {message.from_user.first_name}")
    sleep(0.5)
    slepaya.send_message(cid, "Ничего не говори, знаю")
    sleep(0.6)
    slepaya.send_message(cid, "За советом тебя ко мне отправили",
                         reply_markup=markup)


@slepaya.message_handler(commands=['sub'])
def subscribe(message: telebot.types.Message):
    cid = message.chat.id
    item = {'chat_id': str(cid)}

    dynamo_db = boto3.resource('dynamodb',
                           aws_access_key_id=AWS_KEY_ID,
                           aws_secret_access_key=AWS_SECRET,
                           region_name='eu-north-1')

    table = dynamo_db.Table('users')

    try:
        # User is subbed -> do nothing
        table.get_item(Key=item)['Item']
        slepaya.send_message(cid, "Моя внучка тебя уже записывала",
                             reply_markup=markup)
    except KeyError:
        # User is not subbed -> add to dynamo db
        slepaya.send_message(cid, "Что-ж, ладно, внучка моя запишет тебя")
        sleep(0.4)
        slepaya.send_message(cid, "Раз в 3 дня в 9:33 по часам московским " +
                                  "буду советом тебя одаривать")

        table.put_item(Item=item)
        print(f"LOGS: [SUB] {cid} - {message.from_user.username}")

        slepaya.send_message(cid, "Ну все, ступай с миром")
        slepaya.send_message(cid, "Советом тебя не обделю",
                             reply_markup=markup)


@slepaya.message_handler(regexp=r'Подписаться')
def subscribe_reg(message: telebot.types.Message):
    subscribe(message)


@slepaya.message_handler(commands=['unsub'])
def unsubscribe(message: telebot.types.Message):
    cid = message.chat.id
    name = message.from_user.first_name
    item = {'chat_id': str(cid)}

    dynamo_db = boto3.resource('dynamodb',
                               aws_access_key_id=AWS_KEY_ID,
                               aws_secret_access_key=AWS_SECRET,
                               region_name='eu-north-1')
    table = dynamo_db.Table('users')

    try:
        # User is subbed -> unsubscribe
        table.get_item(Key=item)['Item']

        slepaya.send_message(cid, f"Ох, ох, {name}, что-ж делать-то...")
        sleep(0.8)
        slepaya.send_message(cid, "Ладно, сейчас попрошу внучку " +
                             "тебя убрать из списка")
        table.delete_item(Key=item)
        print(f"LOGS: [UNSUB] {cid} - {message.from_user.username}")
        sleep(0.9)
        slepaya.send_message(cid, "Внучка выписала тебя из тетрадки")
        slepaya.send_message(cid, "Помни одно - ты всегда ко мне " +
                             "можешь обратиться", reply_markup=markup)
    except KeyError:
        # User is not subbed -> do nothing
        slepaya.send_message(cid, "А тебя еще не записывали")
        slepaya.send_message(cid, "Могу попросить мою внучку тебя записать")
        slepaya.send_message(cid, "/sub (Подписаться)", reply_markup=markup)


@slepaya.message_handler(regexp=r'Отписаться')
def unsubscribe_reg(message: telebot.types.Message):
    unsubscribe(message)


@slepaya.message_handler(commands=['advice'])
def send_random_quote(message: telebot.types.Message):
    quote = random.choice(quotes)
    cid = message.chat.id
    slepaya.send_message(cid, quote, reply_markup=markup)
    print(f"LOGS: [ADVICE] {cid} - {message.from_user.username}")


@slepaya.message_handler(regexp=r'Верный совет')
def send_random_quote_reg(message: telebot.types.Message):
    send_random_quote(message)


@slepaya.message_handler(commands=['badvice'])
def send_generated_quote(message: telebot.types.Message):
    cid = message.chat.id
    # text = generate_quote('quotes.txt')
    text = NewlineText(quotes_markof).make_sentence()
    if text:
        slepaya.send_message(cid, text)
        slepaya.send_message(cid, "Так сказал дух древний, " +
                             "посетивший меня только что", reply_markup=markup)
    else:
        slepaya.send_message(cid, "Дух древний промолчал", reply_markup=markup)
    print(f"LOGS: [BADVICE] {cid} - {message.from_user.username}")


@slepaya.message_handler(regexp=r'Чудной совет')
def send_generated_quote_reg(message: telebot.types.Message):
    send_generated_quote(message)


@slepaya.message_handler(commands=['info'])
def send_info(message: telebot.types.Message):
    cid = message.chat.id
    slepaya.send_message(cid, "Сказавши мне /badvice, " +
                         "получишь мудрость чудную")
    sleep(0.5)
    slepaya.send_message(cid, "Их мне дух древний подсказывает, а я тебе пишу")
    sleep(0.4)
    slepaya.send_message(cid, "Дух говорит, что эти мудрости " +
                         "из Марковской цепи берет")
    sleep(0.6)
    slepaya.send_message(cid, "А что это за зверь такой, Марковские цепи, " +
                         "можно в ваших Интернетах посмотреть",
                         reply_markup=markup)


@slepaya.message_handler(regexp=r'Справка')
def send_info_reg(message: telebot.types.Message):
    send_info(message)


@slepaya.message_handler(commands=['help'])
def send_help(message: telebot.types.Message):
    cid = message.chat.id
    txt = """/advice (Верный совет) - Баба Нина одарит Вас мудростью случайной
    /badvice (Чудной совет) - Святой Дух посетит бабу Нину
    /sub (Подписаться) - Баба Нина будет одаривать Вас мудростью каждый третий день
    /unsub (Отписаться) - Отказаться от мудростей бабы Нины каждые 3 дня
    /info (Справка) - Откуда мудрости /badvice духа древнего берутся
    /help (Команды) - Какие услуги могу оказать тебе
    """
    slepaya.send_message(cid, "Вот что жду от тебя услышать")
    sleep(0.6)
    slepaya.send_message(cid, txt)


@slepaya.message_handler(regexp=r'Команды')
def send_help_reg(message: telebot.types.Message):
    send_help(message)


@slepaya.message_handler(commands=['testnotif'])
def test_notification(message: telebot.types.Message):
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


@slepaya.message_handler(func=lambda message: True)
def reply_to_others(message: telebot.types.Message):
    slepaya.reply_to(message, "Ишь ты - за словом в карман не лезешь",
                     reply_markup=markup)


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

        except telebot.apihelper.ApiTelegramException as e:
            err_desc = e.result_json['description']
            print(f"LOGS: [NOTIFICATIONS_EXCEPTION] {err_desc} {c_id}")

        finally:
            total_counter += 1

    print(f"LOGS: [NOTIFICATIONS_STAT] Send to {send_counter}/{total_counter}")


scheduler.start()
slepaya.polling(none_stop=True)
