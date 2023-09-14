from vk_api import VkApi
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from fuzzywuzzy import process
import gspread, math, json


GROUP_ID = "ID from json.config"
GROUP_TOKEN = "Token from json.config"
API_VERSION = "Version from config"

vk_session = VkApi(token=GROUP_TOKEN, api_version=API_VERSION)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)
settings = dict(one_time=False, inline=False)
settings2 = dict(one_time=False, inline=True)





for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:

        if event.obj.message['text'] != '':
            if event.from_user:

                if event.obj.message['text'] ==

                elif event.obj.message['text'] ==

    elif event.type == VkBotEventType.MESSAGE_EVENT:





if __name__ == '__main__':
    print()