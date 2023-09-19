import json
import math
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

dict_users = {}
# temp = []  # поменять на словарь, возможна ошибка если несколько пользователей воспользуются ботом
# groups = []


def category(user_id):
    temp = []
    with con:
        data = con.execute('SELECT Название FROM "Разделы Меню"')
    markup_category = InlineKeyboardMarkup()

    flag = [1]
    for el in data.fetchall():
        temp.append(el[0])
        index = temp.index(el[0])
        markup_category.add(InlineKeyboardButton(el[0], callback_data=json.dumps(flag + [index])))
    dict_users[user_id] = {"Выбранные Категории": temp}
    return markup_category


def products(data, chat_id):
    temp, groups = [], []
    with con:
        data = con.execute(f'Select Имя, Картинка, Описание, Стоимость FROM Позиции '
                           f'INNER JOIN [Разделы Меню] ON Позиции.[ID раздела] = [Разделы Меню]."ID"'
                           f'WHERE [Разделы Меню]."Название" = "{data}";')

    for el in data.fetchall():
        name = el[0]
        image = Image.open(BytesIO(el[1]))
        description = el[2]
        cost = el[3]
        temp.append([name, image, description, cost])
    # temp = [[],[],[],....,[]]
    step = 0
    for i in range(math.ceil(len(temp) / 2)):
        groups.append(temp[step:step + 2])
        step += 2
    # groups = [[[],[]], [[],[]], ...., [[],[]]]

    dict_users[chat_id].update({"groups": groups})

    select_product(dict_users[chat_id]["groups"], chat_id, count=0)


def select_product(data, chat_id, count):
    for el in data[count]:  # data[count] = [[], []]
        case = 0
        name = el[0]
        image = el[1]
        description = el[2]
        cost = el[3]
        caption = f"{name}\n{description}\nСтоимость: {cost}"
        if el == data[count][-1]:
            case = "Next"
            if count == (len(data) - 1):
                case = "Menu"
        bot.send_photo(chat_id=chat_id, photo=image, caption=caption,
                       reply_markup=select_count(count=0, case=case, group_id=count))


def select_count(count, case, group_id):
    data = [4, count, case, group_id]
    order_count = InlineKeyboardMarkup()
    button_decrease = InlineKeyboardButton("➖", callback_data=json.dumps(data + ["-"]))
    number = InlineKeyboardButton(f"{count}", callback_data=json.dumps(data))
    button_increase = InlineKeyboardButton("➕", callback_data=json.dumps(data + ["+"]))
    order_count.row(button_decrease, number, button_increase)
    order_count.add(InlineKeyboardButton("Добавить", callback_data=json.dumps(data + ["add"])))
    if case == "Next":
        order_count.add(InlineKeyboardButton("Следующие", callback_data=json.dumps(data + ["*"])))
    if case == "Menu":
        flag = [2]
        order_count.add(InlineKeyboardButton("Меню", callback_data=json.dumps(flag)))
    return order_count


@bot.message_handler(content_types=['text'])
def start(message):
    if message.text == '/start':

        bot.send_message(message.chat.id, f"Привет {message.from_user.first_name}!\nМы рады приветствовать вас")

        name = message.from_user.first_name
        user_id = message.from_user.id
        print(user_id)
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
                         'Выберите категорию в Меню ⬇️', reply_markup=category(user_id))


@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, )
    id = call.message.chat.id
    call.data = json.loads(call.data)
    flag = call.data[0]
    data = []

    if len(call.data) > 1:
        data = call.data[1:]

    if flag == 1:
        print(dict_users)
        index = data[0]
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="Выбирайте",
                              reply_markup=products(dict_users[id].get("Выбранные Категории")[index], id))

    if flag == 2:
        try:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='Выберите категорию в Меню ⬇️',
                                  reply_markup=category(id))
        except:
            bot.send_message(chat_id=call.message.chat.id,
                             text='Выберите категорию в Меню ⬇️',
                             reply_markup=category(id))

    if flag == 4:
        count, case, group_id, operation = data[0], data[1], data[2], data[3]
        if operation == "-":
            if count > 0:
                count -= 1
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              reply_markup=select_count(count, case, group_id))
        if operation == "+":
            count += 1
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_count(count, case, group_id))
        if operation == "*":
            group_id += 1
            case = 0
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_count(count, case, group_id))
            select_product(dict_users[id]["groups"], id, count=group_id)

    # if flag == "5":
    #     bot.edit_chat_invite_link(call.message.chat.id, )  # Здесь мы должны продумать как сделать приглашение

    # if flag == "2":
    #     operation = data[0]
    #     count = int(data[1:])
    #     if operation == "-":
    #         count -= 1
    #         bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
    #                                       reply_markup=select_product(groups, id, count=count))
    #     if operation == "+":
    #         count += 1
    #         bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
    #                                       reply_markup=select_product(groups, id, count=count))


print("Telegram started successfully")
bot.infinity_polling()
