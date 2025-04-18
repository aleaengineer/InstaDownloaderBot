import os
import yt_dlp
import requests
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "7945724446:AAHZaiHlRoP0aD1w5y_gdvaIjYyldApmFok"

    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Send me a Instagram link to download the content."
    )

# Function to check if URL is a valid TikTok or Instagram URL
def is_valid_url(url):
    tiktok_pattern = r'https?://(www\.)?(tiktok\.com|vm\.tiktok\.com)/.+'
    instagram_pattern = r'https?://(www\.)?(instagram\.com|instagr\.am)/.+'
    
    return re.match(tiktok_pattern, url) or re.match(instagram_pattern, url)

async def download_from_tiktok(url, status_message):
    # Special handling for TikTok
    try:
        # Convert the URL to mobile format for better compatibility
        if "tiktok.com" in url and not url.startswith("https://vm.tiktok.com"):
            # Try to convert to mobile URL format
            if "/video/" in url:
                video_id = url.split("/video/")[1].split("?")[0]
                url = f"https://vm.tiktok.com/{video_id}/"
        
        # Use requests to get the redirect URL which might contain direct video links
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
        }
        
        await status_message.edit_text("Fetching TikTok video information...")
        
        # Configure yt-dlp with more specific options for TikTok
        ydl_opts = {
            'format': 'mp4/bestvideo+bestaudio/best',
            'outtmpl': 'downloads/tiktok_video_%(id)s.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extractor_retries': 5,
            'extractor_args': {
                'tiktok': {
                    'embed_metadata': '0',
                    'embed_thumbnail': '0',
                    'force_mobile_url': '1'
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.add_default_info_extractors()
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
            
            return video_path if os.path.exists(video_path) else None
            
    except Exception as e:
        print(f"TikTok download error: {str(e)}")
        return None

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    # Check if the message is a valid URL
    if not is_valid_url(url):
        await update.message.reply_text("Please send a valid Instagram URL.")
        return
    
    status_message = await update.message.reply_text("Processing your request...")
    
    try:
        video_path = None
        
        # Special handling for TikTok URLs
        if "tiktok.com" in url or "vm.tiktok.com" in url:
            video_path = await download_from_tiktok(url, status_message)
            
            if not video_path:
                await status_message.edit_text("Could not download this TikTok video. The video might be private or regional restrictions might apply.")
                return
        else:
            # Standard procedure for non-TikTok URLs (Instagram, etc.)
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await status_message.edit_text("Downloading video...")
                info = ydl.extract_info(url, download=True)
                video_path = ydl.prepare_filename(info)
        
        # Check if file exists and is not too large
        if os.path.exists(video_path) and os.path.getsize(video_path) < 50 * 1024 * 1024:  # 50MB limit for Telegram
            # Send the video
            await status_message.edit_text("Uploading to Telegram...")
            with open(video_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption="Here's your video!"
                )
            
            # Clean up
            os.remove(video_path)
            await status_message.delete()
        else:
            if os.path.exists(video_path):
                file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                await status_message.edit_text(f"The video is too large to send via Telegram ({file_size_mb:.2f} MB). Telegram has a 50MB limit.")
                os.remove(video_path)
            else:
                await status_message.edit_text("Could not download the video.")
            
    except Exception as e:
        error_message = str(e)
        await status_message.edit_text(f"Sorry, an error occurred: {error_message}\n\nTry again later or with a different link.")

def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
        
    if not TELEGRAM_TOKEN:
        print("Please set the TELEGRAM_TOKEN environment variable")
        return
        
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
