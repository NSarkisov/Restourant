from vk_api import VkApi, VkUpload
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import math, json
import sqlite3
import sqlite3 as sl
import requests
from PIL import Image
from io import BytesIO


with open('Config.json') as config_file:
    config_data = json.load(config_file)
    GROUP_ID = config_data['vk_token']['group_id']
    GROUP_TOKEN = config_data['vk_token']['group_token']
    API_VERSION = config_data['vk_token']['api_version']
    geocoder_api = config_data["geocoder_api"]
con = sl.connect('restaurant.db', check_same_thread=False)
vk_session = VkApi(token=GROUP_TOKEN, api_version=API_VERSION)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)
settings = dict(one_time=False, inline=False)
settings2 = dict(one_time=False, inline=True)
CALLBACK_TYPES = ('show_snackbar', 'open_link', 'open_app')

groups = []
keyboard = []
user = {}

menu_keyboard = VkKeyboard(**settings2)
menu_keyboard.add_callback_button(label='Меню', color=VkKeyboardColor.PRIMARY,
                                        payload={"type": "text", "name": "Меню"})
menu_keyboard.add_line()
menu_keyboard.add_callback_button(label='Профиль', color=VkKeyboardColor.PRIMARY,
                                        payload={"type": "text", "name": "Профиль"})
menu_keyboard.add_line()
menu_keyboard.add_callback_button(label='Мои заказы', color=VkKeyboardColor.PRIMARY,
                                        payload={"type": "text", "name": "Мои заказы"})

def reply_menu(txt):
    
    reply_keyboard = VkKeyboard(**settings)
    
    if txt == 'Начать':
        reply_keyboard.add_button(label='Меню', color=VkKeyboardColor.PRIMARY, payload={"type": "text"})
        reply_keyboard.add_line()
   
        reply_keyboard.add_button(label='Мои заказы', color=VkKeyboardColor.NEGATIVE, payload={"type": "text"})
        reply_keyboard.add_line()
    reply_keyboard.add_callback_button(label='Мы в Телеграме!', color=VkKeyboardColor.PRIMARY,
                                       payload={"type": "open_link", "link": "https://t.me/SuperRestik_bot"})

    return reply_keyboard

def is_slider(board, case): #case = change или Меню
    for el in board:
        if el is keyboard[0] and len(keyboard) != 1:
            el.add_callback_button(label='Далее', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "slider", "index": keyboard.index(el) + 1, "data" : case})
        elif el is not keyboard[0] and el is not keyboard[-1]:
            el.add_callback_button(label='Назад', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "slider", "index": keyboard.index(el) - 1, "data" : case})
            el.add_callback_button(label='Далее', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "slider", "index": keyboard.index(el) + 1, "data" : case})
        elif el is keyboard[-1] and len(keyboard) != 1:
            el.add_callback_button(label='Назад', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "slider", "index": keyboard.index(el) - 1, "data" : case})
            el.add_callback_button(label='На главную', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "text", "name": "На главную", "data" : case})
        elif len(keyboard) == 1:
            el.add_callback_button(label='Меню', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "text", "name": "Меню", "data" : case})

def menu_section(txt, user_id):   #Меню
    global keyboard
    #keyboard.clear()
    step = 0
    user_lst = []
    if txt == "Меню":
        with con:
            data = con.execute("SELECT Название FROM 'Разделы Меню'")
            data = [row[0] for row in data.fetchall()]   #['Холодные закуски', 'Салаты', 'Горячие закуски', 'Хлеб', 'Первые блюда', 'Горячие основные блюда', 'Гарниры', 'Соусы', 'Десерты', 'Фрукты', 'Напитки']
            user_lst.append(data)
        for i in range(math.ceil(len(data) / 5)):
            keyboard.append(VkKeyboard(**settings2))
            for x in data[step:step+5]:
                if x != '':
                    keyboard[i].add_callback_button(label=x, color=VkKeyboardColor.SECONDARY, payload={"type": "position", "name": x})
                    keyboard[i].add_line()
            step += 5
    if user_id not in user.keys() or user[user_id] is None:
        user[user_id] = {"position": user_lst}  
    else:
        user[user_id]["position"] = user_lst
    is_slider(keyboard, txt)    
    
    
