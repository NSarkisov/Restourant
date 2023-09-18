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
cycle = {}
temp = []  # поменять на словарь, возможна ошибка если несколько пользователей воспользуются ботом
groups = []


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


def products(data, chat_id):
    global temp, groups
    temp = []
    groups = []

    with con:
        data = con.execute(f'Select Имя, Картинка, Описание, Стоимость FROM Позиции '
                           f'INNER JOIN [Разделы Меню] ON Позиции.[ID раздела] = [Разделы Меню]."ID"'
                           f'WHERE [Разделы Меню]."Название" = "{data}";')

    for el in data.fetchall():
        name = el[0]
        image = Image.open(BytesIO(el[1]))
        description = el[2]
        cost = el[3]
        # caption = f"{name}\n{description}\nСтоимость: {cost}"
        temp.append([name, image, description, cost])
    step = 0
    for i in range(math.ceil(len(temp) / 2)):
        groups.append(temp[step:step + 2])
        step += 2
    a = select_product(groups, chat_id, count=0)
    return a


def select_product(data, chat_id, count):

    # data это трехмерный список групп = [[[][]], [[][]],....,[[][]]]
    # где внешний список это все группы,
    # где подсписок всех групп это группа с двумя списками,
    # где подсписки группы это списки входящие в группу,
    # Для того что бы отправлять по две карточки продуктов в БОТ
    # count служит выбором группы

    # Задача на завтра заменить слайдер Инлайн кнопок на Реплай и посмотреть результат
    change_group = InlineKeyboardMarkup()
    button_forward = InlineKeyboardButton("⋙", callback_data="2" + "-" + f"{count}")
    button_backward = InlineKeyboardButton("⋘", callback_data="2" + "-" + f"{count}")
    button_home = InlineKeyboardButton("Меню", callback_data="3")
    if count == 0:
        change_group.add(button_forward)
    if count != 0 and count < (len(data) - 1):
        change_group.row(button_backward, button_forward)
    if count == len(data):
        change_group.add(button_home)

    for el in data[count]:
        print(el)
        name = el[0]
        image = el[1]
        description = el[2]
        cost = el[3]
        caption = f"{name}\n{description}\nСтоимость: {cost}"
        bot.send_photo(chat_id=chat_id, photo=image, caption=caption, reply_markup=select_count(count=0))
    bot.send_message(chat_id, text="Показать еще", reply_markup= change_group)


def select_count(count):
    order_count = InlineKeyboardMarkup()
    button_decrease = InlineKeyboardButton("➖", callback_data="4" + "-" + f"{count}")
    number = InlineKeyboardButton(f"{count}", callback_data="4" + f"{count}")
    button_increase = InlineKeyboardButton("➕", callback_data="4" + "+" + f"{count}")
    order_count.row(button_decrease, number, button_increase)
    order_count.add(InlineKeyboardButton("Добавить", callback_data="4" + "add"))

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
    global temp, groups
    bot.answer_callback_query(callback_query_id=call.id, )
    id = call.message.chat.id
    flag = call.data[0]
    data = call.data[1:]
    if flag == "1":
        try:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выбирайте", reply_markup=products(temp[int(data)], id))
        except:
            bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(chat_id=call.message.chat.id, text="Выбирайте", reply_markup=products(temp[int(data)], id))

    if flag == "3":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text='Выберите категорию в Меню ⬇️',
                              reply_markup=category())

    if flag == "2":
        operation = data[0]
        count = int(data[1:])
        if operation == "-":
            count -= 1
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_product(groups, id, count=count))

        if operation == "+":
            count += 1
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_product(groups, id, count=count))

    if flag == "4":

        operation = data[0]

        count = int(data[1:])

        if operation == "-":
            count -= 1
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_count(count))

        if operation == "+":
            print("ok")
            count += 1
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_count(count))

    # if flag == "5":
    #     bot.edit_chat_invite_link(call.message.chat.id, )  # Здесь мы должны продумать как сделать приглашение


print("Telegram started successfully")
bot.infinity_polling()
