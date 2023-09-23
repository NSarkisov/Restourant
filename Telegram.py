import json
import math
import requests
import sqlite3 as sl
import telebot
from io import BytesIO
from PIL import Image
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton

with open("Config.json") as f:
    config = json.load(f)
    Token = config.get("telegram_token")
    database = config.get("database_path")
geocoder_api = "acb5559a-b528-4544-a005-03647e92e708"
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
                       reply_markup=select_count(count=1, case=case, group_id=count, group_el=index))


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


def cart_processing(case, chat_id):
    flag = [4, ""]

    cart_buttons = InlineKeyboardMarkup()
    menu = InlineKeyboardButton("Меню", callback_data=json.dumps([2]))
    change_button = InlineKeyboardButton("Изменить", callback_data=json.dumps(flag + ["change"]))
    accept_order = InlineKeyboardButton("Подтвердить", callback_data=json.dumps(flag + ["accept"]))

    accept_changes = InlineKeyboardButton("Изменить", callback_data=json.dumps(flag + ["Изменить"]))
    back_button = InlineKeyboardButton("Назад", callback_data=json.dumps(flag + ["back"]))

    if case == "show":
        cart_buttons.row(change_button, menu, accept_order)
    if case == "change":
        if "Изменённая Корзина" not in dict_users[chat_id].keys() or dict_users[chat_id]["Изменённая Корзина"] is None:
            dict_users[chat_id]["Изменённая Корзина"] = dict_users[chat_id]["Корзина"]

        for el in dict_users[chat_id]["Изменённая Корзина"]:
            name = el[0]
            cost = el[1] * el[2]
            amount = el[2]
            index = dict_users[chat_id]["Изменённая Корзина"].index(el)
            button_decrease = InlineKeyboardButton("<", callback_data=json.dumps(flag + ["<"] + [index]))
            button_increase = InlineKeyboardButton(">", callback_data=json.dumps(flag + [">"] + [index]))
            button_delete = InlineKeyboardButton("X", callback_data=json.dumps(flag + ["x"] + [index]))
            amount_btn = InlineKeyboardButton(f"{index + 1}: {amount} шт.",
                                              callback_data=json.dumps(flag))
            cost_btn = InlineKeyboardButton(f"{cost}", callback_data=json.dumps(flag))
            cart_buttons.row(button_decrease, amount_btn, cost_btn, button_increase, button_delete)
            if el is dict_users[chat_id]["Изменённая Корзина"][-1]:
                cart_buttons.row(back_button, menu, accept_changes)
        if len(dict_users[chat_id]["Изменённая Корзина"]) == 0:
            cart_buttons.row(back_button, menu, accept_changes)

    if case == "Menu":
        cart_buttons.add(menu)
    return cart_buttons


def order_accepting(case, chat_id):
    if case == "Hide":
        return None

    elif case == "confirmation":
        flag = [4, '']
        order = InlineKeyboardMarkup()
        order_is_right = InlineKeyboardButton("Верно", callback_data=json.dumps(flag + ["right"]))
        order_not_right = InlineKeyboardButton("Не верно", callback_data=json.dumps(flag + ["back"]))
        order.row(order_not_right, order_is_right)
        return order

    elif case == "delivery":
        flag = [5, '']
        delivery = InlineKeyboardMarkup()
        by_delivery = InlineKeyboardButton("Доставка", callback_data=json.dumps(flag + ["by_delivery"]))
        by_users_self = InlineKeyboardButton("Самовывоз", callback_data=json.dumps(flag + ["self"]))
        in_restaurant = InlineKeyboardButton("В заведении", callback_data=json.dumps(flag + ["restaurant"]))
        delivery.add(by_delivery, by_users_self, in_restaurant)
        return delivery

    elif case == "Payment":
        flag = [5, '']
        payment = InlineKeyboardMarkup()
        cash = InlineKeyboardButton("Наличными", callback_data=json.dumps(flag + ["Cash"]))
        card = InlineKeyboardButton("Картой", callback_data=json.dumps(flag + ["Card"]))
        payment.row(cash, card)
        return payment

    elif case == "address":
        flag = [5, '']
        address = InlineKeyboardMarkup()
        geolocation = InlineKeyboardButton("Геолокация", callback_data=json.dumps(flag + ["Geo"]))
        manual_input = InlineKeyboardButton("Вручную", callback_data=json.dumps(flag + ["Manual"]))
        address.row(manual_input, geolocation)
        return address

    elif case == "Geolocation":
        location = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        send_geolocation = KeyboardButton(text="Отправить Геолокацию", request_location=True)
        location.add(send_geolocation)
        return location

    elif case == "Address confirmation":
        flag = [5, '']
        address_is_ok = InlineKeyboardMarkup()
        no = InlineKeyboardButton("Нет", callback_data=json.dumps(flag + ['No']))
        yes = InlineKeyboardButton("Да", callback_data=json.dumps(flag + ['Yes']))
        address_is_ok.row(no, yes)
        return address_is_ok


