import json
import math
import requests
import sqlite3 as sl
import telebot
from io import BytesIO
from PIL import Image
from datetime import datetime

from PIL.ImageDraw import ImageDraw
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton

with open("Config.json") as f:
    config = json.load(f)
    Token = config.get("telegram_token")
    database = config.get("database_path")
    geocoder_api = config.get("geocoder_api")
bot = telebot.TeleBot(Token)
con = sl.connect(database, check_same_thread=False)
dict_users = {}
dict_administrators = {"Администратор": {}, "Заказы": {}, "Принятые заказы": {}, "Комментарии": {}}


def update(case):
    with con:
        if case == "Обновить администраторов":
            administrators = con.execute("SELECT * FROM Администраторы")
            for information in administrators.fetchall():
                if "Администратор" not in dict_administrators.keys():
                    dict_administrators["Администратор"] = {
                        information[7]: {"Имя": information[1], "Фамилия": information[2], "Телефон": information[3],
                                         "Начало Работы": information[4], "Окончание Работы": information[5],
                                         "Уровень доступа": information[6]}}
                else:
                    dict_administrators["Администратор"].update(
                        {information[7]: {"Имя": information[1], "Фамилия": information[2], "Телефон": information[3],
                                          "Начало Работы": information[4], "Окончание Работы": information[5],
                                          "Уровень доступа": information[6]}})
        elif case == "Обновить категории":
            menu = con.execute("SELECT Название FROM 'Разделы Меню'")
            menu_categories = []
            for categories in menu.fetchall():
                menu_categories.append(categories[0])
            dict_users["Категории Меню"] = menu_categories


