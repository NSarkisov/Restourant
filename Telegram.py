import json
import os
import sqlite3
import threading
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


def category():
    con = sl.connect(database)
    data = con.execute('Select Название from "Разделы Меню"')
    markup_category = InlineKeyboardMarkup()
    for el in data.fetchall():
        markup_category.add(InlineKeyboardButton(el[0], callback_data="1" + el[0]))
    return markup_category


def products(data):
    con = sl.connect(database)
    data = con.execute(f'SELECT Имя FROM Позиции '
                       f'INNER JOIN [Разделы Меню] ON Позиции.[ID раздела] = [Разделы Меню]."ID"'
                       f'WHERE [Разделы Меню]."Название" = "{data}"')
    positions = InlineKeyboardMarkup()
    for el in data.fetchall():
        positions.add(InlineKeyboardButton(el[0], callback_data="2" + el[0]))
    positions.add(InlineKeyboardButton("Меню", callback_data="3"))
    return positions


@bot.message_handler(content_types=['text'])
def start(message):
    con = sl.connect(database)
    if message.text == '/start':

        bot.send_message(message.chat.id, f"Привет {message.from_user.first_name}!\nМы рады приветствовать вас")

        name = message.from_user.first_name
        user_id = message.from_user.id

        con.execute('INSERT OR IGNORE INTO Пользователи (Имя, "ID TG") values (?, ?)', [name, user_id])

        photos = bot.get_user_profile_photos(user_id)
        if photos.total_count > 0:
            photo = photos.photos[0][-1]
            file_id = photo.file_id
            file_info = bot.get_file(file_id)
            file_path = file_info.file_path
            avatar_url = f"https://api.telegram.org/file/bot{Token}/{file_path}"
            response = requests.get(avatar_url)
            if response.status_code == 200:
                avatar = response.content
                con.execute(f'UPDATE OR IGNORE Пользователи SET Аватарка = ?'
                            f' where Имя = "{name}" and "ID TG" = {user_id}', [sqlite3.Binary(avatar)])
        bot.send_message(message.chat.id,
                         'Выберите категорию в Меню ⬇️', reply_markup=category())


@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, )
    id = call.message.chat.id
    flag = call.data[0]
    data = call.data[1:]
    if flag == "1":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="Выбирайте", reply_markup=products(data))
    # if flag == "2":
    #     bot.send_document(call.message.chat.id, open(r'Наш.html', 'rb'))
    if flag == "3":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='Выберите категорию в Меню ⬇️',
                              reply_markup=category())
    # if flag == "4":
    #     bot.send_document(call.message.chat.id, open(r'Наш.html', 'rb'))
    # if flag == "5":
    #     bot.edit_chat_invite_link(call.message.chat.id, )  # Здесь мы должны продумать как сделать приглашение


print("Telegram started successfully")
bot.infinity_polling()
