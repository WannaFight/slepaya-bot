from apscheduler.schedulers.background import BackgroundScheduler
import boto3
from os import getenv
import random
import telebot
from time import sleep


AWS_KEY_ID = getenv('AWS_KEY_ID', None)
AWS_SECRET = getenv('AWS_SECRET', None)
TOKEN = getenv('BOT_TOKEN', None)

slepaya = telebot.TeleBot(TOKEN)
quotes = open('quotes.csv').read().splitlines()

scheduler = BackgroundScheduler()


@slepaya.message_handler(commands=['start'])
def send_welcome(message):
    cid = message.chat.id
    print(f"LOGS: [START] {cid} - {message.from_user.username}")
    slepaya.send_message(cid, f"Здравствуй, {message.from_user.first_name}")
    sleep(0.5)
    slepaya.send_message(cid, "Ничего не говори, знаю")
    sleep(0.6)
    slepaya.send_message(cid, "За советом тебя ко мне отправили")


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
        table.get_item(Key=item)['Item']
        slepaya.send_message(cid, "Моя внучка тебя уже записывала")
    except KeyError:
        slepaya.send_message(cid, "Что-ж, ладно, внучка моя запишет тебя")
        sleep(0.4)
        slepaya.send_message(cid, "Каждый день в 9:33 " +
                                  "буду советом тебя одаривать")

        table.put_item(Item=item)

        slepaya.send_message(cid, "Ну все, ступай с миром")
        slepaya.send_message(cid, "Советом тебя не обделю")


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
        table.get_item(Key=item)['Item']

        slepaya.send_message(cid, f"Ох, ох, {name}, что-ж делать-то...")
        sleep(0.8)
        slepaya.send_message(cid, "Ладно, сейчас попрошу внучку " +
                             "тебя убрать из списка")
        table.delete_item(Key=item)
        sleep(0.9)
        slepaya.send_message(cid, "Внучка выписала тебя из тетрадки")
        slepaya.send_message(cid, "Помни одно - ты всегда ко мне" +
                             " можешь обратиться")
    except KeyError:
        slepaya.send_message(cid, "А тебя еще не записывали")
        slepaya.send_message(cid, "Могу попросить мою внучку тебя записать")
        slepaya.send_message(cid, '/sub')


@slepaya.message_handler(commands=['advice'])
def send_random_quote(message):
    q = random.choice(quotes)
    slepaya.send_message(message.chat.id, q)


@slepaya.message_handler(func=lambda message: True)
def reply_to_others(message):
    slepaya.reply_to(message, "Ишь ты - за словом в карман не лезешь")


@scheduler.scheduled_job("interval", start_date='2020-11-7 06:33:00',
                         minutes=1, id='notifications')
def send_notifications():
    dyndb = boto3.resource('dynamodb',
                           aws_access_key_id=AWS_KEY_ID,
                           aws_secret_access_key=AWS_SECRET,
                           region_name='eu-north-1')
    table = dyndb.Table('users')
    ids = table.scan()['Items']
    for c_id in ids:
        print(f"LOGS: [NOTIFICATIONS] send_notifications to {c_id}")
        q = random.choice(quotes)
        slepaya.send_message(c_id['chat_id'], q)
        sleep(0.04)


scheduler.start()
slepaya.polling(none_stop=True)