def admin_panel(case, user_id, index):
    if case == "Панель Администраторов":
        panel = InlineKeyboardMarkup()
        orders = InlineKeyboardButton("📋Заказы", callback_data=json.dumps([0, "orders"]))
        menu_settings = InlineKeyboardButton("🧁Изменения в меню", callback_data=json.dumps([0, "menu_settings"]))
        admin_settings = InlineKeyboardButton("⚙️Настройка администраторов", callback_data=json.dumps([0, "admin"]))
        statistics = InlineKeyboardButton("📈Статистика", callback_data=json.dumps([0, "statistics"]))
        history = InlineKeyboardButton("📆История", callback_data=json.dumps([0, "history"]))
        main_menu = InlineKeyboardButton("🏠Назад", callback_data=json.dumps([0, "main_menu"]))
        panel.add(orders, menu_settings, row_width=1)
        if dict_administrators["Администратор"][user_id]["Уровень доступа"] == 1:
            panel.add(admin_settings)
        panel.add(statistics, history, main_menu, row_width=1)
        return panel
    if case == "Просмотр заказов":
        state = InlineKeyboardMarkup()
        in_approve = InlineKeyboardButton("В обработке", callback_data=json.dumps([0, "in_approve"]))
        accepted_orders = InlineKeyboardButton("Принятые", callback_data=json.dumps([0, "accepted_orders"]))
        back_button = InlineKeyboardButton("Назад", callback_data=json.dumps([0, "settings"]))
        state.add(in_approve, accepted_orders, back_button, row_width=1)
        return state
    if case == "Заказы":
        if len(dict_administrators["Заказы"]) > 0:
            for order_number in dict_administrators["Заказы"]:
                orders = InlineKeyboardMarkup()
                text = "Новый Заказ "
                text += f"№: {order_number}\n\n"
                for position in dict_administrators['Заказы'][order_number]['Позиции']:
                    index = dict_administrators['Заказы'][order_number]['Позиции'].index(position) + 1
                    name, count = position[0], position[2]
                    text += f"{index}. {name}, кол-во: {count}\n"
                text += f"\n{dict_administrators['Заказы'][order_number]['Информация'][0]}\n"
                if dict_administrators['Заказы'][order_number]['Информация'][1] is not None:
                    text += f"Адрес: {dict_administrators['Заказы'][order_number]['Информация'][1]}\n"
                text += f"Оплата: {dict_administrators['Заказы'][order_number]['Информация'][3]}\n"
                text += f"Способ Доставки: {dict_administrators['Заказы'][order_number]['Информация'][4]}\n"
                text += f"Имя клиента: {dict_administrators['Заказы'][order_number]['Информация'][5]}\n"
                text += f"Номер для связи: {dict_administrators['Заказы'][order_number]['Информация'][6]}\n"
                text += f"Итого: {dict_administrators['Заказы'][order_number]['Информация'][2]}.BYN\n"
                accept = InlineKeyboardButton("Принять", callback_data=json.dumps([0, "accept", order_number]))
                orders.add(accept, row_width=1)
                if order_number is list(dict_administrators["Заказы"].keys())[-1]:
                    back = InlineKeyboardButton("Назад", callback_data=json.dumps([0, "orders", "new_message"]))
                    orders.add(back)
                bot.send_message(user_id, text=text, reply_markup=orders)
        else:
            bot.send_message(user_id, text="Новых заказов нет")

    if case == "Изменения в меню":
        categories_for_admin = InlineKeyboardMarkup()
        for category in dict_users["Категории Меню"]:
            index = dict_users["Категории Меню"].index(category)
            categories_for_admin.add(InlineKeyboardButton(category, callback_data=json.dumps([0, "category", index])))
        categories_for_admin.add(InlineKeyboardButton("Назад", callback_data=json.dumps([0, "settings"])))
        return categories_for_admin
    if case == "Позиции":
        positions_for_admin = InlineKeyboardMarkup()
        if "Изменения в меню" not in dict_administrators["Администратор"][user_id].keys():
            selected_category = dict_users["Категории Меню"][index]
            with con:
                positions = con.execute(f"SELECT Имя FROM Позиции "
                                        f"INNER JOIN [Разделы Меню] on Позиции.[ID раздела] = [Разделы Меню].ID "
                                        f"WHERE [Разделы Меню].Название = '{selected_category}'").fetchall()
                # [('Бадриджани',), ('Аджабсандали',), ('Ассорти-пхали',), ('Сациви',), ('Сациви из бадриджан',)]

                for position in positions:
                    if "Изменения в меню" not in dict_administrators["Администратор"][user_id].keys():
                        dict_administrators["Администратор"][user_id].update({"Изменения в меню": [position[0]]})
                    else:
                        dict_administrators["Администратор"][user_id]["Изменения в меню"] += [position[0]]
                    index = dict_administrators["Администратор"][user_id]["Изменения в меню"].index(position[0])
                    positions_for_admin.add(InlineKeyboardButton(position[0],
                                                                 callback_data=json.dumps([0, "position", index])))
        else:
            for position in dict_administrators["Администратор"][user_id]["Изменения в меню"]:
                index = dict_administrators["Администратор"][user_id]["Изменения в меню"].index(position)
                positions_for_admin.add(InlineKeyboardButton(position,
                                                             callback_data=json.dumps([0, "position", index])))
        positions_for_admin.add(InlineKeyboardButton("Назад",
                                                     callback_data=json.dumps([0, "menu_settings"])))
        return positions_for_admin
    if case == "Настройка позиции":
        with con:
            position = dict_administrators["Администратор"][user_id]["Изменение в позиции"]
            check_position = con.execute(f"SELECT Доступен FROM Позиции "
                                         f"WHERE Имя = '{position}'").fetchall()[0][0]
        position_settings = InlineKeyboardMarkup()
        change_name = InlineKeyboardButton("Изменить имя", callback_data=json.dumps([0, "name"]))
        change_description = InlineKeyboardButton("Изменить описание", callback_data=json.dumps([0, "description"]))
        change_image = InlineKeyboardButton("Изменить изображение", callback_data=json.dumps([0, "image"]))
        change_cost = InlineKeyboardButton("Изменить стоимость", callback_data=json.dumps([0, "cost"]))
        stop_position = InlineKeyboardButton("Остановить продажу", callback_data=json.dumps([0, "stop"]))
        start_position = InlineKeyboardButton("Возобновить продажу", callback_data=json.dumps([0, "start"]))
        back_button = InlineKeyboardButton("Назад", callback_data=json.dumps([0, "back"]))
        if dict_administrators['Администратор'][user_id]["Уровень доступа"] == 1:
            position_settings.add(change_name, change_description, change_image, change_cost, row_width=1)
        if check_position == "доступен":
            position_settings.add(stop_position)
        elif check_position == "не доступен":
            position_settings.add(start_position)
        position_settings.add(back_button)
        return position_settings

    if case == "Настройка администраторов":
        administrators_configuration = InlineKeyboardMarkup(row_width=1)
        create_administrator = InlineKeyboardButton("Добавление", callback_data=json.dumps([0, "add_admin"]))
        modify_administrator = InlineKeyboardButton("Изменение", callback_data=json.dumps([0, "modify_admin"]))
        delete_administrator = InlineKeyboardButton("Удаление", callback_data=json.dumps([0, "delete_admin"]))
        back = InlineKeyboardButton("Назад", callback_data=json.dumps([0, "settings"]))
        administrators_configuration.add(create_administrator, modify_administrator, delete_administrator, back)
        return administrators_configuration

    if case == "Добавление администраторов":
        create_administrators = InlineKeyboardMarkup(row_width=2)
        admin_id = InlineKeyboardButton("ID телеграм", callback_data=json.dumps([0, "new_id"]))
        admin_name = InlineKeyboardButton("Имя", callback_data=json.dumps([0, "new_name"]))
        admin_surname = InlineKeyboardButton("Фамилия", callback_data=json.dumps([0, "new_surname"]))
        admin_telephone = InlineKeyboardButton("Телефон", callback_data=json.dumps([0, "new_telephone"]))
        admin_work_begin = InlineKeyboardButton("Начало работы",
                                                callback_data=json.dumps([0, "new_work_start"]))
        admin_work_end = InlineKeyboardButton("Окончание Работы",
                                              callback_data=json.dumps([0, "new_work_end"]))
        admin_rights = InlineKeyboardButton("Уровень доступа", callback_data=json.dumps([0, "new_rights"]))
        create_administrators.add(admin_id, admin_name, admin_surname, admin_telephone, admin_work_begin,
                                  admin_work_end, admin_rights)
        if 'Настройка администраторов' in dict_administrators['Администратор'][user_id].keys():
            if 'Добавление' != dict_administrators['Администратор'][user_id]['Настройка администраторов']:
                cancel_button = InlineKeyboardButton("Отменить",
                                                     callback_data=json.dumps([0, "cancel_creation"]))
                save_button = InlineKeyboardButton("Сохранить", callback_data=json.dumps([0, "save_creation"]))
                create_administrators.row(cancel_button, save_button)
        return create_administrators

    if case == "Изменение администраторов":
        modify_administrators = InlineKeyboardMarkup(row_width=1)
        for telegram_id in dict_administrators["Администратор"].keys():
            name = dict_administrators["Администратор"][telegram_id]['Имя']
            surname = dict_administrators["Администратор"][telegram_id]['Фамилия']
            admin = InlineKeyboardButton(name + " " + surname,
                                         callback_data=json.dumps([0, "modify_in_admin", telegram_id]))
            modify_administrators.add(admin)
        back = InlineKeyboardButton("Назад", callback_data=json.dumps([0, "back_from_modifying"]))
        modify_administrators.add(back)
        return modify_administrators

    if case == "Настройка администратора":
        telegram_id = index
        admin_configuration = InlineKeyboardMarkup(row_width=2)
        admin_name = InlineKeyboardButton("Имя", callback_data=json.dumps([0, "admin_name", telegram_id]))
        admin_surname = InlineKeyboardButton("Фамилия", callback_data=json.dumps([0, "admin_surname", telegram_id]))
        admin_telephone = InlineKeyboardButton("Телефон", callback_data=json.dumps([0, "admin_telephone", telegram_id]))
        admin_work_begin = InlineKeyboardButton("Начало работы",
                                                callback_data=json.dumps([0, "work_start", telegram_id]))
        admin_work_end = InlineKeyboardButton("Окончание Работы",
                                              callback_data=json.dumps([0, "work_end", telegram_id]))
        admin_rights = InlineKeyboardButton("Уровень доступа", callback_data=json.dumps([0, "rights", telegram_id]))
        admin_configuration.add(admin_name, admin_surname, admin_telephone, admin_work_begin,
                                admin_work_end, admin_rights)
        if 'Изменение' != dict_administrators['Администратор'][user_id]['Настройка администраторов']:
            cancel_button = InlineKeyboardButton("Отменить",
                                                 callback_data=json.dumps([0, "cancel_changes", telegram_id]))
            save_button = InlineKeyboardButton("Сохранить", callback_data=json.dumps([0, "save_changes", telegram_id]))
            admin_configuration.row(cancel_button, save_button)
        return admin_configuration

    if case == "Удаление администраторов":
        delete_administrators = InlineKeyboardMarkup(row_width=1)
        for telegram_id in dict_administrators["Администратор"].keys():
            name = dict_administrators["Администратор"][telegram_id]['Имя']
            surname = dict_administrators["Администратор"][telegram_id]['Фамилия']
            delete_administrators.add(InlineKeyboardButton(name + " " + surname,
                                                           callback_data=json.dumps([0, "delete", telegram_id])))
        back = InlineKeyboardButton("Назад", callback_data=json.dumps([0, "back_from_deleting"]))
        delete_administrators.add(back)
        return delete_administrators

    if case == "Подтверждение удаления":
        telegram_id = index
        confirmation = InlineKeyboardMarkup(row_width=2)
        yes_button = InlineKeyboardButton("Да", callback_data=json.dumps([0, "Yes", telegram_id]))
        no_button = InlineKeyboardButton("Нет", callback_data=json.dumps([0, "No", telegram_id]))
        confirmation.add(no_button, yes_button)
        return confirmation

    # if case == "Статистика":
    # if case == "История":

    if case == "Отзыв к заказу":
        order_number = index
        feedback = InlineKeyboardMarkup()
        feedback_order = InlineKeyboardButton("Оставить отзыв к заказу",
                                              callback_data=json.dumps([5, "feedback_order", order_number]))
        no_thanks = InlineKeyboardButton("Нет, спасибо", callback_data=json.dumps([5, "quit"]))
        feedback.add(feedback_order, no_thanks)
        return feedback

    if case == "Отзыв":
        order_number = index
        feedback_type = InlineKeyboardMarkup(row_width=1)
        feedback_for_order = InlineKeyboardButton("Отзыв к заказу",
                                                  callback_data=json.dumps([5, "feedback_for_order", order_number]))
        feedback_for_position = InlineKeyboardButton("Отзыв к позиции",
                                                     callback_data=json.dumps(
                                                         [5, "feedback_for_position", order_number]))
        no_thanks = InlineKeyboardButton("Нет, спасибо", callback_data=json.dumps([5, "quit"]))
        feedback_type.add(feedback_for_order, feedback_for_position, no_thanks)
        return feedback_type

    if case == "Оценка заказа":
        order_number = index
        rate = InlineKeyboardMarkup()
        one = InlineKeyboardButton("⭐", callback_data=json.dumps([5, "1_star", 1, order_number]))
        two = InlineKeyboardButton("⭐", callback_data=json.dumps([5, "2_star", 2, order_number]))
        three = InlineKeyboardButton("⭐", callback_data=json.dumps([5, "3_star", 3, order_number]))
        four = InlineKeyboardButton("⭐", callback_data=json.dumps([5, "4_star", 4, order_number]))
        five = InlineKeyboardButton("⭐", callback_data=json.dumps([5, "5_star", 5, order_number]))
        rate.row(one, two, three, four, five)
        return rate

    if case == "Выбор позиции":
        order_number = index
        select_positions = InlineKeyboardMarkup()
        if "Отзыв к позиции" in dict_administrators["Комментарии"][user_id][order_number].keys():
            if dict_administrators["Комментарии"][user_id][order_number]["Отзыв к позиции"] == "Позиции":
                with con:
                    positions = con.execute(f"SELECT Имя FROM Позиции "
                                            f"INNER JOIN [Состав заказа] ON Позиции.ID = [Состав заказа].[ID позиции] "
                                            f"WHERE [Состав заказа].[ID заказа] = {order_number}").fetchall()
                    for position in positions:
                        if dict_administrators["Комментарии"][user_id][order_number]["Отзыв к позиции"] == "Позиции":
                            dict_administrators["Комментарии"][user_id][
                                order_number].update({"Отзыв к позиции": {"Позиции": [position[0]]}})
                        else:
                            dict_administrators["Комментарии"][user_id][order_number][
                                "Отзыв к позиции"]["Позиции"] += [position[0]]
                        index = dict_administrators["Комментарии"][user_id][order_number][
                            "Отзыв к позиции"]["Позиции"].index(position[0])
                        select_positions.add(InlineKeyboardButton
                                             (position[0],
                                              callback_data=json.dumps([5, "position", order_number, index])))
            else:
                for position in dict_administrators["Комментарии"][user_id][order_number]["Отзыв к позиции"]["Позиции"]:
                    index = dict_administrators["Комментарии"][user_id][order_number]["Отзыв к позиции"][
                        "Позиции"].index(position)
                    select_positions.add(InlineKeyboardButton
                                         (position, callback_data=json.dumps([5, "position", order_number, index])))
            select_positions.add(InlineKeyboardButton("Нет спасибо!", callback_data=json.dumps([5, "quit"])))
        return select_positions

    if case == "Отзыв к позиции":
        order_number = index[0]
        index_in_positions = index[1]
        rate = InlineKeyboardMarkup()
        one = InlineKeyboardButton("⭐", callback_data=json.dumps([5, "1_star", 1,
                                                                  order_number, index_in_positions]))
        two = InlineKeyboardButton("⭐", callback_data=json.dumps([5, "2_star", 2,
                                                                  order_number, index_in_positions]))
        three = InlineKeyboardButton("⭐", callback_data=json.dumps([5, "3_star", 3,
                                                                    order_number, index_in_positions]))
        four = InlineKeyboardButton("⭐", callback_data=json.dumps([5, "4_star", 4,
                                                                   order_number, index_in_positions]))
        five = InlineKeyboardButton("⭐", callback_data=json.dumps([5, "5_star", 5,
                                                                   order_number, index_in_positions]))
        rate.row(one, two, three, four, five)
        return rate


