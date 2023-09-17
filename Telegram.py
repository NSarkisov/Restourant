import json
import os
import gspread
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
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
        user_id = message.from_user.id
        name = message.from_user.first_name

        bot.send_message(message.chat.id, f"Привет {message.from_user.first_name}!\nМы рады приветствовать вас")
        bot.send_message(message.chat.id,
                         'Выберите интересующий для вас раздел')
        con.execute("INSERT OR IGNORE INTO Пользователи (Имя, Аватарка, ID TG) values (?, ?, ?)", )
        # user = message.from_user
        # photos = bot.get_user_profile_photos(user.id)
        # if photos.total_count > 0:
        #     photo = photos.photos[0][-1]
        #     file_id = photo.file_id
        #     file_info = bot.get_file(file_id)
        #     file_path = file_info.file_path
        #     with open('avatar.jpg', 'wb') as file:
        #         file.write(bot.download_file(file_path))
        #     with open("avatar.jpg", 'rb') as photo:
        #         bot.send_photo(message.chat.id, photo)
        #     os.remove("avatar.jpg")


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