def order_info(user_id):
    text = "Ваш заказ:\n"
    indexing = 1
    total = 0
    for position in dict_users[user_id]["Корзина"]:
        cost = position[1] * position[2]
        text += f"{indexing}. {position[0]}, кол-во: {position[2]} сумма: {cost}.BYN\n"
        indexing += 1
        total += cost

    if "Оформление" in dict_users[user_id].keys():
        text += "\n"
        for information in dict_users[user_id]["Оформление"].items():
            text += information[0] + " : " + information[1] + "\n"
        text += "\n"
    text += f"Итого: {total} BYN"
    return text


@bot.message_handler(content_types=['location'])
def location(geodata):
    user_id = geodata.from_user.id
    chat_id = geodata.chat.id
    message_id = geodata.message_id
    if "Оформление" in dict_users[user_id].keys() and dict_users[user_id]["Оформление"] is not None:
        longitude = geodata.location.longitude
        latitude = geodata.location.latitude
        url = f"https://geocode-maps.yandex.ru/1.x/?apikey={geocoder_api}&format=json&geocode={longitude},{latitude}"
        response = requests.get(url).json()
        take_address = ['response', 'GeoObjectCollection', 'featureMember', 0, 'GeoObject', 'metaDataProperty',
                        'GeocoderMetaData', 'Address', 'formatted']
        for x in take_address:
            response = response[x]
        response = response.split(', ')  # ['Беларусь', 'Минск', 'улица Франциска Скорины', '8к1']
        question = f"Ваш адрес {','.join(response[2:])}?"
        if len(response) == 3:
            dict_users[user_id]["Оформление"].update({"Улица": response[2]})
        else:
            dict_users[user_id]["Оформление"].update({"Улица": response[2], "Дом": response[3]})
        bot.send_message(chat_id=chat_id, text=question,
                         reply_markup=order_accepting(case="Address confirmation", chat_id=user_id))