def category(case, user_id):
    if case == "Главная клавиатура":
        hello_board = InlineKeyboardMarkup()
        menu = InlineKeyboardButton("📂Меню", callback_data=json.dumps([2, "menu"]))
        profile = InlineKeyboardButton("🤗Профиль", callback_data=json.dumps([2, "profile"]))
        my_orders = InlineKeyboardButton("📋Мои заказы", callback_data=json.dumps([2, "orders"]))
        hello_board.add(menu, profile, my_orders, row_width=1)
        if user_id in dict_administrators["Администратор"].keys():
            settings = InlineKeyboardButton("⚙️Настройки", callback_data=json.dumps([0, "settings"]))
            hello_board.add(settings)
        return hello_board
    if case == "Клавиатура меню":
        updated_menu, flag = [], 1
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
            markup_category.add(InlineKeyboardButton(categories, callback_data=json.dumps([flag, index])))
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
        bot.send_photo(chat_id=user_id, photo=image, caption=caption,
                       reply_markup=select_count(count=1, case=case, group_id=count, group_el=index))


def select_count(count, case, group_id, group_el):
    data = [3, count, case, group_id, group_el]
    order_count = InlineKeyboardMarkup()
    button_decrease = InlineKeyboardButton("➖", callback_data=json.dumps(data + ["-"]))
    number = InlineKeyboardButton(f"{count}", callback_data=json.dumps([0]))
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
        data = [2, "menu"]
        menu = InlineKeyboardButton("Меню", callback_data=json.dumps(data))
        order_count.row(cart_button, add_button, menu)
    return order_count


def cart_processing(case, user_id):
    menu = InlineKeyboardButton("Меню", callback_data=json.dumps([2, "menu"]))
    if case == "show":
        data = [4, "change", "accept"]
        show_buttons = InlineKeyboardMarkup()
        change_button = InlineKeyboardButton("Изменить", callback_data=json.dumps([data[0], data[1]]))
        accept_order = InlineKeyboardButton("Подтвердить", callback_data=json.dumps([data[0], data[2]]))
        show_buttons.row(change_button, menu, accept_order)
        return show_buttons
    if case == "change":
        data = [4, "Изменить", "back", "<", ">", "x"]
        change_buttons = InlineKeyboardMarkup()
        accept_changes = InlineKeyboardButton("Изменить", callback_data=json.dumps([data[0], data[1]]))
        back_button = InlineKeyboardButton("Назад", callback_data=json.dumps([data[0], data[2]]))
        if "Изменённая Корзина" not in dict_users[user_id].keys() or dict_users[user_id]["Изменённая Корзина"] is None:
            dict_users[user_id]["Изменённая Корзина"] = dict_users[user_id]["Корзина"].copy()
        for el in dict_users[user_id]["Изменённая Корзина"]:
            cost = round(el[1] * el[2], 2)
            amount = el[2]
            index = dict_users[user_id]["Изменённая Корзина"].index(el)
            button_decrease = InlineKeyboardButton("<", callback_data=json.dumps([data[0], data[3], index]))
            button_increase = InlineKeyboardButton(">", callback_data=json.dumps([data[0], data[4], index]))
            button_delete = InlineKeyboardButton("X", callback_data=json.dumps([data[0], data[5], index]))
            amount_btn = InlineKeyboardButton(f"{index + 1}: {amount} шт.", callback_data=json.dumps([4]))
            cost_btn = InlineKeyboardButton(f"{cost}", callback_data=json.dumps([4]))
            change_buttons.row(button_decrease, amount_btn, cost_btn, button_increase, button_delete)
            if el is dict_users[user_id]["Изменённая Корзина"][-1]:
                change_buttons.row(back_button, menu, accept_changes)
        if len(dict_users[user_id]["Изменённая Корзина"]) == 0:
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


def order_info(user_id, case):
    if case == "current order":
        number, order = None, None
        if "Оформление" in dict_users[user_id].keys():
            with con:
                number = con.execute(f'SELECT Заказы.ID FROM Заказы INNER JOIN Пользователи '
                                     f'ON Заказы.[ID Пользователя] = Пользователи.ID '
                                     f'WHERE Пользователи.[ID TG] = {user_id} ORDER BY Заказы.ID DESC LIMIT 1;')
                is_phone = con.execute(f'SELECT Телефон FROM Пользователи '
                                       f'WHERE "ID TG" = {user_id}')
            telephone = is_phone.fetchall()[0][0]
            number = number.fetchall()[0][0]

            order = f"\n"

            for information in dict_users[user_id]["Оформление"].items():
                order += information[0] + " : " + information[1] + "\n"
            if telephone is not None:
                order += f"Номер телефона : {telephone}"
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
            cost = round(position[1] * position[2], 2)
            text += f"{indexing}. {position[0]}, кол-во: {position[2]} сумма: {cost}.BYN\n"
            indexing += 1
            total += cost
        if order is not None:
            text += order
        text += f"Итого: {round(total, 2)} BYN"
        return text
    if case == "show orders":
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
                index = order[1]["Позиции"].index(products) + 1
                text += f"{index}.{products[0]}, кол-во:{products[1]}\n"
                total = products[3]
            text += f"На сумму: {total}.BYN\n\n"
        return text


