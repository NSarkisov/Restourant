import json
import math
import requests
import sqlite3 as sl
import telebot
from io import BytesIO
from PIL import Image
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton

with open("Config.json") as f:
    config = json.load(f)
    Token = config.get("telegram_token")
    database = config.get("database_path")
    geocoder_api = config.get("geocoder_api")
bot = telebot.TeleBot(Token)
con = sl.connect(database, check_same_thread=False)
dict_users = {}
with con:
    menu = con.execute("SELECT Название FROM 'Разделы Меню'")
    menu_categories = []
    for categories in menu.fetchall():
        menu_categories.append(categories[0])
    dict_users["Категории Меню"] = menu_categories
    del menu_categories, menu, categories, f


def category():
    updated_menu, flag = [], [1]

    with con:
        data = con.execute('SELECT Название FROM "Разделы Меню"')
        for categories in data.fetchall():
            updated_menu.append(categories[0])
        if dict_users["Категории Меню"] is not updated_menu:
            dict_users["Категории Меню"] = updated_menu
        del updated_menu, categories

    markup_category = InlineKeyboardMarkup()
    for categories in dict_users["Категории Меню"]:
        index = dict_users["Категории Меню"].index(categories)
        markup_category.add(InlineKeyboardButton(categories, callback_data=json.dumps(flag + [index])))
    del categories
    return markup_category


def products(data, user_id):
    temp, groups = [], []
    with con:
        data = con.execute(f'SELECT Имя, Картинка, Описание, Стоимость FROM Позиции '
                           f'INNER JOIN [Разделы Меню] ON Позиции.[ID раздела] = [Разделы Меню]."ID"'
                           f'WHERE [Разделы Меню]."Название" = "{data}"')

    for product in data.fetchall():
        name = product[0]
        image = Image.open(BytesIO(product[1]))
        description = product[2]
        cost = product[3]
        temp.append([name, image, description, cost])
    # temp = [[],[],[],....,[]]
    step = 0
    for i in range(math.ceil(len(temp) / 2)):
        groups.append(temp[step:step + 2])
        step += 2
    # groups = [[[],[]], [[],[]], ...., [[],[]]] упакованный в zip итераторы
    if user_id not in dict_users.keys():
        dict_users.update({user_id: {"groups": groups}})
    else:
        dict_users[user_id]["groups"] = groups
    select_product(user_id, count=0)