def products(obj):
    global groups
    lst = []
    step = 0
    groups=[]
    name = obj.payload.get("name")
    with con:
        data = con.execute(f'SELECT Имя, Картинка, Описание, Стоимость FROM Позиции '
                           f'INNER JOIN [Разделы Меню] ON Позиции.[ID раздела] = [Разделы Меню]."ID"'
                           f'WHERE [Разделы Меню]."Название" = "{name}"')
    for el in data.fetchall():
        name = el[0]
        image = BytesIO(el[1])
        description = el[2]
        cost = el[3]
        lst.append([name, image, description, cost])
    for i in range(math.ceil(len(lst) / 2)):
        groups.append(lst[step:step + 2])  #[[[],[]], [[],[]],...]
        step += 2
    user[obj.user_id].update({"groups": groups})    
        
    grouping(groups, obj, count =0)  
    
def card_product(el):   #Информация карточки
    name = el[0]
    image = el[1]
    image.seek(0) 
    upload = VkUpload(vk_session)
    photo = upload.photo_messages(photos= image)[0]
    # Получение информации о фото
    photo_id = photo['id']
    owner_id = photo['owner_id']
    access_key = photo['access_key']
    attachment = f'photo{owner_id}_{photo_id}_{access_key}'
    description = el[2]
    cost = el[3]
    caption = f"{name}\n{description}\nСтоимость: {cost}"
    return caption, attachment
         
           
def grouping(data, obj, count):
    for el in data[count]:
        caption, attachment =card_product(el)
        case = 0
        if el == data[count][-1]:   #[[],[]], здесь data[count] это группа из 2 эл
            case= 'Next'
            if count == len(data)-1:  #если count = длинне группы -1 
                case = 'Меню' 
        vk.messages.send(
                peer_id=obj.peer_id,
                random_id=get_random_id(),
                message= caption,
                attachment= attachment,
                conversation_message_id=event.obj.conversation_message_id,
                keyboard=button_of_cards(case, num = 1, group_id = count, group_number=data[count].index(el)).get_keyboard())  


def button_of_cards(case, num, group_id, group_number):
    data = [case, num, group_id, group_number]   #print(data)   #['Next', 0, 0, 0]
    keyboard = VkKeyboard(**settings2)
    keyboard.add_callback_button(label='<<', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "карточка", "name": "-", "data":data})
    keyboard.add_callback_button(f'{num}', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "0"})     
    keyboard.add_callback_button(label='>>', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "карточка", "name": "+", "data":data})
    keyboard.add_line()
    keyboard.add_callback_button(label='Добавить', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "карточка", "name": "Добавить", "data":data})
    keyboard.add_callback_button(label='Корзина', color=VkKeyboardColor.PRIMARY,
                            payload={"type": "карточка", "name": "Корзина", "data":data})
    if case == 'Next':
        keyboard.add_callback_button(label='Следующие', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "карточка", "name": "Следующие",  "data":data })
    if case == 'Меню':
        keyboard.add_callback_button(label='Меню', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "text", "name": "Меню"})
    
    return keyboard