def order_to_base(user_id):
    if "Телефон" in dict_users[user_id]["Оформление"].keys():
        telephone = dict_users[user_id]["Оформление"]["Телефон"]
    else:
        telephone = None
    address = None
    if dict_users[user_id]["Оформление"]["Способ Доставки"] == "Доставка":
        street = dict_users[user_id]["Оформление"]["Улица"]
        house = dict_users[user_id]["Оформление"]["Дом"]
        apartment = dict_users[user_id]["Оформление"]["Квартира"]
        address = street + ", " + house + ", " + apartment
    cost = sum(x[1] * x[2] for x in dict_users[user_id]["Корзина"])
    cost = round(cost, 2)
    payment = dict_users[user_id]["Оформление"]["Способ Оплаты"]
    delivery = dict_users[user_id]["Оформление"]["Способ Доставки"]
    current_date_time = datetime.now().replace(microsecond=0)
    with con:
        if telephone is not None:
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


# {687986481: {'Имя': 'Никита', 'Фамилия': 'Саркисов', 'Телефон': '+375256910740', 'Начало Работы': '25.09.2022',
# 'Окончание Работы': None, 'Уровень доступа': 1}}
@bot.message_handler(content_types=['text', 'photo'])
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
            if user_id not in dict_users.keys() and user_id not in dict_administrators["Администратор"].keys():
                bot.send_message(message.chat.id, f"Привет 🤩 {name}!😍\n"
                                                  f"Мы рады приветствовать вас")
            if user_id in dict_administrators["Администратор"].keys():
                bot.send_message(message.chat.id, f"Добро пожаловать Администратор 💻{name}!")

            bot.send_message(message.chat.id,
                             '📲Выберите интересующий вас раздел',
                             reply_markup=category(case="Главная клавиатура", user_id=user_id))

        if message.text == '/menu':
            bot.send_message(message.chat.id,
                             'Выберите категорию в Меню ⬇️',
                             reply_markup=category(case="Клавиатура меню", user_id=user_id))
        if message.text == '/card':
            if user_id in dict_users.keys() and "Корзина" in dict_users[user_id].keys():
                text = order_info(user_id, case="current order")
                bot.send_message(message.chat.id, text=text, reply_markup=cart_processing(case="show", user_id=user_id))
            else:
                bot.send_message(message.chat.id, text="Ваша корзина пуста, перейдите в меню",
                                 reply_markup=cart_processing(case="Menu", user_id=user_id))
        if message.text == '/orders':
            text = order_info(user_id, case="show orders")
            bot.send_message(message.chat.id, text=text)

    if user_id in dict_users.keys() and "Телефон" in dict_users[user_id].keys():
        if dict_users[user_id]["Телефон"] is None:
            with con:
                con.execute(f'UPDATE OR IGNORE Пользователи '
                            f'SET Телефон = "{message.text}" '
                            f'WHERE "ID TG" = {user_id}')
            bot.send_message(message.chat.id,
                             'Данные обновлены\n📲Выберите интересующий вас раздел',
                             reply_markup=category(case="Главная клавиатура", user_id=user_id))
            del dict_users[user_id]["Телефон"]

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
                with con:
                    is_phone = con.execute(f'SELECT Телефон FROM Пользователи '
                                           f'WHERE "ID TG" = {user_id}')
                    telephone = is_phone.fetchall()[0][0]
                    if telephone is not None:
                        order_to_base(user_id)
                        text = order_info(user_id, case="current order")
                        finished_order = True

                    else:
                        text = "Укажите номер Телефона"
            elif "Телефон" not in dict_users[user_id]["Оформление"].keys() and not finished_order:
                dict_users[user_id]["Оформление"].update({"Телефон": message.text})
                order_to_base(user_id)
                text = order_info(user_id, case="current order")
                finished_order = True

        elif dict_users[user_id]["Оформление"]["Способ Доставки"] == "Самовывоз":
            dict_users[user_id]["Оформление"].update({"Телефон": message.text})
            order_to_base(user_id)
            text = order_info(user_id, case="current order")
            finished_order = True

        elif dict_users[user_id]["Оформление"]["Способ Доставки"] == "В заведении":
            if "Номер стола" not in dict_users[user_id]["Оформление"].keys():
                dict_users[user_id]["Оформление"].update({"Номер стола": message.text})
                with con:
                    is_phone = con.execute(f'SELECT Телефон FROM Пользователи '
                                           f'WHERE "ID TG" = {user_id}')
                    telephone = is_phone.fetchall()[0][0]
                    if telephone is not None:
                        order_to_base(user_id)
                        text = order_info(user_id, case="current order")
                        finished_order = True
                    else:
                        text = "Укажите номер телефона"
            elif "Телефон" not in dict_users[user_id]["Оформление"].keys() and not finished_order:
                dict_users[user_id]["Оформление"].update({"Телефон": message.text})
                order_to_base(user_id)
                text = order_info(user_id, case="current order")
                finished_order = True

        if text != "":
            bot.send_message(chat_id=user_id, text=text, reply_markup=hide_keyboard)
            print("сработало отправка пользователю")
            bot.send_message(chat_id=-4022782368, text=text)
            print("Сработало отправка в группу")
        if finished_order:
            del dict_users[user_id]["Оформление"], dict_users[user_id]["Корзина"]

    if user_id in dict_administrators['Администратор'].keys():
        if "Изменение в позиции" in dict_administrators['Администратор'][user_id].keys():
            position = dict_administrators['Администратор'][user_id]["Изменение в позиции"]
            operation = dict_administrators['Администратор'][user_id]["Операция"]
            if message.content_type == 'text':
                new_info = message.text
                with con:
                    con.execute(f"UPDATE OR IGNORE Позиции "
                                f"SET {operation} = '{new_info}' "
                                f"WHERE Имя = '{position}'")
            else:
                photo = message.photo[-1]
                file_id = photo.file_id
                file_info = bot.get_file(file_id)
                file_path = file_info.file_path
                url = f"https://api.telegram.org/file/bot{Token}/{file_path}"
                new_info = requests.get(url).content
                with con:
                    con.execute(f"UPDATE OR IGNORE Позиции "
                                f"SET {operation} = ? "
                                f"WHERE Имя = '{position}' ", [new_info])
            del dict_administrators['Администратор'][user_id]["Изменение в позиции"]
            del dict_administrators['Администратор'][user_id]["Операция"]
            bot.send_message(user_id, text="Данные внесены успешно")
        elif "Настройка администраторов" in dict_administrators['Администратор'][user_id].keys():
            values = {"ID TG": "Новый ID", "Имя": "Новое Имя", "Фамилия": "Новая Фамилия", "Телефон": "Новый Телефон",
                      "Начало Работы": "Новая дата начала",
                      "Окончание Работы": "Новая дата окончания", "Уровень": "Новый уровень"}
            if "Добавление" != dict_administrators['Администратор'][user_id]["Настройка администраторов"]:
                if "Добавление" in dict_administrators['Администратор'][user_id]["Настройка администраторов"].keys():
                    path = dict_administrators['Администратор'][user_id][
                        "Настройка администраторов"]["Добавление"].copy()
                    for operation, setting in path.items():
                        if operation in values.keys() and values[operation] == setting:
                            new_value = message.text
                            dict_administrators['Администратор'][user_id]["Настройка администраторов"][
                                "Добавление"][operation] = new_value
                    bot.send_message(user_id, text="Данные добавлены сохраните для изменения",
                                     reply_markup=admin_panel(case="Добавление администраторов", user_id=user_id,
                                                              index=None))

            if "Изменение" != dict_administrators['Администратор'][user_id]["Настройка администраторов"]:
                if "Изменение" in dict_administrators['Администратор'][user_id]["Настройка администраторов"].keys():
                    admin_id = list(dict_administrators['Администратор']
                                    [user_id]["Настройка администраторов"]["Изменение"].copy())[0]
                    path = dict_administrators['Администратор'][user_id]["Настройка администраторов"]["Изменение"][
                        admin_id].copy()

                    for operation, setting in path.items():
                        if operation in values.keys() and values[operation] == setting:
                            new_value = message.text
                            dict_administrators['Администратор'][user_id]["Настройка администраторов"]["Изменение"][
                                admin_id][operation] = new_value
                    bot.send_message(user_id, text="Данные добавлены сохраните для изменения",
                                     reply_markup=admin_panel(case="Настройка администратора", user_id=user_id,
                                                              index=admin_id))

    if user_id in dict_administrators["Комментарии"].keys():
        order_number = list(dict_administrators["Комментарии"][user_id])[0]
        if "Отзыв к заказу" in dict_administrators["Комментарии"][user_id][order_number].keys():
            rate = dict_administrators["Комментарии"][user_id][order_number]["Отзыв к заказу"]["Оценка"]
            with con:
                id = con.execute(f"SELECT ID FROM Пользователи "
                                 f"WHERE [ID TG] = {user_id}").fetchall()[0][0]
                con.execute(f"INSERT OR IGNORE INTO Комментарии "
                            f"(Комментарий, [ID Пользователя], [ID Заказа], Оценка) "
                            f"VALUES (?, ?, ?, ?)", [message.text, id, order_number, rate])
                search_for_commented_positions = con.execute(f"SELECT [ID Позиции] FROM Комментарии "
                                                             f"WHERE [ID Заказа] = {order_number}").fetchall()[0][0]
                del dict_administrators["Комментарии"][user_id][order_number]["Отзыв к заказу"]
                if search_for_commented_positions is None:
                    dict_administrators["Комментарии"][user_id][order_number].update({"Отзыв к позиции": "Позиции"})
                    bot.send_message(chat_id=user_id, text="Вы можете оставить отзыв и к позициям",
                                     reply_markup=admin_panel(case="Выбор позиции",
                                                              user_id=user_id, index=order_number))
                else:
                    bot.send_message(chat_id=user_id, text="Спасибо, за отзыв")
        elif "Отзыв к позиции" in dict_administrators["Комментарии"][user_id][order_number].keys():
            print(dict_administrators["Комментарии"])
            rate = dict_administrators["Комментарии"][user_id][order_number]["Отзыв к позиции"]["Оценка"]
            with con:
                id = con.execute(f"SELECT ID FROM Пользователи "
                                 f"WHERE [ID TG] = {user_id}").fetchall()[0][0]
                position = dict_administrators["Комментарии"][user_id][order_number]["Отзыв к позиции"][
                    "Выбранная Позиция"]
                position_id = con.execute(f"SELECT ID FROM Позиции "
                                          f"WHERE Имя = '{position}'").fetchall()[0][0]
                con.execute(f"INSERT OR IGNORE INTO Комментарии "
                            f"(Комментарий, [ID Пользователя], [ID Позиции], [ID Заказа], Оценка) "
                            f"VALUES (?, ?, ?, ?, ?)", [message.text, id, position_id, order_number, rate])
                if 'Позиции' in dict_administrators["Комментарии"][user_id][order_number]["Отзыв к позиции"].keys():
                    position = dict_administrators["Комментарии"][user_id][order_number][
                        "Отзыв к позиции"]['Выбранная Позиция']
                    if len(dict_administrators["Комментарии"][user_id][order_number]["Отзыв к позиции"]["Позиции"]) > 0:
                        index = dict_administrators["Комментарии"][user_id][order_number][
                            "Отзыв к позиции"]["Позиции"].index(position)
                        del dict_administrators["Комментарии"][user_id][order_number]["Отзыв к позиции"]["Позиции"][
                            index]
                        dict_administrators["Комментарии"][user_id][order_number][
                            "Отзыв к позиции"]['Выбранная Позиция'] = None
                bot.send_message(chat_id=user_id, text="Вы можете оставить отзыв и к позициям",
                                 reply_markup=admin_panel(case="Выбор позиции",
                                                          user_id=user_id, index=order_number))