@bot.message_handler(content_types=['text'])
def start(message):

    user_id = message.from_user.id

    if message.text == '/start':

        bot.send_message(message.chat.id, f"Привет {message.from_user.first_name}!\nМы рады приветствовать вас")

        name = message.from_user.first_name

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

    if "Оформление" in dict_users[user_id].keys():
        text = ""

        if dict_users[user_id]["Оформление"]["Способ Доставки"] == "Доставка":
            if "Улица" not in dict_users[user_id]["Оформление"].keys():
                dict_users[user_id]["Оформление"].update({"Улица": message.text})
                text = "Укажите номер дома"
            elif "Дом" not in dict_users[user_id]["Оформление"].keys():
                dict_users[user_id]["Оформление"].update({"Дом": message.text})
                text = "Укажите номер квартиры"
            elif "Квартира" not in dict_users[user_id]["Оформление"].keys():
                dict_users[user_id]["Оформление"].update({"Квартира": message.text})
                text = "Укажите номер Телефона"
            elif "Телефон" not in dict_users[user_id]["Оформление"].keys():
                dict_users[user_id]["Оформление"].update({"Телефон": message.text})
                text = order_info(user_id)
                print(text)
        elif dict_users[user_id]["Оформление"]["Способ Доставки"] == "Самовывоз":
            dict_users[user_id]["Оформление"].update({"Телефон": message.text})


        elif dict_users[user_id]["Оформление"]["Способ Доставки"] == "В заведении":
            if "Номер стола" not in dict_users[user_id]["Оформление"].keys():
                dict_users[user_id]["Оформление"].update({"Номер стола": message.text})
                text = "Укажите номер телефона"
            elif "Телефон" not in dict_users[user_id]["Оформление"].keys():
                dict_users[user_id]["Оформление"].update({"Телефон": message.text})

        if text != "":
            bot.send_message(chat_id=user_id, text=text)


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
        elif operation == "+":
            count += 1
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_count(count, case, group_id, group_el))
        elif operation == "*":
            group_id += 1
            case = 0
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_count(count, case, group_id, group_el))
            select_product(dict_users[id]["groups"], id, count=group_id)
        elif operation == "add":
            reset_count = 1
            if reset_count != count:
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              reply_markup=select_count(reset_count, case, group_id, group_el))
            name = dict_users[id]["groups"][group_id][group_el][0]
            price = dict_users[id]["groups"][group_id][group_el][3]
            bot.send_message(chat_id=call.message.chat.id,
                             text=f'Успешно добавлено:\n'
                                  f'{name}: {count} шт. на сумму: {count * price}')
            if "Корзина" not in dict_users[id].keys():
                dict_users[id].update({"Корзина": [[name, price, count]]})
            else:
                dict_users[id]["Корзина"] += [[name, price, count]]
        elif operation == "cart":
            if "Корзина" not in dict_users[id].keys() or dict_users[id]["Корзина"] is None:
                bot.send_message(chat_id=call.message.chat.id,
                                 text='Ваша корзина пуста')
            else:
                text = order_info(id)
                bot.send_message(chat_id=call.message.chat.id,
                                 text=text,
                                 reply_markup=cart_processing(case="show", chat_id=id))

    if flag == 4:
        operation = data[1]
        index = 0
        if len(data) > 2:
            index = data[2]
        if operation == "change":
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=cart_processing(case="change", chat_id=id))
        if operation == "<":
            amount = dict_users[id]["Изменённая Корзина"][index][2]
            amount -= 1
            if amount >= 0:
                dict_users[id]["Изменённая Корзина"][index][2] = amount
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              reply_markup=cart_processing(case="change", chat_id=id))
        if operation == ">":
            amount = dict_users[id]["Изменённая Корзина"][index][2]
            amount += 1
            dict_users[id]["Изменённая Корзина"][index][2] = amount
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=cart_processing(case="change", chat_id=id))
        if operation == "x":
            del dict_users[id]["Изменённая Корзина"][index]
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=cart_processing(case="change", chat_id=id))
        if operation == "back":
            if "Изменённая Корзина" in dict_users[id].keys():
                del dict_users[id]["Изменённая Корзина"]
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=cart_processing(case="show", chat_id=id))

        if operation == "Изменить":
            if len(dict_users[id]["Изменённая Корзина"]) == 0:
                del dict_users[id]["Изменённая Корзина"]
                del dict_users[id]["Корзина"]
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="После изменений Ваша корзина пуста\n"
                                           "Вернитесь пожалуйста в Меню",
                                      reply_markup=cart_processing(case="Menu", chat_id=id))
            else:
                dict_users[id]["Корзина"] = dict_users[id]["Изменённая Корзина"]
                temp = []
                for el in dict_users[id]["Корзина"]:
                    if el[2] != 0:
                        temp.append(el)
                dict_users[id]["Корзина"] = temp

                if len(dict_users[id]["Корзина"]) == 0:
                    del dict_users[id]["Корзина"], dict_users[id]["Изменённая Корзина"]
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text="После изменений Ваша корзина пуста\n"
                                               "Вернитесь пожалуйста в Меню",
                                          reply_markup=cart_processing(case="Menu", chat_id=id))
                else:
                    del dict_users[id]["Изменённая Корзина"]
                    text = "Выбраные позиции меню:\n"
                    indexing = 1
                    total = 0
                    for el in dict_users[id]["Корзина"]:
                        cost = el[1] * el[2]
                        text += f"{indexing}. {el[0]}, кол-во: {el[2]} сумма: {cost}.BYN\n"
                        indexing += 1
                        total += cost
                    text += f"Итого: {total} BYN"
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text=text, reply_markup=cart_processing(case="show", chat_id=id))
        if operation == "accept":
            text = "Ваш заказ:\n"
            indexing = 1
            total = 0
            for el in dict_users[id]["Корзина"]:
                cost = el[1] * el[2]
                text += f"{indexing}. {el[0]}, кол-во: {el[2]} сумма: {cost}.BYN\n"
                indexing += 1
                total += cost
            text += f"Итого: {total} BYN"
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=text, reply_markup=order_accepting(case="confirmation", chat_id=id))
        if operation == "right":
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=order_accepting(case="Hide", chat_id=id))
            bot.send_message(chat_id=id, text="Как желаете получить заказ?",
                             reply_markup=order_accepting(case="delivery", chat_id=id))

    if flag == 5:
        operation = data[1]
        case, text = "", ""

        if "Оформление" not in dict_users[id].keys() or dict_users[id]["Оформление"] is None:
            if operation == "by_delivery":
                dict_users[id]["Оформление"] = {"Способ Доставки": "Доставка"}
            elif operation == "self":
                dict_users[id]["Оформление"] = {"Способ Доставки": "Самовывоз"}
            elif operation == "restaurant":
                dict_users[id]["Оформление"] = {"Способ Доставки": "В заведении"}
            bot.edit_message_text(chat_id=id, message_id=call.message.message_id,
                                  text="Выберите способ оплаты:",
                                  reply_markup=order_accepting(case="Payment", chat_id=id))

        elif operation == "Cash" or operation == "Card":
            if operation == "Cash":
                operation = "Наличными"
            else:
                operation = "Картой"
            dict_users[id]["Оформление"].update({"Способ Оплаты": operation})
            if dict_users[id]["Оформление"]["Способ Доставки"] == "Доставка":
                case, text = "address", "Отправьте своё местоположение\n" + "или укажите адрес в ручную"
            elif dict_users[id]["Оформление"]["Способ Доставки"] == "Самовывоз":
                case, text = "Hide", "Укажите номер телефона"
            elif dict_users[id]["Оформление"]["Способ Доставки"] == "В заведении":
                case, text = "Hide", "Укажите номер столика"
            bot.edit_message_text(chat_id=id, message_id=call.message.message_id,
                                  text=text, reply_markup=order_accepting(case=case, chat_id=id))

        elif operation == "Geo":
            bot.delete_message(chat_id=id, message_id=call.message.message_id)
            bot.send_message(chat_id=id, text="Отправьте Геолокацию",
                             reply_markup=order_accepting(case="Geolocation", chat_id=id))

        elif operation == "Manual":
            bot.edit_message_text(chat_id=id, message_id=call.message.message_id,
                                  text="Укажите улицу",
                                  reply_markup=order_accepting(case="Hide", chat_id=id))

        elif operation == "Yes":
            if "Дом" not in dict_users[id]["Оформление"].keys():
                text = "Укажите номер дома"
            else:
                text = "Укажите номер квартиры"
            bot.edit_message_text(chat_id=id, message_id=call.message.message_id, text=text)


print("Telegram started successfully")
bot.infinity_polling()
