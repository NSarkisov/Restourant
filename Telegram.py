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

        bot.send_message(message.chat.id, f"Привет {message.from_user.first_name}!\nМы рады приветствовать вас")
        bot.send_message(message.chat.id,
                         'Выберите интересующий для вас раздел')

        name = message.from_user.first_name
        user_id = message.from_user.id

        with con:
            # con.execute("INSERT OR IGNORE INTO Пользователи (Имя, ID TG) values (?, ?)", [name, user_id])
            data1 = con.execute("Select * from MenuSections")
            print(data1.fetchall())

        photos = bot.get_user_profile_photos(user_id)
        if photos.total_count > 0:
            photo = photos.photos[0][-1]
            file_id = photo.file_id
            file_info = bot.get_file(file_id)
            file_path = file_info.file_path
            with open('avatar.jpg', 'wb') as file:
                file.write(bot.download_file(file_path))
            with open("avatar.jpg", 'rb') as file:
                image_data = file.read()
                with con:
                    con.execute(f"INSERT OR IGNORE INTO Пользователи (Аватарка) values (?)"
                                f" where Имя = {name} and ID TG = {user_id}", image_data)
            os.remove("avatar.jpg")






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