@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    bot.answer_callback_query(callback_query_id=call.id, )
    id = call.message.chat.id
    call.data = json.loads(call.data)
    flag = call.data[0]
    data = []
    if len(call.data) > 1:
        data = call.data[1:]

    if flag == 0:
        opertions = ["settings", "orders", "menu_settings", "admin", "statistics", "history", "main_menu"]
        order_operations = ["settings", "orders", "in_approve", "accepted_orders", "accept", "complete"]
        position_operations = {"name": "Имя", "description": "Описание", "image": "Картинка", "cost": "Стоимость",
                               "stop": "Не доступен", "start": "доступен", "back": "Назад"}
        admin_operations = ["admin", "add_admin", "modify_admin", "delete_admin", "modify_in_admin",
                            "back_from_modifying"]
        admin_creation = ["new_id", "new_name", "new_surname", "new_telephone", "new_start", "new_end", "new_rights",
                          "cancel_creation", "save_creation"]
        admin_configuration = ["admin_name", "admin_surname", "admin_telephone", "work_start", "work_end", "rights",
                               "cancel_changes", "save_changes"]
        admin_deleting = ["delete", "Yes", "No", "back_from_deleting"]
        operation = data[0]
        if operation == "main_menu":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text='📲Выберите интересующий вас раздел',
                                  reply_markup=category(case="Главная клавиатура", user_id=id))
        elif operation in order_operations:
            if operation == "settings":
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="📲Выберите интересующий вас раздел",
                                      reply_markup=admin_panel(case="Панель Администраторов", user_id=id, index=None))
            if operation == "orders":

                if len(data) == 1:
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text="Выберите какие заказы вы желаете посмотреть",
                                          reply_markup=admin_panel(case="Просмотр заказов", user_id=id, index=None))
                else:
                    bot.send_message(chat_id=call.message.chat.id, text="Выберите какие заказы вы желаете посмотреть",
                                     reply_markup=admin_panel(case="Просмотр заказов", user_id=id, index=None))
            if operation == "in_approve":
                with con:
                    orders = {}
                    order_information = con.execute("SELECT Заказы.ID, Время, Адресс, Стоимость, Оплата, "
                                                    "Доставка, Имя, Телефон FROM Заказы INNER JOIN "
                                                    "Пользователи ON Заказы.[ID Пользователя] = Пользователи.ID "
                                                    "WHERE Состояние = 'Обработка'").fetchall()
                    for order in order_information:
                        orders.update({order[0]: {"Информация": order[1:]}})

                    for order_number in orders.keys():
                        positions = con.execute(f"SELECT Позиции.Имя, Позиции.Стоимость, [Состав заказа].Количество "
                                                f"FROM [Состав заказа] INNER JOIN Позиции ON "
                                                f"[Состав заказа].[ID позиции] = Позиции.ID "
                                                f"WHERE [Состав заказа].[ID заказа] = {order_number}").fetchall()
                        orders[order_number].update({"Позиции": positions})
                    for order_number in orders:
                        if order_number not in dict_administrators["Заказы"].keys():
                            dict_administrators["Заказы"].update({order_number: orders[order_number]})
                admin_panel(case="Заказы", user_id=id, index=None)
            if operation == "accepted_orders":
                if len(dict_administrators["Принятые заказы"]) > 0:
                    for order_number in dict_administrators["Принятые заказы"]:
                        orders = InlineKeyboardMarkup()
                        text = "Новый Заказ "
                        text += f"№: {order_number}\n\n"
                        for position in dict_administrators['Принятые заказы'][order_number]['Позиции']:
                            index = dict_administrators['Принятые заказы'][order_number]['Позиции'].index(position) + 1
                            name, count = position[0], position[2]
                            text += f"{index}. {name}, кол-во: {count}\n"
                        text += f"\n{dict_administrators['Принятые заказы'][order_number]['Информация'][0]}\n"
                        if dict_administrators['Принятые заказы'][order_number]['Информация'][1] is not None:
                            text += f"Адрес: {dict_administrators['Принятые заказы'][order_number]['Информация'][1]}\n"
                        text += f"Оплата: {dict_administrators['Принятые заказы'][order_number]['Информация'][3]}\n"
                        text += f"Способ Доставки: {dict_administrators['Принятые заказы'][order_number]['Информация'][4]}\n"
                        text += f"Имя клиента: {dict_administrators['Принятые заказы'][order_number]['Информация'][5]}\n"
                        text += f"Номер для связи: {dict_administrators['Принятые заказы'][order_number]['Информация'][6]}\n"
                        text += f"Итого: {dict_administrators['Принятые заказы'][order_number]['Информация'][2]}.BYN\n"
                        complete = InlineKeyboardButton("Завершить",
                                                        callback_data=json.dumps([0, "complete", order_number]))
                        orders.add(complete, row_width=1)
                        if order_number is list(dict_administrators["Принятые заказы"].keys())[-1]:
                            back = InlineKeyboardButton("Назад", callback_data=json.dumps([0, "orders", "new_message"]))
                            orders.add(back)
                        bot.send_message(id, text=text, reply_markup=orders)
                else:
                    bot.send_message(id, text="Еще нет принятых заказов")
            if operation == "accept":
                order_number = data[1]
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="Заказ принят", reply_markup=None)
                order = dict_administrators["Заказы"][order_number]
                dict_administrators["Принятые заказы"].update({order_number: order})
                del dict_administrators["Заказы"][order_number]
                with con:
                    con.execute(f"UPDATE OR IGNORE Заказы "
                                f"SET Состояние = 'Готовится' WHERE ID = {order_number}")
            if operation == "complete":
                order_number = data[1]
                with con:
                    user_id = con.execute(f"SELECT [ID TG] FROM Пользователи "
                                          f"INNER JOIN Заказы ON Заказы.[ID Пользователя] = Пользователи.ID "
                                          f"WHERE Заказы.ID = {order_number}").fetchall()[0][0]
                    con.execute(f"UPDATE OR IGNORE Заказы "
                                f"SET Состояние = 'Выполнен' WHERE ID = {order_number}")
                bot.send_message(id, text="Уведомляю пользователя о завершении")
                bot.send_message(user_id,
                                 text="🤩😍Ваш заказ выполнен успешно🤩😍.\n"
                                      "В целях повышения качества обслуживания оставьте пожалуйста ваш отзыв",
                                 reply_markup=admin_panel(case="Отзыв к заказу", user_id=user_id, index=order_number))
        elif operation == "menu_settings":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="Выберите Категорию из меню",
                                  reply_markup=admin_panel(case="Изменения в меню", user_id=id, index=None))
        elif operation == "category":
            index = data[1]
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=f"Выберите позицию {dict_users['Категории Меню'][index]}",
                                  reply_markup=admin_panel(case="Позиции", user_id=id, index=index))
        elif operation == "position":
            index = data[1]
            position = dict_administrators["Администратор"][id]["Изменения в меню"][index]
            dict_administrators["Администратор"][id].update({"Изменение в позиции": position})
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=f"Меню настроек для {position}",
                                  reply_markup=admin_panel(case="Настройка позиции", user_id=id, index=None))
        elif operation in position_operations.keys():
            position = dict_administrators["Администратор"][id]["Изменение в позиции"]
            if operation != "back":
                dict_administrators["Администратор"][id].update({"Операция": position_operations[operation]})

                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text=f"Отправьте новое {position_operations[operation]}")
            else:
                del dict_administrators["Администратор"][id]["Изменение в позиции"]
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text=f"Выберите позицию",
                                      reply_markup=admin_panel(case="Позиции", user_id=id, index=None))
        elif operation in admin_operations:
            text, settings, keyboard = None, None, None
            if operation == "admin":
                text = "👮‍♀️Панель настройки администраторов"
                keyboard = admin_panel(case="Настройка администраторов", user_id=id, index=None)
            elif operation == "add_admin":
                settings = "Добавление"
                text = "Данные необходимые для ввода\n" + "Обязательные поля: ID, Имя, Фамилия, Уровень Доступа 1 или 2"
                keyboard = admin_panel(case="Добавление администраторов", user_id=id, index=None)
            elif operation == "modify_admin":
                settings = "Изменение"
                text = "Выберите Администратора для изменения"
                keyboard = admin_panel(case="Изменение администраторов", user_id=id, index=None)
            elif operation == "delete_admin":
                settings = "Удаление"
                text = "Выберите Администратора которого хотите удалить"
                keyboard = admin_panel(case="Удаление администраторов", user_id=id, index=None)
            elif operation == "modify_in_admin":
                telegram_id = data[1]
                text = "Выберите что нужно изменить"
                keyboard = admin_panel(case="Настройка администратора", user_id=id, index=telegram_id)
            elif operation == "back_from_modifying":
                text = "👮‍♀️Панель настройки администраторов"
                del dict_administrators["Администратор"][id]["Настройка администраторов"]
                keyboard = admin_panel(case="Настройка администраторов", user_id=id, index=None)
            if "Настройка администраторов" not in dict_administrators["Администратор"][id].keys():
                if settings is not None:
                    dict_administrators["Администратор"][id].update({"Настройка администраторов": settings})
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=text, reply_markup=keyboard)
        elif operation in admin_creation:
            text, keyboard, changed, new_info = None, None, None, None
            if operation == "new_id":
                text = "Введите новый ID"
                changed, new_info = "ID TG", "Новый ID"
            elif operation == "new_name":
                text = "Введите новое Имя"
                changed, new_info = "Имя", "Новое Имя"
            elif operation == "new_surname":
                text = "Введите новую фамилию"
                changed, new_info = "Фамилия", "Новая Фамилия"
            elif operation == "new_telephone":
                text = "Введите новый телефон"
                changed, new_info = "Телефон", "Новый Телефон"
            elif operation == "new_start":
                text = "Введите новую дату поступление на работу"
                changed, new_info = "Начало Работы", "Новая дата начала"
            elif operation == "new_end":
                text = "Введите новую дату увольнения с работы"
                changed, new_info = "Окончание Работы", "Новая дата окончания"
            elif operation == "new_rights":
                changed, new_info = "Уровень", "Новый уровень"
                text = "Выберите уровень доступа"
            elif operation == "cancel_creation":
                del dict_administrators["Администратор"][id]['Настройка администраторов']
                text = "👮‍♀️Панель настройки администраторов\n" + "Изменения отменены"
                keyboard = admin_panel(case="Настройка администраторов", user_id=id, index=None)
            elif operation == "save_creation":
                path = dict_administrators["Администратор"][id]["Настройка администраторов"]["Добавление"]
                keys_to_check = ["ID TG", "Имя", "Фамилия", "Уровень"]
                if all(key in path for key in keys_to_check):
                    text = "👮‍♀️Панель настройки администраторов\n" + "Данные обновлены успешно"
                    with con:
                        con.execute(f"INSERT OR IGNORE INTO Администраторы "
                                    f"([ID TG], Имя, Фамилия, [Уровень] ) values (?,?,?,?) ",
                                    [path["ID TG"], path["Имя"], path["Фамилия"], path["Уровень"]])
                    for information in path.items():
                        if information[0] not in keys_to_check:
                            con.execute(f"UPDATE OR IGNORE Администраторы "
                                        f"SET {information[0]} = '{information[1]}' "
                                        f"WHERE [ID TG] = {path['ID TG']}")
                    update(case="Обновить администраторов")
                    keyboard = admin_panel(case="Настройка администраторов", user_id=id, index=None)
                else:
                    text = "Вы ввели не все обязательные поля для ввода\n" \
                           + "Обязательные поля: ID, Имя, Фамилия, Уровень доступа 1 или 2"
                    keyboard = admin_panel(case="Добавление администраторов", user_id=id, index=None)
            if 'Настройка администраторов' in dict_administrators["Администратор"][id].keys():
                if type(dict_administrators["Администратор"][id]['Настройка администраторов']) is not dict:
                    change = {"Добавление": {changed: new_info}}
                    dict_administrators["Администратор"][id]['Настройка администраторов'] = change
                else:
                    path = dict_administrators["Администратор"][id]['Настройка администраторов']["Добавление"]
                    path[changed] = new_info
            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text=text, reply_markup=keyboard)
            except:
                bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
                bot.send_message(chat_id=call.message.chat.id, text=text, reply_markup=keyboard)
        elif operation in admin_configuration:
            telegram_id = data[1]
            text, keyboard, changed, new_info = None, None, None, None
            if operation == "admin_name":
                text = "Введите новое Имя"
                changed, new_info = "Имя", "Новое Имя"
            elif operation == "admin_surname":
                text = "Введите новую фамилию"
                changed, new_info = "Фамилия", "Новая Фамилия"
            elif operation == "admin_telephone":
                text = "Введите новый телефон"
                changed, new_info = "Телефон", "Новый Телефон"
            elif operation == "work_start":
                text = "Введите новую дату поступление на работу"
                changed, new_info = "Начало Работы", "Новая дата начала"
            elif operation == "work_end":
                text = "Введите новую дату увольнения с работы"
                changed, new_info = "Окончание Работы", "Новая дата окончания"
            elif operation == "rights":
                changed, new_info = "Уровень", "Новый уровень"
                text = "Выберите уровень доступа"
            elif operation == "save_changes":
                text = "👮‍♀️Панель настройки администраторов\n" + "Данные обновлены успешно"
                path = dict_administrators["Администратор"][id]["Настройка администраторов"]["Изменение"]
                new_info = path[telegram_id].items()
                for information in new_info:
                    with con:
                        con.execute(f"UPDATE OR IGNORE Администраторы "
                                    f"SET {information[0]} = '{information[1]}' "
                                    f"WHERE [ID TG] = {telegram_id}")
                update(case="Обновить администраторов")
                keyboard = admin_panel(case="Настройка администраторов", user_id=id, index=None)
                del dict_administrators["Администратор"][id]['Настройка администраторов']
            elif operation == "cancel_changes":
                del dict_administrators["Администратор"][id]['Настройка администраторов']
                text = "👮‍♀️Панель настройки администраторов\n" + "Изменения отменены"
                keyboard = admin_panel(case="Настройка администраторов", user_id=id, index=None)
            if 'Настройка администраторов' in dict_administrators["Администратор"][id].keys():
                if type(dict_administrators["Администратор"][id]['Настройка администраторов']) is not dict:
                    change = {"Изменение": {telegram_id: {changed: new_info}}}
                    dict_administrators["Администратор"][id]['Настройка администраторов'] = change
                else:
                    path = dict_administrators["Администратор"][id]['Настройка администраторов']["Изменение"]
                    path[telegram_id][changed] = new_info
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=text, reply_markup=keyboard)
        elif operation in admin_deleting:
            text, keyboard, telegram_id = None, None, None
            if len(data) > 1:
                telegram_id = data[1]
            if operation == "delete":
                text = "Вы уверены?"
                keyboard = admin_panel(case="Подтверждение удаления", user_id=id, index=telegram_id)
            elif operation == "back_from_deleting":
                text = "👮‍♀️Панель настройки администраторов"
                keyboard = admin_panel(case="Настройка администраторов", user_id=id, index=None)
            elif operation == "Yes":
                with con:
                    con.execute(f"DELETE FROM Администраторы "
                                f"WHERE [ID TG] = {telegram_id} ")
                text = "Операция Выполнена успешно"
                del dict_administrators["Администратор"][telegram_id]
                update(case="Обновить администраторов")
                keyboard = admin_panel(case="Удаление администраторов", user_id=id, index=None)
            elif operation == "No":
                text = "Выберите Администратора которого хотите удалить"
                keyboard = admin_panel(case="Удаление администраторов", user_id=id, index=None)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=text, reply_markup=keyboard)

    elif flag == 1:
        index = data[0]
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="Выбирайте",
                              reply_markup=products(dict_users["Категории Меню"][index], id))

    elif flag == 2:
        operation = data[0]
        if operation == "menu":
            try:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text='Выберите категорию в Меню ⬇️',
                                      reply_markup=category(case="Клавиатура меню", user_id=id))
            except:
                bot.send_message(chat_id=call.message.chat.id,
                                 text='Выберите категорию в Меню ⬇️',
                                 reply_markup=category(case="Клавиатура меню", user_id=id))
        elif operation == "profile":
            with con:
                user_profile = con.execute(f'SELECT * FROM Пользователи WHERE [ID TG] = {id}')
                user_orders = con.execute(f'SELECT COUNT(*) from Заказы '
                                          f'INNER JOIN Пользователи ON Заказы."ID Пользователя" = Пользователи.ID '
                                          f'WHERE "ID TG" = {id}')
                profile_keyboard = InlineKeyboardMarkup()
                request_phone = InlineKeyboardButton("📱Ввести номер", callback_data=json.dumps([2, "phone"]))
                menu = InlineKeyboardButton("Меню🥙", callback_data=json.dumps([2, "menu"]))
                for information in user_profile.fetchall():
                    name = information[1]
                    phone = information[2]
                    image = Image.open(BytesIO(information[3]))
                user_orders = user_orders.fetchall()[0][0]
                image = image.resize((350, 380))
                no_phone = False
                caption = f"\n\nИмя: {name}\n"
                if phone is None:
                    caption += f"Телефон: Нет информации\n"
                    no_phone = True
                    profile_keyboard.row(request_phone, menu)
                else:
                    caption += f"Телефон: {phone}\n"
                    profile_keyboard.row(menu)
                caption += f"Количество заказов: {user_orders}"
                if no_phone:
                    caption += "\n\nНе хотите ли ввести номер телефона?"
                bot.send_photo(chat_id=id, photo=image, caption=caption, reply_markup=profile_keyboard)
        elif operation == "orders":
            text = order_info(id, case="show orders")
            bot.send_message(id, text=text)
        elif operation == "phone":
            dict_users.update({id: {"Телефон": None}})
            bot.send_message(id, text="Введите номер телефона\nВ формате: +375251234567")

    elif flag == 3:
        count, case, group_id, group_el, operation = data[0], data[1], data[2], data[3], data[4]
        configuration = ["-", "+", "*"]
        if operation in configuration:
            if operation == "-":
                if count > 0:
                    count -= 1
            elif operation == "+":
                count += 1
            elif operation == "*":
                next_group = group_id + 1
                case = 0
                select_product(id, count=next_group)
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=select_count(count, case, group_id, group_el))
        elif operation == "add":
            if count != 1:
                count = 1
                bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              reply_markup=select_count(count, case, group_id, group_el))
            name = dict_users[id]["groups"][group_id][group_el][0]
            price = dict_users[id]["groups"][group_id][group_el][3]
            bot.send_message(chat_id=call.message.chat.id,
                             text=f'Успешно добавлено:\n'
                                  f'{name}: {count} шт. на сумму: {round(count * price, 2)}')
            if "Корзина" not in dict_users[id].keys():
                dict_users[id].update({"Корзина": [[name, price, count]]})
            else:
                item = next((x for x in dict_users[id]["Корзина"] if x[0] == name), None)
                if item:
                    item[2] += count
                else:
                    dict_users[id]["Корзина"] += [[name, price, count]]
        elif operation == "cart":
            if "Корзина" not in dict_users[id].keys() or dict_users[id]["Корзина"] is None:
                bot.send_message(chat_id=call.message.chat.id,
                                 text='Ваша корзина пуста')
            else:
                text = order_info(id, case="current order")
                bot.send_message(chat_id=call.message.chat.id,
                                 text=text,
                                 reply_markup=cart_processing(case="show", user_id=id))

    elif flag == 4:
        operation = data[0]
        index = 0
        if len(data) > 1:
            index = data[1]
        configuration = ["change", "<", ">", "x", "back"]
        if operation in configuration:
            case = None
            if operation == "change":
                case = "change"
            elif operation == "<":
                case = "change"
                amount = dict_users[id]["Изменённая Корзина"][index][2]
                amount -= 1
                if amount >= 0:
                    dict_users[id]["Изменённая Корзина"][index][2] = amount
            elif operation == ">":
                case = "change"
                amount = dict_users[id]["Изменённая Корзина"][index][2]
                amount += 1
                dict_users[id]["Изменённая Корзина"][index][2] = amount
            elif operation == "x":
                case = "change"
                del dict_users[id]["Изменённая Корзина"][index]
            elif operation == "back":
                case = "show"
                if "Изменённая Корзина" in dict_users[id].keys():
                    del dict_users[id]["Изменённая Корзина"]
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=cart_processing(case=case, user_id=id))
        elif operation == "Изменить":
            if len(dict_users[id]["Изменённая Корзина"]) == 0:
                del dict_users[id]["Изменённая Корзина"]
                del dict_users[id]["Корзина"]
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text="После изменений Ваша корзина пуста\n"
                                           "Вернитесь пожалуйста в Меню",
                                      reply_markup=cart_processing(case="Menu", user_id=id))
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
                                          reply_markup=cart_processing(case="Menu", user_id=id))
                else:
                    del dict_users[id]["Изменённая Корзина"]
                    text = order_info(id, case="current order")
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text=text, reply_markup=cart_processing(case="show", user_id=id))
        elif operation == "accept":
            text = order_info(id, case="current order")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=text, reply_markup=order_accepting(case="confirmation", chat_id=id))
        elif operation == "right":
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          reply_markup=order_accepting(case="Hide", chat_id=id))
            bot.send_message(chat_id=id, text="Как желаете получить заказ?",
                             reply_markup=order_accepting(case="delivery", chat_id=id))

    elif flag == 5:
        rated = ["1_star", "1_star", "3_star", "4_star", "5_star"]
        operation = data[0]
        case, text = "", ""
        if id in dict_users.keys():
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
        if operation == "Cash" or operation == "Card":
            if operation == "Cash":
                operation = "Наличными"
            else:
                operation = "Картой"
            dict_users[id]["Оформление"].update({"Способ Оплаты": operation})
            with con:
                is_phone = con.execute(f'SELECT Телефон FROM Пользователи '
                                       f'WHERE "ID TG" = {id}')
                telephone = is_phone.fetchall()[0][0]
                keyboard = None

            if dict_users[id]["Оформление"]["Способ Доставки"] == "Доставка":
                case, text = "address", "Отправьте своё местоположение\n" + "или укажите адрес в ручную"
                keyboard = order_accepting(case=case, chat_id=id)

            elif dict_users[id]["Оформление"]["Способ Доставки"] == "Самовывоз":
                if telephone is None:
                    case, text = "Hide", "Укажите номер телефона"
                    keyboard = order_accepting(case=case, chat_id=id)
                else:
                    order_to_base(id)
                    text = order_info(id, case="current order")
                    keyboard = None
                    del dict_users[id]["Оформление"], dict_users[id]["Корзина"]

            elif dict_users[id]["Оформление"]["Способ Доставки"] == "В заведении":
                case, text = "Hide", "Укажите номер столика"
                keyboard = order_accepting(case=case, chat_id=id)

            bot.edit_message_text(chat_id=id, message_id=call.message.message_id,
                                  text=text, reply_markup=keyboard)
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
        elif operation == "feedback_order":
            order_number = data[1]
            bot.edit_message_text(chat_id=id, message_id=call.message.message_id,
                                  text="Нам важно ваше мнение\n"
                                       "Вы можете оставить оценку и комментарий к заказу\n"
                                       "Так-же есть возможность оставить оценку и комментарий\n"
                                       "к отдельной позиции заказа",
                                  reply_markup=admin_panel(case="Отзыв", user_id=id, index=order_number))
        elif operation == "feedback_for_order":
            order_number = data[1]
            dict_administrators["Комментарии"].update({id: {order_number: {"Отзыв к заказу": "Заказы"}}})
            bot.edit_message_text(chat_id=id, message_id=call.message.message_id,
                                  text="Оставьте оценку и комментарий к заказу",
                                  reply_markup=admin_panel(case="Оценка заказа", user_id=id, index=order_number))

        elif operation == "feedback_for_position":
            order_number = data[1]
            dict_administrators["Комментарии"].update({id: {order_number: {"Отзыв к позиции": "Позиции"}}})
            bot.edit_message_text(chat_id=id, message_id=call.message.message_id,
                                  text="Выберите позицию",
                                  reply_markup=admin_panel(case="Выбор позиции", user_id=id, index=order_number))
        elif operation == "position":
            print(data)
            order_number = data[1]
            index_in_positions = data[2]
            position = dict_administrators["Комментарии"][id][order_number]["Отзыв к позиции"]["Позиции"][
                index_in_positions]
            dict_administrators["Комментарии"][id][order_number]["Отзыв к позиции"].update(
                {"Выбранная Позиция": position})
            bot.edit_message_text(chat_id=id, message_id=call.message.message_id,
                                  text="Оставьте оценку и комментарий к позиции",
                                  reply_markup=admin_panel(case="Отзыв к позиции",
                                                           user_id=id, index=[order_number, index_in_positions]))
        elif operation == "quit":
            dict_administrators["Комментарии"][id] = {}
            bot.edit_message_text(chat_id=id, message_id=call.message.message_id, text="Спасибо что выбрали нас",
                                  reply_markup=None)

        elif operation in rated:
            rating = data[1]
            order_number = data[2]
            if len(data) > 3:
                index_in_positions = data[3]
            if "Отзыв к заказу" in dict_administrators["Комментарии"][id][order_number].keys():
                dict_administrators["Комментарии"][id][order_number].update({"Отзыв к заказу": {"Оценка": rating}})
            elif "Отзыв к позиции" in dict_administrators["Комментарии"][id][order_number].keys():
                dict_administrators["Комментарии"][id][order_number]["Отзыв к позиции"].update({"Оценка": rating})
            bot.edit_message_text(chat_id=id, message_id=call.message.message_id,
                                  text="Оценка принята, вы можете добавить комментарий")


update(case="Обновить категории")
update(case="Обновить администраторов")
print("Telegram started successfully")
bot.infinity_polling()