def select_product(user_id, count):
    data = dict_users[user_id]["groups"][count]  # data = [[], []]
    for element in data:
        index = data.index(element)
        case = 0
        name = element[0]
        image = element[1]
        description = element[2]
        cost = element[3]
        caption = f"{name}\n{description}\nСтоимость: {cost}"
        if element == data[-1]:
            case = "Next"
            if count == (len(dict_users[user_id]["groups"]) - 1):
                case = "Menu"
                # dict_users[user_id]["groups"] = None
        bot.send_photo(chat_id=user_id, photo=image, caption=caption,
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
    menu = InlineKeyboardButton("Меню", callback_data=json.dumps([2]))

    if case == "show":
        data = [4, "change", "accept"]
        show_buttons = InlineKeyboardMarkup()
        change_button = InlineKeyboardButton("Изменить", callback_data=json.dumps([data[0], data[1]]))
        menu = InlineKeyboardButton("Меню", callback_data=json.dumps([2]))
        accept_order = InlineKeyboardButton("Подтвердить", callback_data=json.dumps([data[0], data[2]]))
        show_buttons.row(change_button, menu, accept_order)
        return show_buttons

    if case == "change":
        data = [4, "Изменить", "back", "<", ">", "x"]
        change_buttons = InlineKeyboardMarkup()
        button_decrease = InlineKeyboardButton("<")
        button_increase = InlineKeyboardButton(">")
        button_delete = InlineKeyboardButton("X")

        accept_changes = InlineKeyboardButton("Изменить", callback_data=json.dumps([data[0], data[1]]))
        back_button = InlineKeyboardButton("Назад", callback_data=json.dumps([data[0], data[2]]))

        if "Изменённая Корзина" not in dict_users[chat_id].keys() or dict_users[chat_id]["Изменённая Корзина"] is None:
            dict_users[chat_id]["Изменённая Корзина"] = dict_users[chat_id]["Корзина"]

        for el in dict_users[chat_id]["Изменённая Корзина"]:
            cost = el[1] * el[2]
            amount = el[2]
            index = dict_users[chat_id]["Изменённая Корзина"].index(el)
            button_decrease.callback_data = json.dumps([data[0], data[3], [index]])
            button_increase.callback_data = json.dumps([data[0], data[4], [index]])
            button_delete.callback_data = json.dumps([data[0], data[5], [index]])
            amount_btn = InlineKeyboardButton(f"{index + 1}: {amount} шт.", callback_data=json.dumps([4]))
            cost_btn = InlineKeyboardButton(f"{cost}", callback_data=json.dumps([4]))

            change_buttons.row(button_decrease, amount_btn, cost_btn, button_increase, button_delete)

            if el is dict_users[chat_id]["Изменённая Корзина"][-1]:
                change_buttons.row(back_button, menu, accept_changes)

        if len(dict_users[chat_id]["Изменённая Корзина"]) == 0:
            change_buttons.row(back_button, menu, accept_changes)

        return change_buttons

    if case == "Menu":
        back_to_menu = InlineKeyboardMarkup()
        back_to_menu.add(menu)
        return back_to_menu


def order_accepting(case, chat_id):
    if case == "Hide":
        return None

    elif case == "confirmation":
        flag = 4
        order = InlineKeyboardMarkup()
        order_is_right = InlineKeyboardButton("Верно", callback_data=json.dumps([flag, "right"]))
        order_not_right = InlineKeyboardButton("Не верно", callback_data=json.dumps([flag, "back"]))
        order.row(order_not_right, order_is_right)
        return order

    elif case == "delivery":
        flag = 5
        delivery = InlineKeyboardMarkup()
        by_delivery = InlineKeyboardButton("Доставка", callback_data=json.dumps([flag, "by_delivery"]))
        by_users_self = InlineKeyboardButton("Самовывоз", callback_data=json.dumps([flag, "self"]))
        in_restaurant = InlineKeyboardButton("В заведении", callback_data=json.dumps([flag, "restaurant"]))
        delivery.add(by_delivery, by_users_self, in_restaurant)
        return delivery

    elif case == "Payment":
        flag = 5
        payment = InlineKeyboardMarkup()
        cash = InlineKeyboardButton("Наличными", callback_data=json.dumps([flag, "Cash"]))
        card = InlineKeyboardButton("Картой", callback_data=json.dumps([flag, "Card"]))
        payment.row(cash, card)
        return payment

    elif case == "address":
        flag = 5
        address = InlineKeyboardMarkup()
        geolocation = InlineKeyboardButton("Геолокация", callback_data=json.dumps([flag, "Geo"]))
        manual_input = InlineKeyboardButton("Вручную", callback_data=json.dumps([flag, "Manual"]))
        address.row(manual_input, geolocation)
        return address

    elif case == "Geolocation":
        location = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        send_geolocation = KeyboardButton(text="Отправить Геолокацию", request_location=True)
        location.add(send_geolocation)
        return location

    elif case == "Address confirmation":
        flag = 5
        address_is_ok = InlineKeyboardMarkup()
        no = InlineKeyboardButton("Нет", callback_data=json.dumps([flag, 'No']))
        yes = InlineKeyboardButton("Да", callback_data=json.dumps([flag, 'Yes']))
        address_is_ok.row(no, yes)
        return address_is_ok


def order_info(user_id):
    number, order = None, None
    if "Оформление" in dict_users[user_id].keys():
        with con:
            number = con.execute(f'SELECT Заказы.ID FROM Заказы INNER JOIN Пользователи '
                                 f'ON Заказы.[ID Пользователя] = Пользователи.ID '
                                 f'WHERE Пользователи.[ID TG] = {user_id} ORDER BY Заказы.ID DESC LIMIT 1;')
        number = number.fetchall()[0][0]

        order = f"\n"

        for information in dict_users[user_id]["Оформление"].items():
            order += information[0] + " : " + information[1] + "\n"
        order += "\n"
        if dict_users[user_id]["Оформление"]["Способ Доставки"] == "Доставка":
            order += "Доставка в течении: 30 ± 5 минут\n"

    if number is not None:
        text = f"Ваш заказ: №{number}\n\n"
    else:
        text = "Ваш заказ:\n\n"

    indexing = 1
    total = 0
    for position in dict_users[user_id]["Корзина"]:
        cost = position[1] * position[2]
        text += f"{indexing}. {position[0]}, кол-во: {position[2]} сумма: {cost}.BYN\n"
        indexing += 1
        total += cost
    if order is not None:
        text += order
    text += f"Итого: {total} BYN"
    return text


def order_to_base(user_id):
    telephone = dict_users[user_id]["Оформление"]["Телефон"]
    address = None
    if dict_users[user_id]["Оформление"]["Способ Доставки"] == "Доставка":
        street = dict_users[user_id]["Оформление"]["Улица"]
        house = dict_users[user_id]["Оформление"]["Дом"]
        apartment = dict_users[user_id]["Оформление"]["Квартира"]
        address = street + ", " + house + ", " + apartment
    cost = sum(x[1] * x[2] for x in dict_users[user_id]["Корзина"])
    payment = dict_users[user_id]["Оформление"]["Способ Оплаты"]
    delivery = dict_users[user_id]["Оформление"]["Способ Доставки"]
    current_date_time = datetime.now().replace(microsecond=0)
    with con:
        con.execute(f'UPDATE OR IGNORE Пользователи set Телефон = (?)'
                    f'WHERE [ID TG] = {user_id}', [telephone])
        con.execute(f'INSERT OR IGNORE INTO Заказы ("ID Пользователя", Время, Адресс, Стоимость, Оплата, Доставка) '
                    f'values ((SELECT ID FROM Пользователи WHERE [ID TG] = {user_id}),'
                    f'("{current_date_time}"),?,?,?,?)',
                    [address, cost, payment, delivery])
        for product in dict_users[user_id]["Корзина"]:
            name = product[0]
            con.execute(f'INSERT OR IGNORE INTO [Состав заказа] (Количество, "ID заказа", "ID позиции") '
                        f'VALUES (?,(SELECT Заказы.ID FROM Заказы '
                        f'INNER JOIN Пользователи ON Заказы."ID Пользователя" = Пользователи.ID '
                        f'WHERE Пользователи."ID TG" = {user_id} ORDER BY Заказы.ID DESC LIMIT 1),'
                        f'(SELECT ID FROM Позиции WHERE Имя = "{name}"))', [product[2]])


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
    name = message.from_user.first_name
    side_menu = ['/start', '/menu', '/card', '/orders']

    if message.text in side_menu:
        with con:  # Поиск пользователя в Базе, если его нет запись возможной о нём информации
            searching_user = con.execute('SELECT ID, Имя, "ID TG" FROM Пользователи WHERE "ID TG" = ?', [user_id])
            if len(searching_user.fetchall()) == 0:
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
                    con.execute(f'UPDATE OR IGNORE Пользователи SET Аватарка = ? '
                                f'WHERE Имя = "{name}" AND "ID TG" = {user_id}', [sl.Binary(avatar)])
            del searching_user
        if message.text == '/start':
            bot.send_message(message.chat.id, f"Привет {name}!\n"
                                              f"Мы рады приветствовать вас")
            bot.send_message(message.chat.id,
                             'Выберите категорию в Меню ⬇️', reply_markup=category())
        if message.text == '/menu':
            bot.send_message(message.chat.id,
                             'Выберите категорию в Меню ⬇️', reply_markup=category())
        if message.text == '/card':
            if user_id in dict_users.keys() and "Корзина" in dict_users[user_id].keys():
                text = order_info(user_id)
                bot.send_message(message.chat.id, text=text, reply_markup=cart_processing(case="show", chat_id=user_id))
            else:
                bot.send_message(message.chat.id, text="Ваша корзина пуста, перейдите в меню",
                                 reply_markup=cart_processing(case="Menu", chat_id=user_id))
        if message.text == '/orders':
            orders_dict = {}
            with con:
                orders = con.execute(f"SELECT Заказы.ID, Позиции.Имя, [Состав заказа].Количество, Позиции.Стоимость, "
                                     f"Заказы.Стоимость, Заказы.Время FROM Позиции "
                                     f"INNER JOIN [Состав заказа] on [Состав заказа].[ID позиции] = Позиции.ID "
                                     f"INNER JOIN Заказы ON [Состав заказа].[ID заказа] = Заказы.ID "
                                     f"INNER JOIN Пользователи ON Заказы.[ID Пользователя] = Пользователи.ID "
                                     f"WHERE Пользователи.[ID TG] = {user_id}")
            for product in orders.fetchall():
                if product[0] not in orders_dict.keys():
                    orders_dict.update({product[0]: {"Время": product[5], "Позиции": [product[1:5]]}})
                else:
                    orders_dict[product[0]]["Позиции"] += [product[1:5]]
            text = f"Ваши Заказы:\n\n"
            for order in orders_dict.items():
                total = 0
                text += f"Номер заказа: {order[0]}\n"
                text += f"Оформлен: {order[1]['Время']}\n"
                for products in order[1]["Позиции"]:
                    cost = products[1] * products[2]
                    index = order[1]["Позиции"].index(products) + 1
                    text += f"{index}.{products[0]}, кол-во:{products[1]}\n"
                    total = products[3]
                text += f"На сумму: {total}.BYN\n\n"
            bot.send_message(message.chat.id, text=text)

    if user_id in dict_users.keys() and "Оформление" in dict_users[user_id].keys():
        hide_keyboard = ReplyKeyboardRemove()
        text = ""
        finished_order = False
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
                order_to_base(user_id)
                text = order_info(user_id)
                finished_order = True

        elif dict_users[user_id]["Оформление"]["Способ Доставки"] == "Самовывоз":
            dict_users[user_id]["Оформление"].update({"Телефон": message.text})
            order_to_base(user_id)
            text = order_info(user_id)
            finished_order = True

        elif dict_users[user_id]["Оформление"]["Способ Доставки"] == "В заведении":
            if "Номер стола" not in dict_users[user_id]["Оформление"].keys():
                dict_users[user_id]["Оформление"].update({"Номер стола": message.text})
                text = "Укажите номер телефона"
            elif "Телефон" not in dict_users[user_id]["Оформление"].keys():
                dict_users[user_id]["Оформление"].update({"Телефон": message.text})
                order_to_base(user_id)
                text = order_info(user_id)
                finished_order = True

        if text != "":
            bot.send_message(chat_id=user_id, text=text, reply_markup=hide_keyboard)
        if finished_order:
            del dict_users[user_id]["Оформление"], dict_users[user_id]["Корзина"]


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
                              reply_markup=products(dict_users["Категории Меню"][index], id))

    if flag == 2:
        try:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='Выберите категорию в Меню ⬇️',
                                  reply_markup=category())
        except:
            bot.send_message(chat_id=call.message.chat.id,
                             text='Выберите категорию в Меню ⬇️',
                             reply_markup=category())

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
            select_product(id, count=group_id)
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
        operation = data[0]
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
        operation = data[0]
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
