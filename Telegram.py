import json
import math
import requests
import sqlite3 as sl
import telebot
from io import BytesIO
from PIL import Image
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

with open("Config.json") as f:
    config = json.load(f)
    Token = config.get("telegram_token")
    database = config.get("database_path")

bot = telebot.TeleBot(Token)
con = sl.connect(database, check_same_thread=False)
dict_users = {}


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
    if user_id not in dict_users.keys() or dict_users[user_id] is None:
        dict_users[user_id] = {"Выбранные Категории": temp}
    else:
        dict_users[user_id]["Выбранные Категории"] = temp

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
        index = data[count].index(el)
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
                       reply_markup=select_count(count=0, case=case, group_id=count, group_el=index))


def select_count(count, case, group_id, group_el):
    data = [3, count, case, group_id, group_el]

    order_count = InlineKeyboardMarkup()
    button_decrease = InlineKeyboardButton("➖", callback_data=json.dumps(data + ["-"]))
    number = InlineKeyboardButton(f"{count}", callback_data=json.dumps(data))
    button_increase = InlineKeyboardButton("➕", callback_data=json.dumps(data + ["+"]))
    cart_button = InlineKeyboardButton("Корзина", callback_data=json.dumps(data + ["cart"]))
    add_button = InlineKeyboardButton("Добавить", callback_data=json.dumps(data + ["add"]))
    next_button = InlineKeyboardButton("Следующие", callback_data=json.dumps(data + ["*"]))

    order_count.row(button_decrease, number, button_increase)
    if case == 0:
        order_count.add(add_button)
    if case == "Next":
        order_count.row(cart_button, add_button, next_button)
    if case == "Menu":
        flag = [2]
        menu = InlineKeyboardButton("Меню", callback_data=json.dumps(flag))
        order_count.row(cart_button, add_button, menu)
    return order_count


