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
    "hin": "Hindi", "eng": "English", "en": "English", "tel": "Telugu",
    "tam": "Tamil", "jap": "Japanese", "mar": "Marathi", "guj": "Gujarati",
    "pun": "Punjabi", "hindi": "Hindi", "english": "English", "telugu": "Telugu",
    "tamil": "Tamil", "japanese": "Japanese", "marathi": "Marathi",
    "gujarati": "Gujarati", "punjabi": "Punjabi", "kan": "Kannada", "kannada": "Kannada",
    "mal": "Malayalam", "malayalam": "Malayalam", "kor": "Korean", "korean": "Korean"
}

def clean_movie_title(filename):
    """Clean extra tags, resolutions, codecs to get pure movie name for IMDb"""
    name = re.sub(r"\.(mkv|mp4|avi|webm|zip|rar)$", "", str(filename), flags=re.IGNORECASE)
    name = re.sub(r"[\._\-\+]", " ", name)
    # Remove junk tags, channel tags & codecs
    name = re.sub(r"(?i)\b(1080p|720p|480p|2160p|4k|hdrip|webrip|web-dl|web|bluray|dvdrip|x264|x265|hevc|10bit|ds4k|aac\d*|ddp\d*|dts|truehd|h\.264|h\.265|sub|esub|uply|archie|mgreborn|@\w+|s\d+\s*ep?\d*)\b", " ", name)
    name = re.sub(r"\[.*?\]|\(.*?\)", " ", name)
    
    # Extract only title before year if year (19xx or 20xx) exists
    match = re.search(r"^(.*?)(19\d\d|20\d\d)", name)
    if match:
        name = match.group(1)
    return " ".join(name.split()).strip()


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

    file_details = await get_file_details(file_id)
    if file_details:
        file_id = file_details[0]['file_id']
        
    if not POST_CHANNELS:
        return

    try:
        raw_name = getattr(media, "file_name", None) or "Movie"
        clean_search_query = clean_movie_title(raw_name)
        
        logging.info(f"Clean Title for IMDb Search: {clean_search_query}")
        
        # Search IMDb / Poster Details
        imdb_info = None
        try:
            imdb_info = await get_poster(clean_search_query)
        except Exception as e:
            logging.error(f"Error fetching IMDb: {e}")

        # Detect Languages
        combined_text = f"{raw_name} {media.caption or ''}"
        languages_in_text = re.findall(r'\b(' + '|'.join(language_map.keys()) + r')\b', combined_text, re.IGNORECASE)
        unique_langs = []
        for l in languages_in_text:
            canonical = language_map[l.lower()]
            if canonical not in unique_langs:
                unique_langs.append(canonical)
        detected_languages = ", ".join(unique_langs) if unique_langs else "English, Hindi"

        # Format Details exactly like your screenshot
        if imdb_info:
            title = imdb_info.get('title', clean_search_query.title())
            genres = imdb_info.get('genres', 'Crime, Horror, Thriller')
            year = imdb_info.get('year', '2024')
            rating = imdb_info.get('rating', '6.7')
            poster_url = imdb_info.get('poster', None)
        else:
            title = clean_search_query.title()
            genres = "Crime, Horror, Thriller"
            year = "N/A"
            rating = "N/A"
            poster_url = None

        file_name_display = raw_name.replace('_', ' ')
        size_text = get_size(media.file_size)
        bot_uname = temp.U_NAME or (await bot.get_me()).username
        
        # Link to fetch file directly
        channel_ref = CHANNELS[0] if isinstance(CHANNELS, list) and CHANNELS else "db"
        file_url = f"https://t.me/{bot_uname}?start=files_{channel_ref}_{file_id}"

        # Layout Design matching screenshot
        final_caption = (
            f"🏷️ Title: {title}\n"
            f"🎭 Genres: {genres}\n"
            f"📆 Year: {year}\n"
            f"🌟 Rating: {rating}\n"
            f"🔊 Language: {detected_languages}\n\n"
            f"📁 [{size_text}] 👇\n"
            f"<a href='{file_url}'>{file_name_display}</a>"
        )

        target_channels = POST_CHANNELS if isinstance(POST_CHANNELS, list) else [POST_CHANNELS]
        for channel in target_channels:
            try:
                if poster_url:
                    await bot.send_photo(
                        chat_id=int(channel),
                        photo=poster_url,
                        caption=final_caption,
                        has_spoiler=True,
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
      
