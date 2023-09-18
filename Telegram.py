import json
import sqlite3
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMedia, InputMediaPhoto
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import sqlite3 as sl
from PIL import Image
from io import BytesIO

with open("Config.json") as f:
    config = json.load(f)
    Token = config.get("telegram_token")
    database = config.get("database_path")

bot = telebot.TeleBot(Token)
con = sl.connect(database, check_same_thread=False)
temp = []  # поменять на словарь, возможна ошибка если несколько пользователей воспользуются ботом


def category():
    global temp
    with con:
        data = con.execute('Select Название from "Разделы Меню"')
    markup_category = InlineKeyboardMarkup()
    temp = []
    for el in data.fetchall():
        temp.append(el[0])
        markup_category.add(InlineKeyboardButton(el[0], callback_data="1" + str(temp.index(el[0]))))
    return markup_category


def products(data):
    global temp
    with con:
        data = con.execute(f'SELECT Имя FROM Позиции '
                           f'INNER JOIN [Разделы Меню] ON Позиции.[ID раздела] = [Разделы Меню]."ID"'
                           f'WHERE [Разделы Меню]."Название" = "{data}" OR Позиции.[ID раздела] in '
                           f'(SELECT "ID раздела" FROM Позиции WHERE Имя = "{data}")')
    positions = InlineKeyboardMarkup() #Кнопки
    temp = []
    for el in data.fetchall():
        temp.append(el[0])
        positions.add(InlineKeyboardButton(el[0], callback_data="2" + str(temp.index(el[0]))))
    positions.add(InlineKeyboardButton("Меню", callback_data="3"))
    print(temp)
    return positions


def purchasing(product, id):  # Салат цезарь
    global temp
    with con:
        data = con.execute(f'SELECT Имя, Описание, Стоимость FROM Позиции '
                           f'WHERE Имя = "{product}"')  # Картинка третий элемент
        photo = con.execute(f'SELECT Картинка FROM Позиции '
                            f'WHERE Имя = "{product}"')
    image = Image.open(BytesIO(photo.fetchall()[0][0]))
    data = data.fetchall()
    caption = f"{product}\n{data[0][1]}\nСтоимость: {data[0][2]}"
    bot.send_photo(chat_id=id, photo=image, caption=caption, reply_markup=select_count(temp.index(product), count=0))


def select_count(index, count):
    button_decrease = InlineKeyboardButton("➖", callback_data="4" + "-")
    number = InlineKeyboardButton(f"{count}", callback_data="4" + f"{count}")

    button_increase = InlineKeyboardButton("➕", callback_data="4" + "+")
    order_count = InlineKeyboardMarkup()
    order_count.row(button_increase, number, button_decrease)
    order_count.add(InlineKeyboardButton("Подтвердить", callback_data="4" + "ok"))
    order_count.add(InlineKeyboardButton("Назад", callback_data="1" + f"{index}"))
    return order_count


@bot.message_handler(content_types=['text'])
def start(message):
    if message.text == '/start':

        bot.send_message(message.chat.id, f"Привет {message.from_user.first_name}!\nМы рады приветствовать вас")

        name = message.from_user.first_name
        user_id = message.from_user.id
        with con:
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
                with con:
                    con.execute(f'UPDATE OR IGNORE Пользователи SET Аватарка = ?'
                                f' where Имя = "{name}" and "ID TG" = {user_id}', [sqlite3.Binary(avatar)])

        bot.send_message(message.chat.id,
                         'Выберите категорию в Меню ⬇️', reply_markup=category())


@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    global temp
    bot.answer_callback_query(callback_query_id=call.id, )
    id = call.message.chat.id
    flag = call.data[0]
    data = call.data[1:]
    if flag == "1":
        try:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выбирайте", reply_markup=products(temp[int(data)]))
        except:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(chat_id=call.message.chat.id, text="Выбирайте", reply_markup=products(temp[int(data)]))

    if flag == "2":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='Выберите количество', reply_markup=purchasing((temp[int(data)]), id))
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