def cart_processing(case, chat_id, group):
    flag = [4, ""]

    cart_buttons = InlineKeyboardMarkup()
    change_button = InlineKeyboardButton("Изменить", callback_data=json.dumps(flag + ["change"]))
    accept_order = InlineKeyboardButton("Подтвердить", callback_data=json.dumps(flag + ["accept"]))
    menu = InlineKeyboardButton("Меню", callback_data=json.dumps([2]))

    if case == "show":
        cart_buttons.row(change_button, menu, accept_order)

    if case[0] == "change":
        cart = dict_users[chat_id]["Новая Корзина"][group]
        count = cart[2]

        button_decrease = InlineKeyboardButton("➖", callback_data=json.dumps(flag + ["-"] + [group] + [case[1]]))
        number = InlineKeyboardButton(f"{count}", callback_data=json.dumps(flag))
        button_increase = InlineKeyboardButton("➕", callback_data=json.dumps(flag + ["+"] + [group] + [case[1]]))

        cart_buttons.row(button_decrease, number, button_increase)

        if case[1]:
            flag = [5, ""]
            accept_changes = InlineKeyboardButton("Принять", callback_data=json.dumps(flag + ["Принять"] + [group]))
            cancel_changes = InlineKeyboardButton("Отмена", callback_data=json.dumps(flag + ["Отмена"] + [group]))
            cart_buttons.row(cancel_changes, accept_changes)
        # print("Добавь код")

    return cart_buttons


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
                                f' where Имя = "{name}" and "ID TG" = {user_id}', [sl.Binary(avatar)])

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

    if flag == 3:
        count, case, group_id, group_el, operation = data[0], data[1], data[2], data[3], data[4]
        if operation == "-":
            if count > 0:
                count -= 1
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              reply_markup=select_count(count, case, group_id, group_el))
        if operation == "+":
            count += 1
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_count(count, case, group_id, group_el))
        if operation == "*":
            group_id += 1
            case = 0
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_count(count, case, group_id, group_el))
            select_product(dict_users[id]["groups"], id, count=group_id)
        if operation == "add":
            reset_count = 0
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_count(reset_count, case, group_id, group_el))
            name = dict_users[id]["groups"][group_id][group_el][0]
            price = dict_users[id]["groups"][group_id][group_el][3]
            if "Корзина" not in dict_users[id].keys():
                dict_users[id].update({"Корзина": [[name, price, count]]})
            else:
                dict_users[id]["Корзина"] += [[name, price, count]]
        if operation == "cart":
            if "Корзина" not in dict_users[id].keys() or dict_users[id]["Корзина"] is None:
                bot.send_message(chat_id=call.message.chat.id,
                                 text='Ваша корзина пуста')
            else:
                text = "Выбраные позиции меню:\n"
                indexing = 1
                total = 0
                for el in dict_users[id]["Корзина"]:
                    cost = int(el[1][0:-5]) * int(el[2])
                    text += f"{indexing}. {el[0]}, кол-во: {el[2]} сумма: {cost}.BYN\n"
                    indexing += 1
                    total += cost
                text += f"Итого: {total}.BYN"
                bot.send_message(chat_id=call.message.chat.id,
                                 text=text, reply_markup=cart_processing(case="show", chat_id=id, group=None))

    if flag == 4:
        operation = data[1]
        cart = dict_users[id]["Корзина"]
        dict_users[id]["Новая Корзина"] = cart
        new_cart = dict_users[id]["Новая Корзина"]
        if operation == "change":
            for el in new_cart:
                name = el[0]
                index = cart.index(el)
                cost = int(el[1][0:-5])
                count = el[2]
                if el is not cart[-1]:
                    bot.send_message(chat_id=call.message.chat.id,
                                     text=name,
                                     reply_markup=cart_processing(case=["change", False], chat_id=id, group=index))
                else:
                    bot.send_message(chat_id=call.message.chat.id,
                                     text=name,
                                     reply_markup=cart_processing(case=["change", True], chat_id=id, group=index))
        if operation == "-":
            index = data[2]
            price = new_cart[index][2]
            last_btns = data[3]
            if price > 0:
                price -= 1
                new_cart[index][2] = price
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              reply_markup=cart_processing(case=["change", last_btns],
                                                                           chat_id=id, group=index))

        if operation == "+":
            index = data[2]
            price = new_cart[index][2]
            last_btns = data[3]
            price += 1
            new_cart[index][2] = price
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=cart_processing(case=["change", last_btns],
                                                                       chat_id=id, group=index))

        if operation == "accept":
            print("Добавь код")

    if flag == 5:
        operation = data[1]
        index = data[2]
        if operation == "Принять":
            dict_users[id]["Корзина"] = dict_users[id]["Новая Корзина"]

            text = "Выбраные позиции меню:\n"
            indexing = 1
            total = 0
            for el in dict_users[id]["Корзина"]:
                cost = int(el[1][0:-5]) * int(el[2])
                text += f"{indexing}. {el[0]}, кол-во: {el[2]} сумма: {cost}.BYN\n"
                indexing += 1
                total += cost
            text += f"Итого: {total}.BYN"
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=cart_processing(case=["change", False], chat_id=id, group=index))
            del dict_users[id]["Новая Корзина"]
            bot.send_message(chat_id=call.message.chat.id,
                             text=text, reply_markup=cart_processing(case="show", chat_id=id, group=None))

        if operation == "Отмена":

            text = "Выбраные позиции меню:\n"
            indexing = 1
            total = 0
            for el in dict_users[id]["Корзина"]:
                cost = int(el[1][0:-5]) * int(el[2])
                text += f"{indexing}. {el[0]}, кол-во: {el[2]} сумма: {cost}.BYN\n"
                indexing += 1
                total += cost
            text += f"Итого: {total}.BYN"
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=cart_processing(case=["change", False], chat_id=id, group=index))
            del dict_users[id]["Новая Корзина"]
            bot.send_message(chat_id=call.message.chat.id,
                             text=text, reply_markup=cart_processing(case="show", chat_id=id, group=None))


print("Telegram started successfully")
bot.infinity_polling()
