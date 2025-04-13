import os
import logging
import yt_dlp
import asyncio

from keep_alive import keep_alive
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
MUSIC_DIR = os.getenv("MUSIC_DIR", "music")
VIDEO_DIR = os.getenv("VIDEO_DIR", "videos")

os.makedirs(MUSIC_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

user_queries = {}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("👋 Привіт! Введи назву пісні або виконавця:")

@dp.message(F.text)
async def handle_query(message: types.Message):
    query = message.text.strip()
    user_id = message.from_user.id

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch50:{query}", download=False)

    if not result or 'entries' not in result or not result['entries']:
        await message.answer("❌ Нічого не знайдено.")
        return

    user_queries[user_id] = {
        "query": query,
        "page": 0,
        "results": result['entries']
    }

    await show_audio_page(message, user_id, edit=False)

async def show_audio_page(message_or_callback, user_id: int, edit: bool = False):
    data = user_queries[user_id]
    page = data["page"]
    results = data["results"]
    start = page * 10
    end = start + 10
    entries = results[start:end]

    if not entries:
        await message_or_callback.answer("❌ Нічого не знайдено на цій сторінці.")
        return

    message_text = f"<i>Ось деякі результати: {data['query']}</i>"
    keyboard = InlineKeyboardBuilder()

    for entry in entries:
        title = entry.get('title', 'Без назви')[:40]
        author = entry.get('uploader', 'Невідомий')
        duration = entry.get('duration')
        duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "?:??"
        video_id = entry.get('id')
        button_text = f"{title} - {author} | {duration_str}"
        keyboard.button(text=button_text, callback_data=f"aud_{video_id}")

    keyboard.adjust(1)
    nav_row = []
    if page > 0:
        nav_row.append(types.InlineKeyboardButton(text="⬅️", callback_data="page_prev"))
    nav_row.append(types.InlineKeyboardButton(text="⏬ Завантажити всі", callback_data="download_all"))
    if end < len(results):
        nav_row.append(types.InlineKeyboardButton(text="➡️", callback_data="page_next"))
    keyboard.row(*nav_row)

    keyboard.row(types.InlineKeyboardButton(
        text="☕ Купити каву автору",
        url="https://send.monobank.ua/jar/7hLa8gjD1Z"
    ))

    if edit and isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(message_text, reply_markup=keyboard.as_markup())
    else:
        await bot.send_message(message_or_callback.chat.id, message_text, reply_markup=keyboard.as_markup())

@dp.callback_query(F.data.startswith("aud_"))
async def download_selected_audio(callback: CallbackQuery):
    video_id = callback.data.replace("aud_", "")
    url = f"https://www.youtube.com/watch?v={video_id}"
    loading_msg = await callback.message.answer("⏳ Завантаження треку...")

    ydl_opts = {
        'format': 'bestaudio/best',
        'ffmpeg_location': '/usr/bin/ffmpeg',  # для Replit
        'outtmpl': os.path.join(MUSIC_DIR, '%(id)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")
        audio_file = FSInputFile(file_path)
        await bot.send_audio(callback.message.chat.id, audio=audio_file, title=info['title'])
    finally:
        await loading_msg.delete()

@dp.callback_query(F.data == "page_next")
async def next_page(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_queries[user_id]["page"] += 1
    await show_audio_page(callback, user_id, edit=True)

@dp.callback_query(F.data == "page_prev")
async def prev_page(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_queries[user_id]["page"] -= 1
    await show_audio_page(callback, user_id, edit=True)

@dp.callback_query(F.data == "download_all")
async def download_all_tracks(callback: CallbackQuery):
    user_id = callback.from_user.id
    entries = user_queries[user_id]["results"]
    page = user_queries[user_id]["page"]
    page_entries = entries[page * 10:(page + 1) * 10]

    await callback.message.answer(f"⬇️ Завантаження {len(page_entries)} треків...")

    for entry in page_entries:
        video_id = entry['id']
        url = f"https://www.youtube.com/watch?v={video_id}"

        ydl_opts = {
            'format': 'bestaudio/best',
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'outtmpl': os.path.join(MUSIC_DIR, '%(id)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'cookies.txt'
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")
        audio_file = FSInputFile(file_path)
        await bot.send_audio(callback.message.chat.id, audio=audio_file, title=info['title'])

if __name__ == "__main__":
    keep_alive()
    asyncio.run(dp.start_polling(bot))
