import requests
import time
import telebot
import threading
import json
from bs4 import BeautifulSoup

# === Твои данные ===
TELEGRAM_TOKEN = "8307757903:AAH0_9SDxC2ws4S3f_bqlwo9tOpyo3nI0OY"
CHAT_ID = "886731596"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# === Файл для сохранения ===
TRACK_FILE = "tracked.json"

# Загружаем сохранённые товары
try:
    with open(TRACK_FILE, "r", encoding="utf-8") as f:
        tracked_items = json.load(f)
except:
    tracked_items = {}

# === Сохранение списка в файл ===
def save_tracked():
    with open(TRACK_FILE, "w", encoding="utf-8") as f:
        json.dump(tracked_items, f, ensure_ascii=False, indent=2)

# === Функция проверки остатка ===
def check_stock(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        # Название товара
        title_tag = soup.find("h1", {"class": "x-item-title__mainTitle"})
        title = title_tag.get_text(strip=True) if title_tag else "Не удалось найти название"

        # Продавец
        seller_tag = soup.find("span", {"class": "ux-seller-section__item--seller"})
        seller = seller_tag.get_text(strip=True) if seller_tag else "Неизвестный продавец"

        # Количество (обычно "xx available")
        stock_span = soup.find("span", {"class": "qtyTxt"})
        if stock_span:
            stock_text = stock_span.get_text(strip=True)
            stock_number = int("".join(filter(str.isdigit, stock_text)))
        else:
            stock_number = None

        return {"title": title, "seller": seller, "stock": stock_number}

    except Exception as e:
        print("Ошибка:", e)
        return None

# === Мониторинг товаров ===
def monitor():
    while True:
        for url, item_data in tracked_items.items():
            limit = item_data.get("limit", 1)
            data = check_stock(url)
            if data and data["stock"] is not None and data["stock"] <= limit:
                bot.send_message(
                    CHAT_ID,
                    f"⚠️ Остаток товара снизился!\n\n"
                    f"👤 Поставщик: {data['seller']}\n"
                    f"📦 Название: {data['title']}\n"
                    f"📉 Остаток: {data['stock']} шт (лимит {limit})\n"
                    f"🔗 {url}"
                )
        time.sleep(1800)  # проверка каждые 30 мин

# === Команды бота ===
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет 👋 Я бот для отслеживания остатков eBay!\n\n"
        "Команды:\n"
        "/add <url> – добавить товар (лимит ставится автоматически)\n"
        "/remove <url> – удалить товар\n"
        "/list – список отслеживаемых\n"
        "/check <url> – проверить товар вручную\n"
        "/suppliers – показать всех поставщиков\n"
    )

@bot.message_handler(commands=['add'])
def add_item(message):
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.send_message(message.chat.id, "⚠️ Используй формат:\n/add <url>")
            return

        url = parts[1].strip()

        # Получаем данные товара
        data = check_stock(url)
        if data and data["stock"] is not None:
            limit = data["stock"]  # лимит = текущий остаток
            tracked_items[url] = {"limit": limit}
            save_tracked()
            bot.send_message(
                message.chat.id,
                f"✅ Товар добавлен в отслеживание!\n\n"
                f"👤 Поставщик: {data['seller']}\n"
                f"📦 Название: {data['title']}\n"
                f"📉 Текущий остаток: {data['stock']} шт\n"
                f"📊 Лимит уведомления установлен автоматически: {limit}\n"
                f"🔗 {url}"
            )
        else:
            bot.send_message(message.chat.id, "⚠️ Не удалось получить данные о товаре или товар недоступен.")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Ошибка: {e}")

@bot.message_handler(commands=['remove'])
def remove_item(message):
    try:
        url = message.text.split(maxsplit=1)[1].strip()
        if url in tracked_items:
            del tracked_items[url]
            save_tracked()
            bot.send_message(message.chat.id, f"✅ Товар удалён:\n{url}")
        else:
            bot.send_message(message.chat.id, "⚠️ Этот товар не отслеживается.")
    except:
        bot.send_message(message.chat.id, "⚠️ Используй формат:\n/remove <url>")

@bot.message_handler(commands=['list'])
def list_items(message):
    if tracked_items:
        msg = "📋 Отслеживаемые товары:\n"
        for url, item_data in tracked_items.items():
            limit = item_data.get("limit", 1)
            msg += f"- {url} (лимит {limit})\n"
        bot.send_message(message.chat.id, msg)
    else:
        bot.send_message(message.chat.id, "📭 Список пуст.")

@bot.message_handler(commands=['check'])
def check_item(message):
    try:
        url = message.text.split(maxsplit=1)[1].strip()
        data = check_stock(url)
        if data:
            bot.send_message(
                message.chat.id,
                f"🔍 Проверка товара:\n\n"
                f"👤 Поставщик: {data['seller']}\n"
                f"📦 Название: {data['title']}\n"
                f"📉 Остаток: {data['stock'] if data['stock'] else 'Неизвестно'}\n"
                f"🔗 {url}"
            )
        else:
            bot.send_message(message.chat.id, "⚠️ Не удалось проверить товар.")
    except:
        bot.send_message(message.chat.id, "⚠️ Используй формат:\n/check <url>")

@bot.message_handler(commands=['suppliers'])
def suppliers_list(message):
    if tracked_items:
        msg = "📦 Список поставщиков и их товары:\n\n"
        for url, item_data in tracked_items.items():
            limit = item_data.get("limit", 1)
            data = check_stock(url)
            if data:
                msg += (
                    f"👤 Поставщик: {data['seller']}\n"
                    f"📦 Название: {data['title']}\n"
                    f"📉 Остаток: {data['stock'] if data['stock'] else 'Неизвестно'} (лимит {limit})\n"
                    f"🔗 {url}\n\n"
                )
        bot.send_message(message.chat.id, msg)
    else:
        bot.send_message(message.chat.id, "📭 Нет поставщиков в списке.")

# === Запуск мониторинга в отдельном потоке ===
threading.Thread(target=monitor, daemon=True).start()

# === Запуск бота ===
bot.polling(none_stop=True)
