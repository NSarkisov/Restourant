import json
import gspread
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3 as sl

with open("Config.json") as f:
    config = json.load(f)
    Token = config.get("telegram_token")
    database = config.get("database_path")

bot = telebot.TeleBot(Token)
con = sl.connect(database)


# markup_category = InlineKeyboardMarkup()
# markup_category.add(InlineKeyboardButton('Меню', callback_data="1" + 'Меню'))
# markup_category.add(InlineKeyboardButton('Профиль', callback_data="2" + 'Профиль'))
# markup_category.add(InlineKeyboardButton('Мои заказы', callback_data="3" + 'Мои заказы'))
# markup_category.add(InlineKeyboardButton('Наши контакты', callback_data="4" + 'Наши контакты'))
# markup_category.add(InlineKeyboardButton('Пригласить друга', callback_data="5" + 'Наши контакты'))


@bot.message_handler(content_types=['text'])
def start(message):


    if message.text == '/start':
        #Запись данных о пользователе

        bot.send_message(message.chat.id,
                         'Выберите интересующий для вас раздел')


@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, )
    id = call.message.chat.id
    flag = call.data[0]
    data = call.data[1:]
    if flag == "1":
        bot.send_document(call.message.chat.id, open(r'Наш.html', 'rb'))
    if flag == "2":
        bot.send_document(call.message.chat.id, open(r'Наш.html', 'rb'))
    if flag == "3":
        bot.send_document(call.message.chat.id, open(r'Наш.html', 'rb'))
    if flag == "4":
        bot.send_document(call.message.chat.id, open(r'Наш.html', 'rb'))
    if flag == "5":
        bot.edit_chat_invite_link(call.message.chat.id, )  # Здесь мы должны продумать как сделать приглашение
    

print("Telegram started successfully")
bot.infinity_polling()
