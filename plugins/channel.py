# This code has been modified by @Safaridev
# Please do not remove this credit
from pyrogram import Client, filters, enums
from info import CHANNELS, POST_CHANNELS
from database.ia_filterdb import save_file, get_file_details
from utils import get_poster, get_size, temp
import logging
import re

media_filter = filters.document | filters.video | filters.audio

language_map = {
    "hin": "Hindi",
    "eng": "English",
    "en": "English",
    "tel": "Telugu",
    "tam": "Tamil",
    "jap": "Japanese",
    "mar": "Marathi",
    "guj": "Gujarati",
    "pun": "Punjabi",
    "hindi": "Hindi",
    "english": "English",
    "telugu": "Telugu",
    "tamil": "Tamil",
    "japanese": "Japanese",
    "marathi": "Marathi",
    "gujarati": "Gujarati",
    "punjabi": "Punjabi"
}

@Client.on_message(filters.chat(CHANNELS) & media_filter)
async def media(bot, message):
    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)
        if media is not None:
            break
    else:
        return

    media.file_type = file_type
    media.caption = message.caption
    success, file_id = await save_file(media)
    
    if not success or not file_id:
        return

    # Fetch file ID details if required
    file_details = await get_file_details(file_id)
    if file_details:
        file_id = file_details[0]['file_id']
        
    # --- Auto Post Logic (Direct Trigger) ---
    if not POST_CHANNELS:
        return

    try:
        raw_caption = media.caption or media.file_name or ""
        clean_movie_name = re.sub(r"\[.*?\]|\(.*?\)|\.mkv|\.mp4|\.avi|\.webm", "", raw_caption.split('|')[0]).strip()
        
        # Search IMDb / Poster
        imdb_info = None
        try:
            imdb_info = await get_poster(clean_movie_name)
        except Exception as e:
            logging.error(f"Error fetching IMDb: {e}")

        # Detect Languages from caption/file_name
        languages_in_text = re.findall(r'\b(' + '|'.join(language_map.keys()) + r')\b', raw_caption, re.IGNORECASE)
        detected_languages = ", ".join(set(language_map[lang.lower()] for lang in languages_in_text if lang.lower() in language_map)) or "Hindi, English"

        # Format Details
        if imdb_info:
            title = imdb_info.get('title', clean_movie_name)
            rating = imdb_info.get('rating', 'N/A')
            genre = imdb_info.get('genres', 'Crime, Horror, Thriller')
            poster_url = imdb_info.get('poster', None)
            year = imdb_info.get('year', 'N/A')
        else:
            title = clean_movie_name
            rating = "N/A"
            genre = "Crime, Horror, Thriller"
            poster_url = None
            year = "N/A"

        file_name_display = media.file_name.replace('_', ' ')
        size_text = get_size(media.file_size)
        bot_uname = temp.U_NAME or (await bot.get_me()).username
        
        # Link Format matching your bot's temp start logic
        channel_ref = CHANNELS[0] if isinstance(CHANNELS, list) and CHANNELS else "db"
        file_url = f"https://t.me/{bot_uname}?start=files_{channel_ref}_{file_id}"

        urls_text = f"📁 [{size_text}]👇\n<a href='{file_url}'>{file_name_display}</a>"
        final_caption = (
            f"<b>🏷 Title: {title}\n"
            f"🎭 Genres: {genre}\n"
            f"📆 Year: {year}\n"
            f"🌟 Rating: {rating}\n"
            f"🔊 Language: {detected_languages}\n\n"
            f"{urls_text}</b>"
        )

        target_channels = POST_CHANNELS if isinstance(POST_CHANNELS, list) else [POST_CHANNELS]
        for channel in target_channels:
            try:
                if poster_url:
                    await bot.send_photo(
                        chat_id=int(channel),
                        photo=poster_url,
                        caption=final_caption,
                        parse_mode=enums.ParseMode.HTML
                    )
                else:
                    await bot.send_message(
                        chat_id=int(channel),
                        text=final_caption,
                        parse_mode=enums.ParseMode.HTML,
                        disable_web_page_preview=False
                    )
            except Exception as e:
                logging.error(f"Error sending auto post to channel {channel}: {str(e)}")

    except Exception as e:
        logging.error(f"Auto post execution error: {str(e)}")
