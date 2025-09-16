import os
import logging
import glob
import requests
import re
from aiogram import Bot, Dispatcher, types, executor
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB
import ffmpeg
import time
import shutil

TOKEN = "TOKEN"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

SRC_DIR = "src"
if not os.path.exists(SRC_DIR):
    os.makedirs(SRC_DIR)

def clean_title(title: str) -> str:
    patterns_to_remove = [
        r'\([^)]*audio[^)]*\)', r'\([^)]*Audio[^)]*\)',
        r'\([^)]*official[^)]*\)', r'\([^)]*Official[^)]*\)',
        r'\([^)]*video[^)]*\)', r'\([^)]*Video[^)]*\)',
        r'\([^)]*from[^)]*\)', r'\([^)]*From[^)]*\)',
        r'\([^)]*movie[^)]*\)', r'\([^)]*Movie[^)]*\)',
        r'\([^)]*lyric[^)]*\)', r'\([^)]*Lyric[^)]*\)',
        r'\([^)]*version[^)]*\)', r'\([^)]*Version[^)]*\)',
        r'\[[^\]]*\]',
    ]
    
    feat_patterns = [r'\(ft\.[^)]*\)', r'\(feat\.[^)]*\)', r'\(featuring[^)]*\)']
    feat_matches = []
    
    for pattern in feat_patterns:
        matches = re.findall(pattern, title, re.IGNORECASE)
        feat_matches.extend(matches)
    
    cleaned_title = title
    for pattern in patterns_to_remove:
        cleaned_title = re.sub(pattern, '', cleaned_title, flags=re.IGNORECASE)
    
    cleaned_title = re.sub(r'\s+', ' ', cleaned_title).strip()
    
    if feat_matches:
        for feat in feat_matches:
            if feat not in cleaned_title:
                cleaned_title += f' {feat}'
    
    return cleaned_title

def download_youtube_audio(url: str, output_path: str) -> dict:
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'writethumbnail': True,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            },
            {
                'key': 'FFmpegMetadata',
            },
        ],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info

def get_thumbnail_path(output_path: str) -> str:
    for file in os.listdir(output_path):
        if file.endswith(('.jpg', '.webp', '.png')):
            return os.path.join(output_path, file)
    return None

def download_thumbnail_from_url(thumbnail_url: str, output_path: str):
    try:
        response = requests.get(thumbnail_url, timeout=10)
        if response.status_code == 200:
            cover_path = os.path.join(output_path, "cover.jpg")
            with open(cover_path, 'wb') as f:
                f.write(response.content)
            return cover_path
    except Exception as e:
        logging.error(f"Thumbnail download error: {e}")
    return None

def add_metadata(mp3_path: str, cover_path: str, info: dict):
    try:
        audio = MP3(mp3_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        
        title = info.get('title', 'Unknown')
        uploader = info.get('uploader', 'Unknown')
        cleaned_title = clean_title(title)
    
        audio.tags.add(TIT2(encoding=3, text=cleaned_title))
        audio.tags.add(TPE1(encoding=3, text=uploader))
        audio.tags.add(TALB(encoding=3, text="Malik's YTMP3"))
        
        if cover_path and os.path.exists(cover_path):
            with open(cover_path, 'rb') as f:
                cover_data = f.read()
            
            mime_type = 'image/jpeg'
            if cover_path.endswith('.png'):
                mime_type = 'image/png'
            elif cover_path.endswith('.webp'):
                mime_type = 'image/webp'
            
            audio.tags.add(APIC(
                encoding=3,
                mime=mime_type,
                type=3,
                desc='Cover',
                data=cover_data
            ))
        
        audio.save()
        return cleaned_title
    except Exception as e:
        logging.error(f"Metadata error: {e}")
        return title

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("🎵 Hey! Send me a YouTube link and I'll convert it to MP3 with cover art!")

@dp.message_handler(commands=['clear'])
async def clear(message: types.Message):
    if message.from_user.username == 'yjamr':
        files = os.listdir("src/")
        for f in files:
            f = f"src/{f}"
            try:
                shutil.rmtree(f)
            except OSError:
                os.remove(f)
        await message.reply("🗑 Files deleted")

@dp.message_handler()
async def handle_message(message: types.Message):
    if 'youtube.com' in message.text or 'youtu.be' in message.text:
        try:
            msg = await message.reply("🔄 Processing...")
            timestamp = str(int(time.time()))
            user_dir = os.path.join(SRC_DIR, f"user_{message.from_user.id}_{timestamp}")
            os.makedirs(user_dir, exist_ok=True)
            
            await msg.edit_text("📥 Downloading audio and cover...")
            info = download_youtube_audio(message.text, user_dir)
            
            mp3_files = [f for f in os.listdir(user_dir) if f.endswith('.mp3')]
            if not mp3_files:
                raise Exception("Failed to download audio")
            
            mp3_path = os.path.join(user_dir, mp3_files[0])
            
            await msg.edit_text("🖼️ Processing cover...")
            cover_path = get_thumbnail_path(user_dir)
            
            if not cover_path:
                thumbnail_url = info.get('thumbnail', '')
                if thumbnail_url:
                    cover_path = download_thumbnail_from_url(thumbnail_url, user_dir)
            
            await msg.edit_text("📝 Adding metadata...")
            cleaned_title = add_metadata(mp3_path, cover_path, info)
            
            await msg.edit_text("📤 Sending file...")
            title = info.get('title', 'Unknown')
            uploader = info.get('uploader', 'Unknown')
    
            with open(mp3_path, 'rb') as audio_file:
                await message.reply_audio(
                    audio_file,
                    title=cleaned_title,
                    performer=uploader,
                    caption=f"🎵 <b>{cleaned_title}</b>\n\n<em><a href='{message.text}'>song.link</a></em>",
                    parse_mode='HTML'
                )

            await msg.delete()
                
        except Exception as e:
            await message.reply(f"❌ Error: {str(e)}")
            logging.error(f"Error: {e}")
    else:
        await message.reply("⚠️ Please send a valid YouTube link")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
