import requests
import telebot
import time
import threading
from telebot import types
from decouple import config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TELEGRAM_TOKEN = config('TELEGRAM_TOKEN')
CHAT_ID = config('CHAT_ID')
SERVERS_STRING = config('SERVERS')
CHECK_INTERVAL = 60

def parse_servers(servers_string):
    servers = {}
    entries = servers_string.split(';')
    for entry in entries:
        name, url, status = entry.split(',')
        servers[name] = [url, status.strip().lower() == 'true']
    return servers

SERVERS = parse_servers(SERVERS_STRING)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

def send_notification(message, photo_path='log.jpg'):
    logging.info(f"Отправка уведомления: {message}")
    if photo_path:
        with open(photo_path, 'rb') as photo:
            bot.send_photo(CHAT_ID, photo=photo, caption=message)
    else:
        bot.send_message(CHAT_ID, message)

def check_servers():
    while True:
        for name, (url, status) in SERVERS.items():
            logging.info(f"Проверка сервера: {name} ({url})")
            if not status:
                logging.info(f"Сервер {name} отключен для мониторинга.")
                continue
            try:
                response = requests.get(url, timeout=10)
                logging.info(f"Сервер {name} доступен. Код ответа: {response.status_code}")
                current_status = True
            except requests.RequestException as e:
                logging.error(f"Ошибка подключения к серверу {name}: {e}")
                if status:
                    send_notification(f"Сервер {name} ({url}) не отвечает. Статус: Не доступен")
                    SERVERS[name][1] = False
                continue
            
            if not status and current_status:
                SERVERS[name][1] = True
                send_notification(f"Сервер {name} ({url}) снова в рабочем состоянии.")
        
        time.sleep(CHECK_INTERVAL)

@bot.message_handler(commands=['start'])
def start(message):
    logging.info("Команда /start получена")
    bot.reply_to(message, 'Бот запущен. Используйте команду /status для получения статуса серверов.')

@bot.message_handler(commands=['help'])
def helper(message, photo_path='help.jpg'):
    logging.info("Команда /help получена")
    if photo_path:
        with open(photo_path, 'rb') as photo:
            bot.send_photo(message.chat.id, photo=photo, caption='the skibidi rizzler sigma')
    else:
        bot.send_message(message.chat.id, message)

@bot.message_handler(commands=['status'])
def status(message):
    logging.info("Команда /status получена")
    keyboard = types.InlineKeyboardMarkup()
    message_text = "Статус серверов:\n"
    for name, (url, status) in SERVERS.items():
        status_text = "Работает ✅" if status else "Не работает ❌"
        message_text += f"{name}: {status_text}\n"
        button = types.InlineKeyboardButton(f"{name}", callback_data=name)
        keyboard.add(button)
    
    bot.send_message(message.chat.id, message_text, reply_markup=keyboard)

def update_status(call):
    server_name = call.data
    logging.info(f"Обновление статуса сервера: {server_name}")
    if server_name in SERVERS:
        current_status = SERVERS[server_name][1]
        new_status = not current_status
        SERVERS[server_name][1] = new_status
        status_text = "Работает ✅" if new_status else "Не работает ❌"
        bot.edit_message_text(
            text=f"Статус сервера {server_name} обновлён на {status_text}.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        if not new_status:
            send_notification(f"Сервер {server_name} ({SERVERS[server_name][0]}) был вручную помечен как не рабочий.")
        else:
            send_notification(f"Сервер {server_name} ({SERVERS[server_name][0]}) был вручную помечен как рабочий.")

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    logging.info(f"Получен callback_query: {call.data}")
    update_status(call)

threading.Thread(target=check_servers, daemon=True).start()

bot.set_my_commands([
    telebot.types.BotCommand("/start", 'Instructions'),
    telebot.types.BotCommand("/status", 'Status of servers'),
    telebot.types.BotCommand("/help", 'Helpful Help')
])
bot.polling(none_stop=True)
