from vk_api import VkApi, VkUpload
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import gspread, math, json
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

def is_slider(board):
    for el in board:
        if el is keyboard[0] and len(keyboard) != 1:
            el.add_callback_button(label='Далее', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "slider", "index": keyboard.index(el) + 1})
        elif el is not keyboard[0] and el is not keyboard[-1]:
            el.add_callback_button(label='Назад', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "slider", "index": keyboard.index(el) - 1})
            el.add_callback_button(label='Далее', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "slider", "index": keyboard.index(el) + 1})
        elif el is keyboard[-1] and len(keyboard) != 1:
            el.add_callback_button(label='Назад', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "slider", "index": keyboard.index(el) - 1})
            el.add_callback_button(label='На главную', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "text", "name": "На главную"})
        elif len(keyboard) == 1:
            el.add_callback_button(label='Меню', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "text", "name": "Меню"})

def menu_section(txt, user_id):   #Меню
    global keyboard
    keyboard.clear()
    step = 0
    user_lst = []
    if txt == "Меню":
        with con:
            data = con.execute("SELECT Название FROM 'Разделы Меню'")
            data = [row[0] for row in data.fetchall()]   #['Холодные закуски', 'Салаты', 'Горячие закуски', 'Хлеб', 'Первые блюда', 'Горячие основные блюда', 'Гарниры', 'Соусы', 'Десерты', 'Фрукты', 'Напитки']
            
        for i in range(math.ceil(len(data) / 5)):
            keyboard.append(VkKeyboard(**settings2))
            for x in data[step:step+5]:
                if x != '':
                    keyboard[i].add_callback_button(label=x, color=VkKeyboardColor.SECONDARY, payload={"type": "position", "name": x})
                    keyboard[i].add_line()
            step += 5
        user[user_id] = {"position": user_lst}    
        print(user)
    is_slider(keyboard)    
    
    
def products(obj):
    global groups
    lst = []
    step = 0
    groups=[]
    #count = 0
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
       #caption = f"{name}\n{description}\nСтоимость: {cost}"
        lst.append([name, image, description, cost])
    for i in range(math.ceil(len(lst) / 2)):
        groups.append(lst[step:step + 2])  #[[[],[]], [[],[]],...]
        step += 2
    user[obj.user_id].update({"groups": groups})    
    print(groups)  
    print(user)       
    grouping(groups, obj, count =0)  
           
def grouping(data, obj, count):
    print(count)
    #if count < len(data):
    for el in data[count]:
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
                keyboard=button_of_cards(case, count = 0, group_id = count, group_number=data[count].index(el)).get_keyboard())  
        
def button_of_cards(case, count, group_id, group_number):
    data = [case, count, group_id, group_number]   #print(data)   #['Next', 0, 0]
    count = 1
    keyboard = VkKeyboard(**settings2)
    keyboard.add_callback_button(label='<<', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "карточка", "name": "-", "data":data})
    keyboard.add_callback_button(f'{count}', color=VkKeyboardColor.PRIMARY,
                                payload={"type": "карточка", "name": "number"})
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

    

print("Ready")

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:

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
            #print(event.object) #{'user_id': 7995642, 'peer_id': 7995642, 'event_id': 'f4c6337841b8', 'payload': {'type': 'position', 'name': 'Первые блюда'}, 'conversation_message_id': 530}
            products(event.object)
        
        elif event.object.payload.get('type') == "slider":  # инлайн кнопка НАЗАД
            index = event.object.payload.get("index")
            last_id = vk.messages.edit(
                peer_id=event.obj.peer_id,
                message='Выбирай категорию',
                conversation_message_id=event.obj.conversation_message_id,
                keyboard=keyboard[index].get_keyboard())

        elif event.object.payload.get('type') == "карточка":  
            #print(event.object.payload)    #{'type': 'карточка', 'name': 'Следующие', 'data': ['Next', 0, 0]}
            name = event.object.payload.get('name')
            data = event.object.payload.get('data')    # data = case, count, group_id
            case, count, group_id, group_number = data[0], data[1], data[2], data[3]
            if name == '-':
                if count >0:
                    count -=1
                    vk.messages.updateKeyboard(
                            peer_id=event.obj.peer_id,
                            conversation_message_id=event.obj.conversation_message_id,
                            keyboard=button_of_cards(case, count, group_id).get_keyboard()
                        )
            if name == '+':
                count +=1
                vk.messages.updateKeyboard(
                         peer_id=event.obj.peer_id,
                            conversation_message_id=event.obj.conversation_message_id,
                            keyboard=button_of_cards(case, count, group_id).get_keyboard()
                        )     
            if name == 'Следующие': 
                group_id +=1
                case = 0
                grouping(groups, event.object, group_id)
            
            if name =='Добавить':
                name = user[event.object.user_id]["groups"][group_id][group_number][0]
                cost = user[event.object.user_id]["groups"][group_id][group_number][3]
                if 'bag' not in user.keys():
                    user[event.object.user_id].update({'bag':[[name, count, cost]]}) 
                else:
                    user[event.object.user_id]['bag'] += [[name, count, cost]]
                print(user[event.object.user_id])
            if name == 'Корзина':
                if  'bag' not in user[event.object.user_id].keys() or user[event.object.user_id]['bag'] is None:
                    vk.messages.send(
                        user_id=event.obj.user_id,
                        random_id=get_random_id(),
                        peer_id=event.obj.peer_id,
                        message= f'{user_name}, к сожалению корзина пуста. Добавьте позицию!')
                else:
                    print(user[event.object.user_id]['bag'])
                    for x in user[event.object.user_id]['bag']:
                        price = []
                        if len(user[event.object.user_id]['bag']) > 1:
                            price.append 
if __name__ == '__main__':
    print()