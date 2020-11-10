# Default libraries
from datetime import datetime
from os import getenv
import random
from time import sleep

# Third party libraries
from apscheduler.schedulers.background import BackgroundScheduler
import boto3
from lunarcalendar import Solar, Converter
from markovify import NewlineText
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton


AWS_KEY_ID = getenv('AWS_KEY_ID', None)
AWS_SECRET = getenv('AWS_SECRET', None)
TOKEN = getenv('BOT_TOKEN', None)

slepaya = telebot.TeleBot(TOKEN)

markup = ReplyKeyboardMarkup(resize_keyboard=True)
markup.row(KeyboardButton('/advice'),
           KeyboardButton('/badvice'),
           KeyboardButton('/help'))
markup.row(KeyboardButton('/sub'),
           KeyboardButton('/unsub'),
           KeyboardButton('/info'))


quotes_markof = open('quotes.csv').read()
quotes = quotes_markof.splitlines()

scheduler = BackgroundScheduler()


@slepaya.message_handler(commands=['start'])
def send_welcome(message):
    cid = message.chat.id
    print(f"LOGS: [START] {cid} - {message.from_user.username}")
    slepaya.send_message(cid, f"Здравствуй, {message.from_user.first_name}")
    sleep(0.5)
    slepaya.send_message(cid, "Ничего не говори, знаю")
    sleep(0.6)
    slepaya.send_message(cid, "За советом тебя ко мне отправили",
                         reply_markup=markup)


@slepaya.message_handler(commands=['sub'])
def subscribe(message):
    cid = message.chat.id
    item = {'chat_id': str(cid)}

    dyndb = boto3.resource('dynamodb',
                           aws_access_key_id=AWS_KEY_ID,
                           aws_secret_access_key=AWS_SECRET,
                           region_name='eu-north-1')

    table = dyndb.Table('users')

    try:
        # User is subbed
        table.get_item(Key=item)['Item']
        slepaya.send_message(cid, "Моя внучка тебя уже записывала",
                             reply_markup=markup)
    except KeyError:
        # User is not subbed
        slepaya.send_message(cid, "Что-ж, ладно, внучка моя запишет тебя")
        sleep(0.4)
        slepaya.send_message(cid, "Каждый день в 9:33 " +
                                  "буду советом тебя одаривать")

        table.put_item(Item=item)
        print(f"LOGS: [SUB] {cid} - {message.from_user.username}")

        slepaya.send_message(cid, "Ну все, ступай с миром")
        slepaya.send_message(cid, "Советом тебя не обделю",
                             reply_markup=markup)


@slepaya.message_handler(commands=['unsub'])
def unsubscribe(message):
    cid = message.chat.id
    name = message.from_user.first_name
    item = {'chat_id': str(cid)}

    dyndb = boto3.resource('dynamodb',
                           aws_access_key_id=AWS_KEY_ID,
                           aws_secret_access_key=AWS_SECRET,
                           region_name='eu-north-1')
    table = dyndb.Table('users')

    try:
        # User is subbed -> unsub
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
        slepaya.send_message(cid, '/sub', reply_markup=markup)


@slepaya.message_handler(commands=['advice'])
def send_random_quote(message):
    q = random.choice(quotes)
    cid = message.chat.id
    slepaya.send_message(cid, q, reply_markup=markup)
    print(f"LOGS: [ADVICE] {cid} - {message.from_user.username}")


@slepaya.message_handler(commands=['badvice'])
def send_generated_quote(message):
    cid = message.chat.id
    # text = generate_quote('quotes.csv')
    text = NewlineText(quotes_markof).make_sentence()
    slepaya.send_message(cid, text if text else "Дух древний промолчал")
    slepaya.send_message(cid, "Так сказал дух древний, " +
                         "посетивший меня только-что", reply_markup=markup)
    print(f"LOGS: [BADVICE] {cid} - {message.from_user.username}")


@slepaya.message_handler(commands=['info'])
def send_info(message):
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


@slepaya.message_handler(commands=['help'])
def send_help(message):
    cid = message.chat.id
    txt = ("/advice - Баба Нина одарить Вас мудростью случайной\n"
           "/badvice - Святой Дух посетит бабу Нину\n"
           "/sub - Баба Нина будет одаривать Вас мудростью каждый день\n"
           "/unsub - Отказаться от ежедневных мудростей бабы Нины\n"
           "/info - Откуда мудрости /badvice духа древнего берутся\n"
           "/help - Какие услуги могу оказать тебе\n")
    slepaya.send_message(cid, "Вот что жду от тебя услышатьь")
    sleep(0.6)
    slepaya.send_message(cid, txt)


@slepaya.message_handler(func=lambda message: True)
def reply_to_others(message):
    slepaya.reply_to(message, "Ишь ты - за словом в карман не лезешь",
                     reply_markup=markup)


@scheduler.scheduled_job("interval", start_date='2020-11-7 06:33:00',
                         hours=24, id='notifications')
def send_notifications():
    dyndb = boto3.resource('dynamodb',
                           aws_access_key_id=AWS_KEY_ID,
                           aws_secret_access_key=AWS_SECRET,
                           region_name='eu-north-1')
    table = dyndb.Table('users')
    ids = table.scan()['Items']
    send_counter = 0

    cur_date = datetime.now()
    solar = Solar(cur_date.year, cur_date.month, cur_date.day)
    lunar = Converter.Solar2Lunar(solar).day
    lunar_msg = f"{random.choice(['За окном', 'На дворе', 'Сегодня'])} "
    lunar_msg += f"{lunar} {random.choice(['лунные сутки', 'лунный день'])}"

    for c_id in ids:
        q = random.choice(quotes)
        try:
            slepaya.send_message(c_id['chat_id'], lunar_msg)
            slepaya.send_message(c_id, "Вот что сегодня скажу тебе")
            slepaya.send_message(c_id['chat_id'], q)
            print(f"LOGS: [NOTIFICATIONS] send_notifications to {c_id}")
            send_counter += 1
            sleep(0.09)
        except telebot.apihelper.ApiTelegramException as e:
            print(f"LOGS: [NOTIFICATIONS_EXCEPTION] {e}")

    print(f"LOGS :[NOTIFICATIONS] Send to {send_counter} out of {len(ids)}")


scheduler.start()
slepaya.polling(none_stop=True)
