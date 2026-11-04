import os
import telebot
import sqlite3
from telebot import types
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# ТОКЕН
TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

# --- БАЗА ДАННЫХ ---
conn = sqlite3.connect('rayon.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (user_id INTEGER PRIMARY KEY, score INTEGER)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS problems
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   user_id INTEGER, 
                   text TEXT)''')
conn.commit()

def add_score(user_id, points):
    cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute('INSERT INTO users (user_id, score) VALUES (?, ?)', (user_id, points))
    else:
        new_score = result[0] + points
        cursor.execute('UPDATE users SET score = ? WHERE user_id = ?', (new_score, user_id))
    conn.commit()

def get_score(user_id):
    cursor.execute('SELECT score FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0

# --- ЛОГИКА БОТА ---

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    # ССЫЛКА С НОВОЙ ВЕРСИЕЙ (v=10)
    app_url = "https://kozazaz.github.io/rayon-app/?v=10"
    web_app_info = types.WebAppInfo(url=app_url)
    
    btn1 = types.KeyboardButton('📰 Лента')
    btn2 = types.KeyboardButton('⚠️ Сообщить о проблеме')
    btn3 = types.KeyboardButton('⭐ Мои баллы')
    
    markup.add(btn1, btn2, btn3)
    
    # Обновляем кнопку меню
    bot.set_chat_menu_button(
        chat_id=message.chat.id,
        menu_button=types.MenuButtonWebApp(
            text="Открыть RAYON",
            web_app=web_app_info
        )
    )

    bot.send_message(message.chat.id, 
        f'Привет, {message.from_user.first_name}!\n'
        'Нажми на кнопку ниже, чтобы открыть приложение:', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📰 Лента')
def feed(message):
    bot.send_message(message.chat.id, 'Здесь будет лента объявлений.')

@bot.message_handler(func=lambda message: message.text == '⚠️ Сообщить о проблеме')
def report_problem(message):
    msg = bot.send_message(message.chat.id, 'Опиши проблему:')
    bot.register_next_step_handler(msg, save_problem)

def save_problem(message):
    user_id = message.from_user.id
    problem_text = message.text
    cursor.execute('INSERT INTO problems (user_id, text) VALUES (?, ?)', (user_id, problem_text))
    conn.commit()
    add_score(user_id, 10)
    bot.send_message(message.chat.id, f'✅ Записано: "{problem_text}"\n+10 баллов!')

@bot.message_handler(func=lambda message: message.text == '⭐ Мои баллы')
def my_scores(message):
    user_id = message.from_user.id
    score = get_score(user_id)
    bot.send_message(message.chat.id, f'У тебя {score} баллов.')

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.send_message(message.chat.id, f'[Лента] {message.from_user.first_name}: {message.text}')

# --- СЕРВЕР ДЛЯ САЙТА (заглушка) ---
class WebAppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*') 
        self.end_headers()
        response = {"name": "Сосед", "score": 150}
        self.wfile.write(json.dumps(response).encode())

def run_server():
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, WebAppHandler)
    httpd.serve_forever()

threading.Thread(target=run_server, daemon=True).start()
from server import start_health_server
start_health_server()
print('Бот запущен...')
bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)