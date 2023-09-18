from vk_api import VkApi
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import gspread, math, json
import sqlite3
import sqlite3 as sl
import requests


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

keyboard = []

menu_keyboard = VkKeyboard(**settings2)
menu_keyboard.add_callback_button(label='Меню', color=VkKeyboardColor.PRIMARY,
                                        payload={"type": "text", "name": "Меню"})
menu_keyboard.add_line()
menu_keyboard.add_callback_button(label='Профиль', color=VkKeyboardColor.PRIMARY,
                                        payload={"type": "text", "name": "Профиль"})
menu_keyboard.add_line()
menu_keyboard.add_callback_button(label='Мои заказы', color=VkKeyboardColor.PRIMARY,
                                        payload={"type": "text", "name": "Мои заказы"})


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
            el.add_callback_button(label='Меню', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "text", "name": "Меню"})
        elif len(keyboard) == 1:
            el.add_callback_button(label='Меню', color=VkKeyboardColor.PRIMARY,
                                    payload={"type": "text", "name": "Меню"})

def menu_section(txt):   #Меню
    global keyboard
    keyboard.clear()
    step = 0
    if txt == "Меню":
        with con:
            data = con.execute("SELECT Название FROM 'Разделы Меню'")
            data = [row[0] for row in data.fetchall()]   #['Холодные закуски', 'Салаты', 'Горячие закуски', 'Хлеб', 'Первые блюда', 'Горячие основные блюда', 'Гарниры', 'Соусы', 'Десерты', 'Фрукты', 'Напитки']
            
        for i in range(math.ceil(len(data) / 5)):
            keyboard.append(VkKeyboard(**settings2))
            print(i)
            for x in data[step:step+5]:
                print(data[step:step+5])
                if x != '':
                    keyboard[i].add_callback_button(label=x, color=VkKeyboardColor.SECONDARY, payload={"type": "text", "name": x})
                    keyboard[i].add_line()
            step += 5
    is_slider(keyboard)    

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
                    key_board = menu_keyboard
                    vk.messages.send(
                        user_id=event.obj.message['from_id'],
                        random_id=get_random_id(),
                        peer_id=event.obj.message['peer_id'],
                        keyboard=key_board.get_keyboard(),
                        message= f'Что вы хотели бы заказать в нашем ресторане сегодня, {user_name}:')
                    
                elif event.obj.message['text'] == "Меню":
                    print(event.obj.message['text'])
                    menu_section(event.obj.message['text'])
                    vk.messages.send(
                        user_id=event.obj.message['from_id'],
                        random_id=get_random_id(),
                        peer_id=event.obj.message['peer_id'],
                        keyboard=keyboard[0].get_keyboard(),
                        message='Выберите раздел меню!')




    elif event.type == VkBotEventType.MESSAGE_EVENT:
        if event.object.payload.get('type') in CALLBACK_TYPES:
            vk.messages.sendMessageEventAnswer(
                        event_id=event.object.event_id,
                        user_id=event.object.user_id,
                        peer_id=event.object.peer_id,                                                   
                        event_data=json.dumps(event.object.payload))
        elif event.object.payload.get('type') in "text":
           
            if event.object.payload.get('name') == 'Меню':
                print(event.object.payload.get('name'))   #Меню
                menu_section(event.object.payload.get('name'))
                last_id = vk.messages.edit(
                    peer_id=event.obj.peer_id,
                    message='Выбирайте',
                    conversation_message_id=event.obj.conversation_message_id,
                    keyboard=keyboard[0].get_keyboard())

        elif event.object.payload.get('type') == "slider":  # инлайн кнопка НАЗАД
                index = event.object.payload.get("index")
                last_id = vk.messages.edit(
                    peer_id=event.obj.peer_id,
                    message='Выбирай категорию',
                    conversation_message_id=event.obj.conversation_message_id,
                    keyboard=keyboard[index].get_keyboard())



if __name__ == '__main__':
    print()