import gspread
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3 as sl

bot = telebot.TeleBot('Token from json config')
con = sl.connect('Path for Database file')

markup_category = InlineKeyboardMarkup()
markup_category.add(InlineKeyboardButton('Меню', callback_data="1" + 'Меню'))
markup_category.add(InlineKeyboardButton('Профиль', callback_data="2" + 'Профиль'))
markup_category.add(InlineKeyboardButton('Мои заказы', callback_data="3" + 'Мои заказы'))
markup_category.add(InlineKeyboardButton('Наши контакты', callback_data="4" + 'Наши контакты'))
markup_category.add(InlineKeyboardButton('Пригласить друга', callback_data="5" + 'Наши контакты'))


@bot.message_handler(content_types=['text'])
def start(message):
    print(message.from_user.id)

    if message.text == '/start':
        bot.send_message(message.chat.id,
                         'Выберите интересующий для вас раздел',
                         reply_markup=markup_category)


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