def collect_bag(case, user_id):   
    keyboard1 = VkKeyboard(**settings2)
    if case == 'views':
       
        keyboard1.add_callback_button(label='Изменить', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "корзина", "name": "Изменить"})
        keyboard1.add_callback_button(label='Меню', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "text", "name": "Меню"})
        keyboard1.add_callback_button(label='Оформить заказ', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "корзина", "name": "Оформить заказ"})   
        return keyboard1
    
    global keyboard
    #keyboard.clear()
    if case == 'change':
        if "new_bag" not in user[user_id].keys():
            user[user_id]["new_bag"] = user[user_id]["bag"]
        step = 0
        for i in range(math.ceil(len(user[user_id]["new_bag"]) / 2)):
            keyboard.append(VkKeyboard(**settings2))
            for x in user[user_id]["new_bag"][step:step+2]:
                if x != '':
                    name = x[0]
                    cost = x[1] * x[2]
                    amount = x[1]
                    index = user[user_id]["new_bag"].index(x)
                    keyboard[i].add_callback_button(label='-', color=VkKeyboardColor.PRIMARY,
                            payload={"type": "корзина", "name": "<<", "data":index})
                    keyboard[i].add_callback_button(label=f"{index + 1}: {amount} шт. - {cost} BYN", color=VkKeyboardColor.SECONDARY, payload={"type": "position", "name": x})
                    keyboard[i].add_callback_button(label='+', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "корзина", "name": ">>", "data":index})
                    keyboard[i].add_callback_button(label= 'X', color=VkKeyboardColor.PRIMARY,
                                            payload={"type": "корзина", "name": "del", "data": index})
                    keyboard[i].add_line()
            keyboard[i].add_callback_button(label= 'Корзина', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "корзина", "name": "Назад"})
            step += 2
            
    is_slider(keyboard, 'change')
        
def checkout(case, user_id):
    
    if case == "delivery":
        keyboard = VkKeyboard(**settings2) 
        keyboard.add_callback_button(label='Доставка', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "оформить заказ", "name": "Доставка", 'data':'способ доставки'})
        keyboard.add_callback_button(label='Самовывоз', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "оформить заказ", "name": "Самовывоз", 'data':'способ доставки'})
        keyboard.add_callback_button(label='В заведении', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "оформить заказ", "name": "Заведение", 'data':'способ доставки'})
        return keyboard

    if case == "payment":
        keyboardPayment = VkKeyboard(**settings2)  
        print('payment прилетел')
        keyboardPayment.add_callback_button(label='Карта', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "оформить заказ", "name": "Карта", 'data':'способ оплаты'})
        keyboardPayment.add_callback_button(label='Наличные', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "оформить заказ", "name": "Наличные", 'data':'способ оплаты'})
        return keyboardPayment
    
    if case == "address":
        keyboardAddress = VkKeyboard(**settings2) 
        keyboardAddress.add_callback_button(label='В ручную', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "оформить заказ", "name": "в ручную", 'data':'адрес доставки'})
        keyboardAddress.add_callback_button(label='Геолокация', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "оформить заказ", "name": "гео", 'data':'адрес доставки'})
        return keyboardAddress
    
    if case == 'geo':
        keyboardGeo = VkKeyboard(**settings) 
        keyboardGeo.add_location_button()
        return keyboardGeo
    
    if case == 'confirmation':
        keyboardconfirmation = VkKeyboard(**settings2)     
        keyboardconfirmation.add_callback_button(label='Да', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "оформить заказ", "name": "Да", 'data':'подтверждение'})
        keyboardconfirmation.add_callback_button(label='Нет', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "оформить заказ", "name": "Нет", 'data':'подтверждение'})
        return keyboardconfirmation
    
def save_checklist(user_id):
    with con:
    # Вставка номера телефона в бд
        con.execute('UPDATE OR IGNORE Пользователи SET Телефон = ? WHERE "ID Vk" = ?', [ user_id])
        
def check_info(user_id):
    text = "Ваш заказ:\n"
    num = 1
    result = 0
    for el in user[user_id]['bag']:
        cost = el[1] * el[2]
        text += f"{num}. {el[0]}, кол-во: {el[1]} сумма: {cost} BYN\n"
        num += 1
        result += cost

    if 'checkout' in user[user_id].keys():
        print('hi')
        text += "\n"
        for inf in user[user_id]['checkout'].items():
            text += inf[0] + " : " + inf[1] + "\n"
        text += "\n"
    text += f"Итого: {result} BYN"
    return text
        
