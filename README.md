# 🎵 YouTube to MP3 Telegram Bot

A simple and elegant Telegram bot that converts YouTube videos into MP3 audio files with embedded cover art and metadata.

## ✨ Features
- Download audio from YouTube links
- Automatically clean and format track titles
- Add cover art (thumbnail) and metadata (title, artist, album)
- Send back the MP3 file directly in Telegram
- Temporary file handling with auto-clean option

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/youtube-to-mp3-bot.git
cd youtube-to-mp3-bot
```

### 2. Install dependencies
Make sure you have Python 3.9+ and ffmpeg installed on your system.
Then install the required Python packages:
```bash
pip install -r requirements.txt
```
```requirements.txt``` should contain:
```bash
aiogram==2.25.1
pytube
requests
mutagen
ffmpeg-python
```
