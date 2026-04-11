import telebot
from telebot import types
import time
import requests
from io import BytesIO
import sqlite3
from datetime import datetime
import copy
import threading

bot = telebot.TeleBot("8636956440:AAFpyogfeax6LLw2bmKaVQ9bA8LCfvXTdzM")
ADMIN_IDS = [760217595, 1486385025]  # Список админов

# Настройки оплаты (можно менять)
PAYMENT_SETTINGS = {
    "card_number": "4441114432886206",
    "ukr_card_number": "4441114432886206",  # Украинская карта
    "crypto_bot_link": "http://t.me/send?start=IVYmg0VNAOof",
    "ton_wallet": "UQDZLYLq_FZkjdBSKxKC75xDV_q4j1Jl9yY4SIbg5Rkk6Op_",
    "trc20_wallet": "TRvgVquVHPaddvWRJL7p5z5phM2sLSQqsf",
    "support_username": "Manager_yopa",
    "stars_instruction": "https://telegra.ph/Instrukciya-03-07-17"
}

# Инициализация БД
def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)  # Исправлено check_s_same_thread -> check_same_thread
    c = conn.cursor()
    
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  joined_date TEXT)''')
    
    # Таблица квитанций
    c.execute('''CREATE TABLE IF NOT EXISTS receipts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  tariff_name TEXT,
                  payment_method TEXT,
                  amount REAL,
                  receipt_text TEXT,
                  receipt_photo_id TEXT,
                  date TEXT,
                  status TEXT DEFAULT 'pending')''')  # Добавлен статус
    
    conn.commit()
    conn.close()

init_db()

# Функции для работы с БД
def add_user(user_id, username, first_name):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date) VALUES (?, ?, ?, ?)",
              (user_id, username, first_name, date))
    conn.commit()
    conn.close()

def add_receipt(user_id, tariff_name, payment_method, amount, receipt_text=None, receipt_photo_id=None):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO receipts 
                 (user_id, tariff_name, payment_method, amount, receipt_text, receipt_photo_id, date, status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_id, tariff_name, payment_method, amount, receipt_text, receipt_photo_id, date, 'pending'))
    receipt_id = c.lastrowid
    conn.commit()
    conn.close()
    return receipt_id

def update_receipt_status(receipt_id, status):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("UPDATE receipts SET status = ? WHERE id = ?", (status, receipt_id))
    conn.commit()
    conn.close()

def get_pending_receipts():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT id, user_id, tariff_name, payment_method, amount, date FROM receipts WHERE status = 'pending' ORDER BY date DESC")
    receipts = c.fetchall()
    conn.close()
    return receipts

def get_receipt_by_id(receipt_id):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,))
    receipt = c.fetchone()
    conn.close()
    return receipt

# Функция для рассылки всем юзерам
def broadcast_to_users(text, photo=None):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    count = 0
    for (uid,) in users:
        try:
            if photo:
                bot.send_photo(uid, photo, caption=text)
            else:
                bot.send_message(uid, text)
            count += 1
        except:
            pass
    return count

# Словарь с описаниями и ценами
tariffs_data = {
    0: {
        "name": "☁️🔞Шkoднuцы (Maлышku дo 16 лeT)🔞☁️",
        "price_rub": 650,
        "price_usd": 8.38,
        "price_uah": 363,
        "price_stars": 645,
        "description": """
☁️🔞Шkoднuцы (Maлышku дo 16 лeT)🔞☁️
Цена: 650₽
Продолжительность: Навсегда
Описание: 🦋Что вы получите после оплаты?🦋
 
  🎀Эксклюзuвный контeнт шkoльниц с вo3pаcтoм примepно 6-I6 лeт из личных архивов, весь материал премиум качества! В паке содержится 3ООО+ фoто и 35ОО+ видео контента🎀
 
 ✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️🔞Шkoднuцы (Maлышku дo 16 лeT)🔞☁️
"""
    },
    1: {
        "name": "☁️🪩Впucкu и тycoвкu (Пьяные)🍷☁️",
        "price_rub": 700,
        "price_usd": 9.02,
        "price_uah": 390,
        "price_stars": 700,
        "description": """
☁️🪩Впucкu и тycoвкu (Пьяные)🍷☁️
Цена: 700₽
Продолжительность: Навсегда
Описание: 🦋Что вы получите после оплаты?🦋
 
 🪩Эксклюзuвный контeнт сo впucoк и тycoвок (как дoмашниx в основном, так и в клyбе, на природе и т.д) из первых pyк, такого вы не найдете в интернeте!В папке содержится 33OO+ фoто и 3OOO+ видео кoнтентa - Oтcocaлa в клубе, набyхaлu Maлышky ради cekca🪩
 🔞Возраст: 14-20🔞
 
 ✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️🪩Впucкu и тycoвкu (Пьяные)🍷☁️
"""
    },
    2: {
        "name": "☁️🍓Студeнтки (KpacoTku 16-20 лeт)🍓☁️",
        "price_rub": 750,
        "price_usd": 9.66,
        "price_uah": 418,
        "price_stars": 744,
        "description": """
☁️🍓Студeнтки (KpacoTku 16-20 лeт)🍓☁️
Цена: 750₽
Продолжительность: Навсегда
Описание: 🦋Что вы полyчите после оплаты?🦋
 
 💟Эксклюзuвный вuдeо контeнт студeнток с вo3pаcтoм примepно 15-21 лeт из личных архивов, весь материал премиум качества!💟
В паке содержится 15ОО+ фoто и 25ОО+ вuдeо контeнта - Пoдpoчuлa пpeпoдy за зачёт, oтдaлаcь oдногpyппнuky прямо на паре!🔞
 
✔️Все честно!
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️🍓Студeнтки (KpacoTku 16-20 лeт)🍓☁️
"""
    },
    3: {
        "name": "☁️⛔️И3HOСЫ (без согласия)🕯☁️",
        "price_rub": 850,
        "price_usd": 10.95,
        "price_uah": 474,
        "price_stars": 843,
        "description": """
☁️⛔️И3HOСЫ (без согласия)🕯☁️
Цена: 850₽
Продолжительность: Навсегда
Описание: 🦋Что вы полyчите после оплаты?🦋
 
 😈Эксклюзuвный вuдeо контeнт с uзнosoм из личных архивов, весь материал премиум качества, такого вы не найдете в интернeте!
В паке содержится 35ОО+ фoто и 31ОО+ вuдeо контeнта - Пpuвязaл Maлышky к кpoвaтu, Hakaпал воском на Шkoднuцy😈
 
 ✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️⛔️И3HOСЫ (без согласия)🕯☁️
"""
    },
    4: {
        "name": "☁️🐶aniмal (c животными)🐣☁️",
        "price_rub": 900,
        "price_usd": 11.6,
        "price_uah": 502,
        "price_stars": 893,
        "description": """
☁️🐶aniмal (c животными)🐣☁️
Цена: 900₽
Продолжительность: Навсегда
Описание: 🦋Что вы получите после оплаты?
 
 🔓🐶3ОOO+ фoто и 33OO+ вuдeo эксклюзuвнoго ZOO контeнта (CoБаKu EбyT дeBoчек, Muнет ocлами и многое другое) из первых pyк, такого вы не найдете в интернeте! Максимально редкий контент🐶
 
 ✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️🐶aniмal (c животными)🐣☁️
"""
    },
    5: {
        "name": "☁️👩‍❤‍💋‍👨Иⲏцеsт (ceмейноe)👩‍❤‍💋‍👨☁️",
        "price_rub": 750,
        "price_usd": 9.66,
        "price_uah": 418,
        "price_stars": 744,
        "description": """
☁️👩‍❤‍💋‍👨Иⲏцеsт (ceмейноe)👩‍❤‍💋‍👨☁️
Цена: 750₽
Продолжительность: Навсегда
Описание: 🦋Что вы полyчите после оплаты?🦋
 
  👩‍❤‍💋‍👨Эксклюзuвный вuдeо контeнт с uнцesтом (брат + сестра, отец + дочь и тд) из личных архивов, весь материал премиум качества!👩‍❤‍💋‍👨
 В паке содержится 25ОО+ фoто и 27ОО+ вuдeо контeнта.
 
 ✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️👩‍❤‍💋‍👨Иⲏцеsт (ceмейноe)👩‍❤‍💋‍👨☁️
"""
    },
    6: {
        "name": "☁️🌈GAY P0RN (6-18 лeт)🌈☁️",
        "price_rub": 700,
        "price_usd": 9.02,
        "price_uah": 390,
        "price_stars": 690,
        "description": """
☁️🌈GAY P0RN (6-18 лeт)🌈☁️
Цена: 700₽
Продолжительность: Навсегда
Описание: 🦋Что вы получите после оплаты?🦋
 
📁Категории: М+М, минет, анал, группа.
🌈Около 3000+ фото и видео, которые разбиты на папки для вашего удобства🌈
 
 ✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️🌈GAY P0RN (6-18 лeт)🌈☁️
"""
    },
    7: {
        "name": "☁️👭PEEDмамы И PEEDпапы👬☁️",
        "price_rub": 850,
        "price_usd": 10.95,
        "price_uah": 474,
        "price_stars": 843,
        "description": """
☁️👭PEEDмамы И PEEDпапы👬☁️
Цена: 850₽
Продолжительность: Навсегда
Описание: 🦋Что вы получите после оплаты?🦋
 
 🔥Более 1700+ отборных видео 👭педмамок и педпапок👬
 
 ✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️👭PEEDмамы И PEEDпапы👬☁️
"""
    },
    8: {
        "name": "☁️🩸ПЕPВЫЙ PAЗ (Лишенue мaлышеk)🩸☁️",
        "price_rub": 900,
        "price_usd": 11.6,
        "price_uah": 502,
        "price_stars": 890,
        "description": """
☁️🩸ПЕPВЫЙ PAЗ (Лишенue мaлышеk)🩸☁️
Цена: 900₽
Продолжительность: Навсегда
Описание: 🦋Что вы получите после оплаты?🦋
 
🔓25OO+ фoто и 32OO+ вuдeo эксклюзuвнoго контeнта с пеpвblм paзоm дeвочeк (лишенue) из личных архивов, такого вы не найдете в интернeте!🩸 Редкий контент.
 
 ✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️🩸ПЕPВЫЙ PAЗ (Лишенue мaлышеk)🩸☁️
"""
    },
    9: {
        "name": "☁️🍭M1NET🍌☁️",
        "price_rub": 750,
        "price_usd": 9.66,
        "price_uah": 418,
        "price_stars": 750,
        "description": """
☁️🍭M1NET🍌☁️
Цена: 750₽
Продолжительность: Навсегда
Описание: 🦋Что вы получите после оплаты?🦋

Более 3000+ отборных видео 🍭M1NET0В🍌 и 🔞CUMШ0т0в🔞, возраст 6-16📛 
 
 ✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️🍭M1NET🍌☁️
"""
    },
    10: {
        "name": "☁️✨ЗАКЛАДЧИЦЫ✨☁️",
        "price_rub": 800,
        "price_usd":  10.31,
        "price_uah": 446.83,
        "price_stars": 800,
        "description": """
☁️✨ЗАКЛАДЧИЦЫ✨☁️
Цена: 800₽
Продолжительность: Навсегда
Описание: 🦋Что вы получите после оплаты?🦋
 
🔞КУРЬЕРШИ платят телом за свои долги.🔞 📛Полная распечатка во все щели📛
🩸выeбалu палкой в подъезде🩸
 😈Куколды смотрят и плачат, как их жены платят ртом и жопой ЗА их долги.😈
❗️САМЫЕ ЭКСКЛЮЗИВНЫЕ И ЖЕСТОКИЕ НАКАЗАНИЯ доЛЖНИЦ.❗️
 
 ✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️✨ЗАКЛАДЧИЦЫ✨☁️
"""
    },
    11: {
        "name": "☁️👾DаRкNеT (1-4 kласс)👾☁️",
        "price_rub": 800,
        "price_usd": 10.31,
        "price_uah": 446.83,
        "price_stars": 790,
        "description": """
☁️👾DаRкNеT (1-4 kласс)👾☁️
Цена: 800₽
Продолжительность: Навсегда
Описание: 🦋Что вы получите после оплаты?🦋
 
👾Тариф, в котором вы получаете доступ к ГРОМАДНОМУ эксклюзиву. Эксклюзив наша команда ищет на самом даркнете.👾
☁️Около 5000 фото и видео, которые разбиты на папки для вашего удобства.☁️
 🔞Возраст: 1-4 класс🔞
 
✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️👾DаRкNеT (1-4 kласс)👾☁️
"""
    },
    12: {
        "name": "☁️💎ВСЕ ВКЛЮЧЕНО💎☁️",
        "price_rub": 2500,
        "price_usd": 32.21,
        "price_uah": 1396,
        "price_stars": 2400,
        "description": """
☁️💎ВСЕ ВКЛЮЧЕНО💎☁️
Цена: 2500₽
Продолжительность: Навсегда
Описание: 🦋Что вы получите после оплаты?🦋
 
🔞 Достyп в пpuват «Шkoднuцы» 💦
😈 Достyп в пpuват «ИЗH0C» 😨
🍑 Доступ в пpuват «Bпucкu и туcoвкu» 💟
⛔️ Достyп в пpuват «Инцesт» 🤫
 🩸 Достyп в пpuват «ПEPВЫЙ РАЗ» 🩸
 🍎 Достyп в пpuват «Студeнтки» 👑
 👄 Достyп в пpuват «ДETCKAЯ KOMHATA»🍼
🍭Достyп в пpuват 🍭M1NET🍌
👾Достyп в пpuват DаRкNеT👾
🌈Достyп в пpuват GAY P0RN🌈
 
✔️Все честно!✔️
 🦋Бот автоматически выдаст ссылку после оплаты.🦋

Вы получите приглашение в канал/чат 👇
— ☁️🩸ПЕPВЫЙ PAЗ (Лишенue мaлышеk)🩸☁️
— ☁️✨ЗАКЛАДЧИЦЫ✨☁️
— ☁️🌈GAY P0RN (6-18 лeт)🌈☁️
— ☁️🐶aniмal (c животными)🐣☁️
— ☁️⛔️И3HOСЫ (без согласия)🕯☁️
— ☁️👩‍❤‍💋‍👨Иⲏцеsт (ceмейноe)👩‍❤‍💋‍👨☁️
— ☁️🍬Фут Фетиш🍬☁️
— ☁️🍭M1NET🍌☁️
— ☁️👭PEEDмамы И PEEDпапы👬☁️
— ☁️👾DаRкNеT (1-4 kласс)👾☁️
— ☁️🍓Студeнтки (KpacoTku 16-20 лeт)🍓☁️
— ☁️🔮Тариф MIX🔮☁️
— ☁️🇯🇵Аниме (лоли хентай)🧸☁️
— ☁️🪩Впucкu и тycoвкu (Пьяные)🍷☁️
— ☁️🔞Шkoднuцы (Maлышku дo 16 лeT)🔞☁️
"""
    },
    13: {
        "name": "🥵 EXCLUSIVE 🥵",
        "price_rub": 4500,
        "price_usd": 48,
        "price_uah": 2513,
        "price_stars": 4500,
        "description": """
🥵 EXCLUSIVE 🥵
Цена: 4500₽
Продолжительность: Навсегда
Описание: ЭТО СAМЫЙ КРУТOЙ ПРИВАТ 🔐, Вы получаете абсолютно весь материал который у нас есть. В нём ОТСОРТИРОВАННО всё по полочкам и легко можно найти любую категорию. - Никогда не потеряете доступ к контенту, за счёт резервных копий. - Почти ежедневное пополнение новым конентом. - Контент содержит 320 000 + ВИДЕО. - На запретных ресурсах, подобный товар стоит несколько десятков тысяч, но не у нас. После оплаты, Вы в автоматическом режиме, в этом чате (боте), получите ссылку на закрытый Телеграмм канал, в котором будут ссылки облачного хранилища данного шедевра.

Вы получите приглашение в канал/чат 👇
— 🥵 EXCLUSIVE 🥵
"""
    }
}

categories_list = [
    "☁️🔞Шkоднuцы (Малышku до 16 леT)🔞☁️-650₽",
    "☁️🪩Впucкu и туcoвкu (Пьяные)🍷☁️-700₽",
    "☁️🍓CтудeнTки (КрасоTku 16-20 лет)🍓☁️-750₽",
    "☁️⛔И3НOCЫ (без согласия)🕯☁️-850₽",
    "☁️🐶аniмаl (с животными)🐣☁️-900₽",
    "☁️👩‍❤‍💋‍👨ИHцеsт (семейное)👩‍❤‍💋‍👨☁️-750₽",
    "☁️🌈GАY Р0RN (6-18 лет)🌈 ☁️-700₽",
    "☁️👩‍❤‍👩PEEDмамы И PEEDпапы👨‍❤‍👨☁️-850₽",
    "☁️🩸ПEPВЫЙ PА3 (Лишенue мaлышek)🩸☁️-900₽",
    "☁️🍭М1NЕT🍌☁️-750₽",
    "☁️✨ЗAКЛAДЧИЦЫ✨☁️-800₽",
    "☁️👾DаRkNeТ (1-4 kлаcс)👾☁️-800₽",
    "☁️💎ВCЕ ВKЛЮЧEНО💎☁️-2500₽",
    "🥵EXСLUSIVЕ🥵-4500₽"
]

# Бэкап оригинальных цен для восстановления после скидки
ORIGINAL_TARIFFS_DATA = copy.deepcopy(tariffs_data)
ORIGINAL_CATEGORIES_LIST = copy.deepcopy(categories_list)

# Хранилище состояний пользователей
user_states = {}
admin_reply_states = {}  # Для отслеживания ответов админа
admin_states_data = {}   # Для новых функций админки (рассылка, скидки)
discount_timer = None

# Функции работы со скидками
def remove_discount():
    global tariffs_data, categories_list, discount_timer
    tariffs_data.update(copy.deepcopy(ORIGINAL_TARIFFS_DATA))
    for i in range(len(categories_list)):
        categories_list[i] = ORIGINAL_CATEGORIES_LIST[i]
    discount_timer = None
    notify_admins("⌛ Скидка закончилась, цены возвращены к стандартным.", type('', (), {'first_name':'Система', 'username':'bot', 'id':0}))

def apply_discount_to_all(percent):
    global tariffs_data, categories_list
    factor = (100 - percent) / 100.0
    for k, v in tariffs_data.items():
        orig = ORIGINAL_TARIFFS_DATA[k]
        v['price_rub'] = int(orig['price_rub'] * factor)
        v['price_usd'] = round(orig['price_usd'] * factor, 2)
        v['price_uah'] = int(orig['price_uah'] * factor)
        v['price_stars'] = int(orig['price_stars'] * factor)
        
        # Обновляем текст в описании
        desc = orig['description']
        desc = desc.replace(f"Цена: {orig['price_rub']}₽", f"Цена: {v['price_rub']}₽ (🔥 СКИДКА {percent}%)")
        v['description'] = desc
        
    for i in range(len(categories_list)):
        orig_str = ORIGINAL_CATEGORIES_LIST[i]
        orig_price = ORIGINAL_TARIFFS_DATA[i]['price_rub']
        new_price = tariffs_data[i]['price_rub']
        categories_list[i] = orig_str.replace(f"{orig_price}₽", f"{new_price}₽")

# Функция для отправки уведомлений админам
def notify_admins(action, user, details=""):
    user_info = f"👤 Пользователь: {user.first_name} (@{user.username}) ID: {user.id}"
    message = f"🔔 {action}\n\n{user_info}\n{details}"
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, message)
        except:
            pass

def notify_admins_photo(user, photo, caption=""):
    for admin_id in ADMIN_IDS:
        try:
            bot.send_photo(admin_id, photo, caption=caption)
        except:
            pass

# Команда для админов
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("📋 Ожидающие квитанции", callback_data='admin_pending')
    btn2 = types.InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')
    btn3 = types.InlineKeyboardButton("📢 Рассылка", callback_data='admin_broadcast_btn')
    btn4 = types.InlineKeyboardButton("🎁 Скидки", callback_data='admin_discount_btn')
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    
    bot.send_message(message.chat.id, "🔐 Админ-панель", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ['admin_broadcast_btn', 'admin_discount_btn'])
def admin_extra_menus(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    if call.data == 'admin_broadcast_btn':
        admin_states_data[call.from_user.id] = {'action': 'broadcast'}
        bot.send_message(call.message.chat.id, "📢 Введите текст (или отправьте фото с текстом) для рассылки всем пользователям:")
    elif call.data == 'admin_discount_btn':
        admin_states_data[call.from_user.id] = {'action': 'discount_text'}
        bot.send_message(call.message.chat.id, "🎁 Введите текст сообщения о скидке, который улетит всем пользователям:")

@bot.callback_query_handler(func=lambda call: call.data.startswith('disc_'))
def set_discount_percent(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    percent = int(call.data.split('_')[1])
    if call.from_user.id in admin_states_data and admin_states_data[call.from_user.id].get('action') == 'discount_percent':
        admin_states_data[call.from_user.id]['percent'] = percent
        admin_states_data[call.from_user.id]['action'] = 'discount_duration'
        bot.send_message(call.message.chat.id, f"Выбрана скидка {percent}%.\n\n⏳ Введите на сколько времени добавить скидку (например: 1m, 1h, 1d):")

@bot.callback_query_handler(func=lambda call: call.data == 'admin_pending')
def admin_pending(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipts = get_pending_receipts()
    
    if not receipts:
        bot.send_message(call.message.chat.id, "✅ Нет ожидающих квитанций")
        return
    
    for receipt in receipts:
        receipt_id, user_id, tariff_name, method, amount, date = receipt
        
        # Получаем информацию о пользователе
        try:
            user_info = bot.get_chat(user_id)
            username = f"@{user_info.username}" if user_info.username else "Нет username"
            name = user_info.first_name
        except:
            username = "Неизвестно"
            name = "Неизвестно"
        
        text = f"📝 Квитанция #{receipt_id}\n"
        text += f"👤 Пользователь: {name} ({username})\n"
        text += f"📦 Тариф: {tariff_name}\n"
        text += f"💳 Способ: {method}\n"
        text += f"💰 Сумма: {amount}\n"
        text += f"📅 Дата: {date}\n"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_approve = types.InlineKeyboardButton("✅ Подтвердить", callback_data=f'approve_{receipt_id}')
        btn_reject = types.InlineKeyboardButton("❌ Отклонить", callback_data=f'reject_{receipt_id}')
        btn_reply = types.InlineKeyboardButton("💬 Ответить", callback_data=f'reply_{receipt_id}')
        markup.add(btn_approve, btn_reject)
        markup.add(btn_reply)
        
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_'))
def approve_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipt_id = int(call.data.split('_')[1])
    receipt = get_receipt_by_id(receipt_id)
    
    if receipt:
        user_id = receipt[1]
        update_receipt_status(receipt_id, 'approved')
        
        bot.answer_callback_query(call.id, "✅ Квитанция одобрена")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, f"✅ Квитанция #{receipt_id} одобрена")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def reject_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipt_id = int(call.data.split('_')[1])
    receipt = get_receipt_by_id(receipt_id)
    
    if receipt:
        user_id = receipt[1]
        update_receipt_status(receipt_id, 'rejected')
        
        # Отправляем уведомление пользователю
        try:
            bot.send_message(
                user_id,
                "❌ Ваша квитанция отклонена. Пожалуйста, свяжитесь с поддержкой для уточнения деталей."
            )
        except:
            pass
        
        bot.answer_callback_query(call.id, "❌ Квитанция отклонена")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, f"❌ Квитанция #{receipt_id} отклонена")

@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_'))
def reply_to_receipt(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    receipt_id = int(call.data.split('_')[1])
    receipt = get_receipt_by_id(receipt_id)
    
    if receipt:
        user_id = receipt[1]
        admin_reply_states[call.from_user.id] = {
            'user_id': user_id,
            'receipt_id': receipt_id
        }
        
        bot.send_message(
            call.message.chat.id,
            f"✏️ Введите сообщение для пользователя (квитанция #{receipt_id}):\n"
            f"(просто напишите текст - он отправится без лишних надписей)"
        )
        bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'admin_stats')
def admin_stats(call):
    if call.from_user.id not in ADMIN_IDS:
        return
    
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    
    # Статистика пользователей
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE date(joined_date) = date('now')")
    today_users = c.fetchone()[0]
    
    # Статистика квитанций
    c.execute("SELECT COUNT(*) FROM receipts")
    total_receipts = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM receipts WHERE status = 'pending'")
    pending_receipts = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM receipts WHERE status = 'approved'")
    approved_receipts = c.fetchone()[0]
    
    c.execute("SELECT SUM(amount) FROM receipts WHERE status = 'approved'")
    total_earned = c.fetchone()[0] or 0
    
    conn.close()
    
    text = "📊 Статистика бота:\n\n"
    text += f"👥 Всего пользователей: {total_users}\n"
    text += f"📅 За сегодня: {today_users}\n\n"
    text += f"📝 Всего квитанций: {total_receipts}\n"
    text += f"⏳ Ожидают: {pending_receipts}\n"
    text += f"✅ Подтверждено: {approved_receipts}\n"
    text += f"💰 Заработано: {total_earned:.2f} RUB"
    
    bot.send_message(call.message.chat.id, text)

@bot.message_handler(commands=['start'])
def start(message):
    # Добавляем пользователя в БД
    add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    # Главное меню с кнопками (Reply Keyboard)
    markup_reply = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🦋 Тарuфы 🦋")
    btn2 = types.KeyboardButton("🦋 Моя подnuска 🦋")
    btn3 = types.KeyboardButton("🦋 Доказательства 🦋")
    btn4 = types.KeyboardButton("🦋 Тех.поддержка 🦋")
    markup_reply.add(btn1, btn2, btn3, btn4)
    
    # Чтобы отобразить нижнюю клавиатуру без конфликтов с инлайн кнопками
    bot.send_message(message.chat.id, "Открыто главное меню 👇", reply_markup=markup_reply)
    
    welcome_text = """<b>🔥 Для того чтобы ознакомиться с тарифом, выберите необходимый, нажав на соответствующую кнопку 🔥

🖐️ Добро пожаловать!!

🌀 В нашем боте, в отличие от других, описания тарифов полностью совпадают с их содержанием! 🌀
 
Преимущество нашего бота:

┃☱ ✔️ Имеем большое количество контента разных категорий ☁️
┃☱ ✔️ Цена соответствует качеству контента (без какого либо шлака и плохого качества) 🎩
┃☱ ✔️ Быстрая тех.поддержка ☁️
┃☱ ✔️ Моментальная выдача тøваров
┃☱ ✔️ ПОЛНАЯ анонuмность 🔮
┃☱ ✔️ Самые красивые дeвочku в отличной форме [FULL EXCLUSIVE] 🍓
┃☱ ✔️ Самые низкие цены 💸</b>"""

    # Инлайн клавиатура под фото
    markup_inline = types.InlineKeyboardMarkup(row_width=2)
    in_btn1 = types.InlineKeyboardButton("🦋 Тарuфы 🦋", callback_data='show_categories')
    in_btn2 = types.InlineKeyboardButton("🦋 Моя подnuска 🦋", callback_data='show_sub')
    in_btn3 = types.InlineKeyboardButton("🦋 Доказательства 🦋", callback_data='show_proof')
    in_btn4 = types.InlineKeyboardButton("🦋 Тех.поддержка 🦋", callback_data='show_support')
    markup_inline.add(in_btn1, in_btn2, in_btn3, in_btn4)
    
    photo_url = "https://radika1.link/2026/03/09/1000227939efed780b77f5f16a.jpg"
    
    try:
        bot.send_photo(
            message.chat.id, 
            photo_url, 
            caption=welcome_text, 
            parse_mode='HTML', 
            reply_markup=markup_inline
        )
    except Exception as e:
        # Резервный вариант, если фото не загрузится (ссылка недоступна и т.п.)
        bot.send_message(
            message.chat.id, 
            welcome_text, 
            parse_mode='HTML', 
            reply_markup=markup_inline
        )
    
    # Уведомление админам о новом пользователе
    notify_admins("🚀 Новый пользователь запустил бота", message.from_user)

@bot.message_handler(func=lambda message: message.text == "🦋 Тарuфы 🦋")
def tariffs_menu(message):
    markup = types.InlineKeyboardMarkup()
    btn_buy = types.InlineKeyboardButton("🛍️ Прuoбрестu доctyп", callback_data='show_categories')
    markup.add(btn_buy)
    bot.send_message(message.chat.id, "🦋Чтобы ознакомиться с тарифом, выберите необходимый, нажав на соответствующую кнопку🦋", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🦋 Моя подnuска 🦋")
def my_subscription(message):
    text = "❌ У вас нет активных подписок.\n\nЖелаете приобрести?"
    
    markup = types.InlineKeyboardMarkup()
    btn_buy = types.InlineKeyboardButton("🛍️ Перейти к тарифам", callback_data='show_categories')
    markup.add(btn_buy)
    
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🦋 Доказательства 🦋")
def proof(message):
    try:
        photo_url = "https://radika1.link/2026/03/04/1000227598f0850322b8e7f5ef.jpg"
        response = requests.get(photo_url)
        if response.status_code == 200:
            photo = BytesIO(response.content)
            bot.send_photo(message.chat.id, photo, caption="📸 Наши доказательства качества")
        else:
            bot.send_message(message.chat.id, "❌ Не удалось загрузить фото. Попробуйте позже.")
    except:
        bot.send_message(message.chat.id, "❌ Ошибка загрузки фото.")

@bot.message_handler(func=lambda message: message.text == "🦋 Тех.поддержка 🦋")
def support(message):
    # Уведомление админам
    notify_admins("💬 Пользователь открыл поддержку", message.from_user)
    
    support_text = f"""
<b>💻 Поддержка 💻</b>

👉 <b>Проблемы с тарифом?</b>
👉 <b>Не можете оплатить или не понимаете как?</b>
👉 <b>Хочешь совета от поддержки по поводу тарифа?</b>
👉 <b>Не знаешь как оплатить криптовалютой?</b>

📢 <i>На эти и другие вопросы мы поможем дать краткий и понятный ответ ✍🏻</i>

⚡️ <b>Пиши нам в поддержку - отвечаем сразу ⚡️</b>

🕓 <i>Работаем 24 / 7 🕓</i>

➡ <b>Написать в поддержку:</b> @{PAYMENT_SETTINGS['support_username']}
"""
    
    bot.send_message(message.chat.id, support_text, parse_mode='HTML')

# ====== НОВЫЕ ОБРАБОТЧИКИ ДЛЯ ИНЛАЙН-КНОПОК ИЗ МЕНЮ СТАРТ ======

@bot.callback_query_handler(func=lambda call: call.data == 'show_sub')
def call_my_subscription(call):
    msg = call.message
    msg.from_user = call.from_user
    my_subscription(msg)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'show_proof')
def call_proof(call):
    msg = call.message
    msg.from_user = call.from_user
    proof(msg)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'show_support')
def call_support(call):
    msg = call.message
    msg.from_user = call.from_user
    support(msg)
    bot.answer_callback_query(call.id)

# ===============================================================

@bot.callback_query_handler(func=lambda call: call.data == 'show_categories')
def show_categories(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for i, cat in enumerate(categories_list):
        btn = types.InlineKeyboardButton(cat, callback_data=f'view_{i}')
        markup.add(btn)
    
    # Если это было фото из /start, то редактируем подпись, иначе просто текст
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="🦋Чтобы ознакомиться с тарифом, выберите необходимый, нажав на соответствующую кнопку🦋",
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🦋Чтобы ознакомиться с тарифом, выберите необходимый, нажав на соответствующую кнопку🦋",
                reply_markup=markup
            )
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def view_tariff(call):
    index = int(call.data[5:])
    user_states[call.from_user.id] = {"tariff_index": index}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🇷🇺 Карта РФ", callback_data=f'pay_card_{index}')
    btn2 = types.InlineKeyboardButton("🇺🇦 Карта УКР", callback_data=f'pay_ukr_card_{index}')
    btn3 = types.InlineKeyboardButton("💵 Крипта", callback_data=f'pay_crypto_{index}')
    btn4 = types.InlineKeyboardButton("🤖 CryptoBot", callback_data=f'pay_cryptobot_{index}')
    btn5 = types.InlineKeyboardButton("⭐️ Stars", callback_data=f'pay_stars_{index}')
    btn_back = types.InlineKeyboardButton("🔙 Назад", callback_data='show_categories')
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    markup.add(btn_back)
    
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=tariffs_data[index]["description"],
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=tariffs_data[index]["description"],
                reply_markup=markup
            )
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_card_'))
def pay_card(call):
    index = int(call.data.split('_')[2])
    tariff = tariffs_data[index]
    
    card_number = PAYMENT_SETTINGS['card_number']
    
    text = f"<b>Тариф:</b> {tariff['name']}\n" \
           f"<b>Способ оплаты:</b> 🇷🇺 Оплата картой РФ\n" \
           f"<b>Сумма к оплате:</b> {tariff['price_rub']}₽\n\n" \
           f"<b>Информация об оплате:</b>\n" \
           f"У вас 15 минут на оплату\n\n" \
           f"<code>{card_number}</code>\n" \
           f"(нажмите на номер выше, чтобы скопировать)\n" /
           f"<b>если у вас не проходит оплата, покупайте за звёзды либо крипту</b>"

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("✅ Я оплатил", callback_data=f'paid_{index}_card')
    btn2 = types.InlineKeyboardButton("✖️ Отменить", callback_data='show_categories')
    markup.add(btn1, btn2)
    
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=text,
                reply_markup=markup,
                parse_mode='HTML'
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup,
                parse_mode='HTML'
            )
    except:
        pass
    
    notify_admins(
        "💳 Запрос на оплату картой РФ", 
        call.from_user,
        f"Тариф: {tariff['name']}\nСумма: {tariff['price_rub']}₽"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_ukr_card_'))
def pay_ukr_card(call):
    index = int(call.data.split('_')[3])
    tariff = tariffs_data[index]
    
    ukr_card_number = PAYMENT_SETTINGS['ukr_card_number']
    
    text = f"<b>Тариф:</b> {tariff['name']}\n" \
           f"<b>Способ оплаты:</b> 🇺🇦 Оплата картой УКР\n" \
           f"<b>Сумма к оплате:</b> {tariff['price_uah']}₴\n\n" \
           f"<b>Информация об оплате:</b>\n" \
           f"У вас 15 минут на оплату\n\n" \
           f"<code>{ukr_card_number}</code>\n" \
           f"(нажмите на номер выше, чтобы скопировать)\n\n" \
           f"<b>Банк:</b> OTP Bank"

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("✅ Я оплатил", callback_data=f'paid_{index}_ukr_card')
    btn2 = types.InlineKeyboardButton("✖️ Отменить", callback_data='show_categories')
    markup.add(btn1, btn2)
    
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=text,
                reply_markup=markup,
                parse_mode='HTML'
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup,
                parse_mode='HTML'
            )
    except:
        pass
    
    notify_admins(
        "💳 Запрос на оплату картой УКР", 
        call.from_user,
        f"Тариф: {tariff['name']}\nСумма: {tariff['price_uah']}₴"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_cryptobot_'))
def pay_cryptobot(call):
    index = int(call.data.split('_')[2]) 
    tariff = tariffs_data[index]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_link = types.InlineKeyboardButton("🔗 Перейти в CryptoBot", url=PAYMENT_SETTINGS['crypto_bot_link'])
    btn_paid = types.InlineKeyboardButton("✅ Я оплатил", callback_data=f'paid_{index}_cryptobot')
    btn_cancel = types.InlineKeyboardButton("✖️ Отменить", callback_data='show_categories')
    markup.add(btn_link)
    markup.add(btn_paid, btn_cancel)
    
    text = f"""Тариф: {tariff['name']}
Способ оплаты: 🤖 CryptoBot
Сумма к оплате: {tariff['price_usd']}$

Информация об оплате:
1. Нажмите кнопку "Перейти в CryptoBot"
2. Отправьте {tariff['price_usd']}$ на кошелек бота
3. После оплаты нажмите "Я оплатил"
4. Отправьте скриншот подтверждения"""

    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=text,
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup
            )
    except:
        pass
    
    notify_admins(
        "🤖 Запрос на оплату через CryptoBot", 
        call.from_user,
        f"Тариф: {tariff['name']}\nСумма: {tariff['price_usd']}$"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_crypto_'))
def pay_crypto(call):
    parts = call.data.split('_')
    if len(parts) >= 3:
        index = int(parts[2])
    else:
        index = int(call.data[10:])
    
    tariff = tariffs_data[index]
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_paid = types.InlineKeyboardButton("✅ Я оплатил", callback_data=f'paid_{index}_crypto')
    btn_cancel = types.InlineKeyboardButton("✖️ Отменить", callback_data='show_categories')
    markup.add(btn_paid, btn_cancel)
    
    text = f"""<b>Тариф:</b> {tariff['name']}
<b>Способ оплаты:</b> 💵 Криптовалюта
<b>Сумма к оплате:</b> {tariff['price_usd']}$

<b>Информация об оплате:</b>
Переведите {tariff['price_usd']}$ на один из кошельков:

<b>TON (USDT):</b>
<code>{PAYMENT_SETTINGS['ton_wallet']}</code>

<b>TRC20 (USDT):</b>
<code>{PAYMENT_SETTINGS['trc20_wallet']}</code>

(нажмите на адрес выше, чтобы скопировать)

⚠️ После оплаты нажмите кнопку "✅ Я оплатил" и отправьте скриншот подтверждения"""

    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=text,
                reply_markup=markup,
                parse_mode='HTML'
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup,
                parse_mode='HTML'
            )
    except:
        pass
    
    notify_admins(
        "💵 Запрос на оплату криптовалютой", 
        call.from_user,
        f"Тариф: {tariff['name']}\nСумма: {tariff['price_usd']}$"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_stars_'))
def pay_stars(call):
    index = int(call.data.split('_')[2])
    tariff = tariffs_data[index]
    
    text = f"""Тариф: {tariff['name']}
Способ оплаты: Оплата Telegram Stars 🌟
Сумма к оплате: {tariff['price_stars']}⭐️.
Информация об оплате:
Алгоритм оплаты прост:

🛒 1. Узнайте цену тарифа в звездах, она указана выше
👤 2. Перейдите в профиль @{PAYMENT_SETTINGS['support_username']}
📩 3. Отправьте подарок по стоимости тарифа
✅ 4. Отправьте скриншот оплаты в бота

Не обязательно предупреждать перед оплатой, всё просто, оплатили и получили тариф!

Инструкция : {PAYMENT_SETTINGS['stars_instruction']}"""

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("✅ Я оплатил", callback_data=f'paid_{index}_stars')
    btn2 = types.InlineKeyboardButton("✖️ Отменить", callback_data='show_categories')
    markup.add(btn1, btn2)
    
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=text,
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup
            )
    except:
        pass
    
    notify_admins(
        "⭐️ Запрос на оплату Stars", 
        call.from_user,
        f"Тариф: {tariff['name']}\nСумма: {tariff['price_stars']}⭐️"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def paid(call):
    parts = call.data.split('_')
    index = int(parts[1])
    method = parts[2]
    
    text = """💰 Оплатили?

Отправьте боту квитанцию об оплате: скриншот или фото.
На квитанции должны быть четко видны: дата, время и сумма платежа."""

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_back = types.InlineKeyboardButton("🔙 Назад", callback_data=f'view_{index}')
    btn_cancel = types.InlineKeyboardButton("✖️ Отменить", callback_data='show_categories')
    markup.add(btn_back, btn_cancel)
    
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=text,
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup
            )
    except:
        pass
    
    user_states[call.from_user.id] = {
        "tariff_index": index,
        "payment_method": method,
        "waiting_receipt": True
    }

@bot.message_handler(content_types=['text', 'photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    # Обработка новых функций админа: Рассылка и Скидки
    if user_id in admin_states_data:
        state = admin_states_data[user_id]
        
        if state['action'] == 'broadcast':
            text = message.text or message.caption
            photo = message.photo[-1].file_id if message.content_type == 'photo' else None
            count = broadcast_to_users(text, photo)
            bot.reply_to(message, f"✅ Рассылка успешно отправлена {count} пользователям!")
            del admin_states_data[user_id]
            return
            
        elif state['action'] == 'discount_text':
            state['text'] = message.text or message.caption
            state['photo'] = message.photo[-1].file_id if message.content_type == 'photo' else None
            state['action'] = 'discount_percent'
            
            markup = types.InlineKeyboardMarkup(row_width=4)
            markup.add(
                types.InlineKeyboardButton("10%", callback_data="disc_10"),
                types.InlineKeyboardButton("15%", callback_data="disc_15"),
                types.InlineKeyboardButton("25%", callback_data="disc_25"),
                types.InlineKeyboardButton("50%", callback_data="disc_50")
            )
            bot.send_message(user_id, "Выберите размер скидки:", reply_markup=markup)
            return
            
        elif state['action'] == 'discount_duration':
            dur_str = (message.text or "").strip().lower()
            seconds = 0
            if dur_str.endswith('m'): seconds = int(dur_str[:-1]) * 60
            elif dur_str.endswith('h'): seconds = int(dur_str[:-1]) * 3600
            elif dur_str.endswith('d'): seconds = int(dur_str[:-1]) * 86400
            else:
                bot.send_message(user_id, "❌ Неверный формат! Введите время корректно (например: 1m, 1h, 1d):")
                return
            
            percent = state['percent']
            text = state['text']
            photo = state.get('photo')
            
            # Применяем скидку
            apply_discount_to_all(percent)
            
            # Запускаем таймер на отмену скидки
            global discount_timer
            if discount_timer:
                discount_timer.cancel()
            discount_timer = threading.Timer(seconds, remove_discount)
            discount_timer.start()
            
            # Делаем рассылку
            count = broadcast_to_users(text, photo)
            bot.reply_to(message, f"✅ Скидка {percent}% применена на {dur_str} и рассылка отправлена {count} пользователям!")
            del admin_states_data[user_id]
            return

    # Проверяем, находится ли админ в режиме ответа
    if user_id in admin_reply_states:
        state = admin_reply_states[user_id]
        target_user_id = state['user_id']
        receipt_id = state['receipt_id']
        
        try:
            if message.content_type == 'photo' and message.caption:
                bot.send_photo(target_user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == 'photo':
                bot.send_photo(target_user_id, message.photo[-1].file_id)
            else:
                bot.send_message(target_user_id, message.text)
            
            bot.reply_to(message, f"✅ Сообщение отправлено пользователю (квитанция #{receipt_id})")
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка при отправке: {e}")
        
        del admin_reply_states[user_id]
        return
    
    # Проверяем, ожидает ли пользователь отправки квитанции
    if user_id in user_states and user_states[user_id].get("waiting_receipt"):
        state = user_states[user_id]
        tariff = tariffs_data[state["tariff_index"]]
        method_map = {
            "card": "картой РФ",
            "ukr_card": "картой УКР",
            "crypto": "криптовалютой",
            "cryptobot": "CryptoBot",
            "stars": "Stars"
        }
        method = method_map.get(state["payment_method"], state["payment_method"])
        
        if state["payment_method"] == "card":
            amount = tariff['price_rub']
        elif state["payment_method"] == "ukr_card":
            amount = tariff['price_uah']
        elif state["payment_method"] in ["crypto", "cryptobot"]:
            amount = tariff['price_usd']
        else:
            amount = tariff['price_stars']
        
        if message.content_type == 'photo':
            receipt_id = add_receipt(
                user_id, 
                tariff['name'], 
                method, 
                amount,
                message.caption,
                message.photo[-1].file_id
            )
            
            caption = f"📸 Получена квитанция (фото) #{receipt_id}\n\n👤 Пользователь: {message.from_user.first_name} (@{message.from_user.username}) ID: {user_id}\nТариф: {tariff['name']}\nСпособ оплаты: {method}\nСумма: {amount}"
            notify_admins_photo(message.from_user, message.photo[-1].file_id, caption)
        else:
            receipt_id = add_receipt(
                user_id, 
                tariff['name'], 
                method, 
                amount,
                message.text
            )
            
            notify_admins(
                f"📝 Получена квитанция (текст) #{receipt_id}", 
                message.from_user,
                f"Тариф: {tariff['name']}\nСпособ оплаты: {method}\nСумма: {amount}\n\nТекст: {message.text}"
            )
        
        bot.reply_to(message, "✅ Спасибо! Квитанция отправлена на проверку, вы получите уведомление как только её проверят.")
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn1 = types.KeyboardButton("🦋 Тарuфы 🦋")
        btn2 = types.KeyboardButton("🦋 Моя подnuска 🦋")
        btn3 = types.KeyboardButton("🦋 Доказательства 🦋")
        btn4 = types.KeyboardButton("🦋 Тех.поддержка 🦋")
        markup.add(btn1, btn2, btn3, btn4)
        
        bot.send_message(
            message.chat.id,
            "Выберите действие:",
            reply_markup=markup
        )
        
        del user_states[user_id]

bot.polling()