print("Ready")

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        if event.obj.message.get('geo'):
            if 'checkout' in user[event.obj.message['from_id']].keys() and user[event.obj.message['from_id']]['checkout'] is not None:
            # Обработка геолокации
                lat = event.obj.message['geo']['coordinates']['latitude']
                long = event.obj.message['geo']['coordinates']['longitude']
                url = f"https://geocode-maps.yandex.ru/1.x/?apikey={geocoder_api}&format=json&geocode={long},{lat}"
                response = requests.get(url).json()
                take_address = ['response', 'GeoObjectCollection', 'featureMember', 0, 'GeoObject', 'metaDataProperty',
                                'GeocoderMetaData', 'Address', 'formatted']
                for x in take_address:
                    response = response[x]
                response = response.split(', ')  # ['Беларусь', 'Минск', 'улица Франциска Скорины', '8к1']
                print(response)
                question = f"Ваш адрес {','.join(response[2:])}?"
                if len(response) == 3:
                    user[event.obj.message['from_id']]['checkout'].update({"Улица": response[2]})
                else:
                    user[event.obj.message['from_id']]['checkout'].update({"Улица": response[2], "Дом": response[3]})
                vk.messages.send(
                        user_id=event.obj.message['from_id'],
                        random_id=get_random_id(),
                        peer_id=event.obj.message['peer_id'],
                        message=question,
                        keyboard = checkout(case = "confirmation", user_id = event.obj.message['from_id']).get_keyboard()) 
                   
        if event.obj.message['text'] != '':
            #записываем информацию о пользовавтеле в БД
            user_id = event.obj.message['from_id']
            user_info = vk.users.get(user_ids=user_id, fields='photo_max_orig')
            user_name = user_info[0]['first_name']
            avatar_url = user_info[0]['photo_max_orig']
            # сохранение информации о пользователе в бд
            with con:
                    con.execute('INSERT OR IGNORE INTO Пользователи ("ID Vk", Имя) VALUES (?, ?)',
                   [user_id, user_name]) 
            # Скачивание аватарки пользователя
            response = requests.get(avatar_url)
            if response.status_code == 200:
                avatar_data = response.content
            # если аватарка есть, добавляем ее в табл    
                with con:
                    con.execute('UPDATE OR IGNORE Пользователи SET Аватарка = ? WHERE "ID Vk" = ?', [sqlite3.Binary(avatar_data), user_id])
            try:
                if event.obj.message['from_id'] in user.keys() and 'checkout' in user[event.obj.message['from_id']].keys():
                    text = ''
                    print(text)
                    if user[event.obj.message['from_id']]['checkout']['Способ доставки'] == "Доставка":
                        if "Улица" not in user[event.obj.message['from_id']]['checkout'].keys():
                            user[event.obj.message['from_id']]['checkout'].update({"Улица": event.obj.message['text']})
                            text = "Укажите номер дома"
                        elif "Дом" not in user[event.obj.message['from_id']]['checkout'].keys():
                            user[event.obj.message['from_id']]['checkout'].update({"Дом": event.obj.message['text']})
                            text = "Укажите номер квартиры"
                        elif "Квартира" not in user[event.obj.message['from_id']]['checkout'].keys():
                            user[event.obj.message['from_id']]['checkout'].update({"Квартира": event.obj.message['text']})
                            text = "Укажите номер Телефона"
                        elif "Телефон" not in user[event.obj.message['from_id']]['checkout'].keys():
                            user[event.obj.message['from_id']]['checkout'].update({"Телефон": event.obj.message['text']})
                          
                            text = check_info(event.obj.message['from_id'])
                    
                    elif user[event.obj.message['from_id']]['checkout']['Способ доставки'] == "Самовывоз":
                        user[event.obj.message['from_id']]['checkout'].update({"Телефон": event.obj.message['text']})
                        text = check_info(event.obj.message['from_id'])
                        print(user[event.obj.message['from_id']]['checkout'])  
                        
                    elif user[event.obj.message['from_id']]['checkout']['Способ доставки'] == "В заведении":
                        if "Место" not in user[event.obj.message['from_id']]['checkout'].keys():
                            user[event.obj.message['from_id']]['checkout'].update({"Место": event.obj.message['text']})
                            text = "Укажите номер телефона"
                        elif "Телефон" not in user[event.obj.message['from_id']]['checkout'].keys():
                            user[event.obj.message['from_id']]['checkout'].update({"Телефон": event.obj.message['text']}) 
                            text = check_info(event.obj.message['from_id'])
                        print(user[event.obj.message['from_id']]['checkout'])      
                    if text != "":
                        vk.messages.send(
                            user_id=event.obj.message['from_id'],
                            random_id=get_random_id(),
                            peer_id=event.obj.message['peer_id'],
                            message=text)
            except:
                pass
                    
            if event.from_user:
                if event.obj.message['text'] == 'Начать':
                    key_board = reply_menu(event.obj.message['text'])
                    vk.messages.send(
                        user_id=event.obj.message['from_id'],
                        random_id=get_random_id(),
                        peer_id=event.obj.message['peer_id'],
                        keyboard=key_board.get_keyboard(),
                        message=f'1. Для заказа нажмите : "Меню"\n' \
                           f'2. Выберите нужный раздел меню, если не нашли на первой странице, нажмите : "далее"\n' \
                           f'3. Затем выберите блюдо и добавьте в корзину.\n' \
                           f'4. Чтобы всегда оставаться на связи, подпишитесь на нас в ' \
                           f'телеграмм канале, нажав кнопку : "Мы в Телеграме"')
                    
                elif event.obj.message['text'] == "Меню":
                    key_board = menu_keyboard
                    vk.messages.send(
                        user_id=event.obj.message['from_id'],
                        random_id=get_random_id(),
                        peer_id=event.obj.message['peer_id'],
                        keyboard=key_board.get_keyboard(),
                        message= f'Что вы хотели бы заказать в нашем ресторане сегодня, {user_name}:')
                elif event.obj.message['text'] == "Мои заказы":
                    pass
                    
                   
    elif event.type == VkBotEventType.MESSAGE_EVENT:
        if event.object.payload.get('type') in CALLBACK_TYPES:
            vk.messages.sendMessageEventAnswer(
                        event_id=event.object.event_id,
                        user_id=event.object.user_id,
                        peer_id=event.object.peer_id,                                                   
                        event_data=json.dumps(event.object.payload))
        elif event.object.payload.get('type') in "text":
           
            if event.object.payload.get('name') == 'Меню':     #Меню
                menu_section(event.object.payload.get('name'), event.object.user_id)  #вызов
                last_id = vk.messages.edit(
                    peer_id=event.obj.peer_id,
                    message=f'Что вы хотели бы заказать в нашем ресторане сегодня, {user_name}:',
                    conversation_message_id=event.obj.conversation_message_id,
                    keyboard=keyboard[0].get_keyboard())
                
            if event.object.payload.get('name') == 'На главную':
                last_id = vk.messages.edit(
                    peer_id=event.obj.peer_id,
                    message=f'Что вы хотели бы заказать в нашем ресторане сегодня, {user_name}:',
                    conversation_message_id=event.obj.conversation_message_id,
                    keyboard = menu_keyboard.get_keyboard())
                
        elif event.object.payload.get('type') in "position": 
            products(event.object)
        
        elif event.object.payload.get('type') == "slider":  # инлайн кнопка НАЗАД
            data = event.object.payload.get("data")
            index = event.object.payload.get("index")
            if data == "Меню":
                last_id = vk.messages.edit(
                    peer_id=event.obj.peer_id,
                    message='Выбирай категорию',
                    conversation_message_id=event.obj.conversation_message_id,
                    keyboard=keyboard[index].get_keyboard())
            if data == 'change':
                text = check_info(event.object.user_id)
                last_id = vk.messages.edit(
                    peer_id=event.obj.peer_id,
                    message=text,
                    conversation_message_id=event.obj.conversation_message_id,
                    keyboard=keyboard[index].get_keyboard())

        elif event.object.payload.get('type') == "карточка":  
            name = event.object.payload.get('name')
            data = event.object.payload.get('data')    # data = case, count, group_id
            case, count, group_id, group_number = data[0], data[1], data[2], data[3]
            if name == '-':
                if count >0:
                    count -=1
                    el = groups[group_id][group_number]
                    caption, attachment =card_product(el)
                    vk.messages.edit(
                        peer_id=event.obj.peer_id,
                        message= caption,
                        attachment = attachment,
                        conversation_message_id=event.obj.conversation_message_id,
                        keyboard=button_of_cards(case, count, group_id, group_number).get_keyboard()
                            )     
            if name == '+':
                count +=1
                el = groups[group_id][group_number]
                caption, attachment =card_product(el)
                vk.messages.edit(
                    peer_id=event.obj.peer_id,
                    message= caption,
                    attachment = attachment,
                    conversation_message_id=event.obj.conversation_message_id,
                    keyboard=button_of_cards(case, count, group_id, group_number).get_keyboard()
                        )     
            if name == 'Следующие': 
                group_id +=1
                case = 0
                grouping(groups, event.object, group_id)
            
            if name =='Добавить':
                updated_count = 1    #после добавления обновляю цифру между -/+
                if updated_count != count:
                    el = groups[group_id][group_number]
                    caption, attachment =card_product(el)
                    vk.messages.edit(
                        peer_id=event.obj.peer_id,
                        message= caption,
                        attachment = attachment,
                        conversation_message_id=event.obj.conversation_message_id,
                        keyboard=button_of_cards(case, updated_count, group_id, group_number).get_keyboard()
                            )     
                name = user[event.object.user_id]["groups"][group_id][group_number][0]
                cost = user[event.object.user_id]["groups"][group_id][group_number][3]
                if 'bag' not in user[event.object.user_id].keys():
                    user[event.object.user_id].update({'bag':[[name, count, cost]]}) 
                else:
                    user[event.object.user_id]['bag'] += [[name, count, cost]]
                vk.messages.send(
                    user_id=event.obj.user_id,
                    random_id=get_random_id(),
                    peer_id=event.obj.peer_id,
                    message= f'Товар, {name}: {count} шт. на сумму: {count * cost} BYN, успешно добавлен в корзину!')
            if name == 'Корзина':
                if  'bag' not in user[event.object.user_id].keys():
                    vk.messages.send(
                        user_id=event.obj.user_id,
                        random_id=get_random_id(),
                        peer_id=event.obj.peer_id,
                        message= f'{user_name}, к сожалению корзина пуста. Добавьте позицию!')
                else:
                    print(user[event.object.user_id]['bag'])
                    text = check_info(event.object.user_id)
                    vk.messages.send(
                            user_id=event.obj.user_id,
                            random_id=get_random_id(),
                            peer_id=event.obj.peer_id,
                            message= text,
                            keyboard = collect_bag(case="views", user_id=event.obj.user_id).get_keyboard())  #, count = 0
        
        elif event.object.payload.get('type') == "корзина":  
            name = event.object.payload.get('name')
            data = event.object.payload.get('data')    
            if name == 'Оформить заказ':
                keyboard = checkout(case = "delivery", user_id=event.obj.user_id)
                vk.messages.send(
                    user_id=event.obj.user_id,
                    random_id=get_random_id(),
                    peer_id=event.obj.peer_id,
                    message= f'Способ получения заказа',
                    keyboard = keyboard.get_keyboard())
            if name == 'Изменить':
                text = check_info(event.object.user_id)
                collect_bag(case="change", user_id=event.obj.user_id)                         
                vk.messages.edit(
                        peer_id=event.obj.peer_id,
                        message= text,
                        conversation_message_id=event.obj.conversation_message_id,
                        keyboard = keyboard[0].get_keyboard())         
            if name == '<<':
                index = data
                amount = user[event.object.user_id]["new_bag"][index][1]
                amount -= 1
                if amount >= 0:
                    user[event.object.user_id]["new_bag"][index][1] = amount
                    text = check_info(event.object.user_id)
                    collect_bag(case="change", user_id=event.obj.user_id)
                    vk.messages.edit(
                    peer_id=event.obj.peer_id,
                    message= f'Количество позиций изменено. \n {text}',
                    conversation_message_id=event.obj.conversation_message_id,
                    keyboard = keyboard[0].get_keyboard())
            if name == '>>':
                index = data
                amount = user[event.object.user_id]["new_bag"][index][1]
                amount += 1
                user[event.object.user_id]["new_bag"][index][1] = amount
                text = check_info(event.object.user_id)
                collect_bag(case="change", user_id=event.obj.user_id)
                vk.messages.edit(
                    peer_id=event.obj.peer_id,
                    message= f'Количество позиций изменено.\n {text}',
                    conversation_message_id=event.obj.conversation_message_id,
                    keyboard = keyboard[0].get_keyboard())    
            if name == "del":
                index = data
                product = user[event.object.user_id]['new_bag'][index][0]
                del user[event.object.user_id]['new_bag'][index]
                text = check_info(event.object.user_id)
                collect_bag(case="change", user_id=event.obj.user_id)
                vk.messages.edit(
                    peer_id=event.obj.peer_id,
                    message= f'Товар, {product}, успешно удален из корзины.\n {text}',
                    conversation_message_id=event.obj.conversation_message_id,
                    keyboard =keyboard[0].get_keyboard())
            if name == "Назад":
                del user[event.object.user_id]['new_bag']
                text = check_info(event.object.user_id)
                vk.messages.edit(
                    peer_id=event.obj.peer_id,
                    message= text,
                    conversation_message_id=event.obj.conversation_message_id,
                    keyboard = collect_bag(case="views", user_id=event.obj.user_id).get_keyboard())
            if name == "change":
                if len(user[event.object.user_id]["new_bag"]) == 0:
                    del user[event.object.user_id]["new_bag"]
                    del user[event.object.user_id]["bag"]
                    vk.messages.edit(
                        peer_id=event.obj.peer_id,
                        message= "Ваша корзина пуста.\n Перейдите в Меню!",
                        conversation_message_id=event.obj.conversation_message_id,
                        keyboard = keyboard[0].get_keyboard())              #!!!!!!!
                else:
                    user[event.object.user_id]["bag"] = user[event.object.user_id]["new_bag"]
                    print(user[event.object.user_id]["bag"])
                    lst = []
                    for el in user[event.object.user_id]["bag"]:
                        if el[2] != 0:
                            lst.append(el)
                    user[event.object.user_id]["bag"] = lst

                    if len(user[event.object.user_id]["bag"]) == 0:
                        del user[event.object.user_id]["bag"], user[event.object.user_id]["new_bag"]
                        vk.messages.edit(
                            peer_id=event.obj.peer_id,
                            message= "Ваша корзина пуста.\n Перейдите в Меню!",
                            conversation_message_id=event.obj.conversation_message_id,
                            keyboard = keyboard[0].get_keyboard()) 
                    else:
                        del user[event.object.user_id]["new_bag"]
                        text = "Выбранные позиции меню:\n"
                        num = 1
                        result = 0
                        for el in user[event.object.user_id]['bag']:
                            cost = el[1]* el[2]
                            text += f"{num}. {el[0]}, кол-во: {el[1]} сумма: {cost} BYN\n"
                            num += 1
                            result += cost
                        text += f"Итого: {result} BYN"
                        vk.messages.edit(
                            peer_id=event.obj.peer_id,
                            message= text,
                            conversation_message_id=event.obj.conversation_message_id,
                            keyboard = collect_bag(case="views", user_id=event.obj.user_id).get_keyboard())
        elif event.object.payload.get('type') == "оформить заказ":   
            name = event.object.payload.get('name') 
            operation = event.object.payload.get('data') 
            case, text = "", ""
            if operation == 'способ доставки':
                if 'checkout' not in user[event.object.user_id].keys():
                    if name == "Доставка":
                        user[event.object.user_id]['checkout'] = {'Способ доставки': "Доставка"}
                            
                    elif name == "Самовывоз":
                        user[event.object.user_id]['checkout'] = {'Способ доставки': "Самовывоз"}
                    
                    elif name == "Заведение":
                        user[event.object.user_id]['checkout'] = {'Способ доставки': "В заведении"} 
                        print(user[event.obj.user_id]['checkout'])     
                    vk.messages.edit(
                            peer_id=event.obj.peer_id,
                            message= "Выберите способ оплаты:",
                            conversation_message_id=event.obj.conversation_message_id,
                            keyboard = checkout(case="payment", user_id = event.object.user_id).get_keyboard()) 
            if operation == 'способ оплаты':   
                if name == "Карта": 
                    user[event.obj.user_id]['checkout'].update({"Способ оплаты": "Карта"})
                    print(user[event.obj.user_id]['checkout'])
                elif name == "Наличные":    
                    user[event.obj.user_id]['checkout'].update({"Способ оплаты": "Наличные"})
                    print(user[event.obj.user_id]['checkout'])
                if user[event.obj.user_id]['checkout']['Способ доставки'] == "Доставка":
                    vk.messages.edit(
                        peer_id=event.obj.peer_id,
                        message= "Отправьте своё местоположение\n или укажите адрес в ручную",
                        conversation_message_id=event.obj.conversation_message_id,
                        keyboard = checkout(case="address", user_id = event.object.user_id).get_keyboard())
                
                elif user[event.obj.user_id]['checkout']['Способ доставки'] == "Самовывоз":
                    vk.messages.edit(
                        peer_id=event.obj.peer_id,
                        message= "Укажите номер телефона",
                        conversation_message_id=event.obj.conversation_message_id)
                elif user[event.obj.user_id]['checkout']['Способ доставки'] == "В заведении":
                    vk.messages.edit(
                        peer_id=event.obj.peer_id,
                        message= "Укажите номер столика",
                        conversation_message_id=event.obj.conversation_message_id)
                    print(user[event.obj.user_id]['checkout'])
            if operation == 'адрес доставки':
                if name == "в ручную":
                    vk.messages.edit(
                        peer_id=event.obj.peer_id,
                        message= "Укажите улицу:",
                        conversation_message_id=event.obj.conversation_message_id)
                if name == "гео":
                    vk.messages.edit(
                        peer_id=event.obj.peer_id,
                        message= "Отправьте геолокацию:",
                        conversation_message_id=event.obj.conversation_message_id,
                        keyboard = checkout(case = 'geo', user_id = event.object.user_id).get_keyboard())    
                if operation == 'подтверждение':
                    if name == "Да":
                        if "Дом" not in user[event.obj.user_id]['checkout'].keys():
                            vk.messages.edit(
                                peer_id=event.obj.peer_id,
                                message= "Укажите номер дома:",
                                conversation_message_id=event.obj.conversation_message_id)
                        else:
                            vk.messages.edit(
                            peer_id=event.obj.peer_id,
                            message= "Укажите номер квартитры:",
                            conversation_message_id=event.obj.conversation_message_id)
                     
                           

            
              
                  

                
               
                            
if __name__ == '__main__':
    print()