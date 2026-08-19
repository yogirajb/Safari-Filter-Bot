# This code has been modified by @Safaridev
# Please do not remove this credit
from pyrogram import Client, filters, enums
from info import CHANNELS, POST_CHANNELS
from database.ia_filterdb import save_file, get_file_details
from utils import get_poster, get_size, temp
import logging
import re
import asyncio

media_filter = filters.document | filters.video | filters.audio

# Memory cache to store recent movie posts for Auto-Merging
# Format: {clean_title: {"msg_ids": {channel_id: msg_id}, "files": [(file_id, name, size)], "header": str, "poster": str}}
ACTIVE_POSTS = {}

language_map = {
    "hin": "Hindi", "eng": "English", "en": "English", "tel": "Telugu",
    "tam": "Tamil", "jap": "Japanese", "mar": "Marathi", "guj": "Gujarati",
    "pun": "Punjabi", "hindi": "Hindi", "english": "English", "telugu": "Telugu",
    "tamil": "Tamil", "japanese": "Japanese", "marathi": "Marathi",
    "gujarati": "Gujarati", "punjabi": "Punjabi", "kan": "Kannada", "kannada": "Kannada",
    "mal": "Malayalam", "malayalam": "Malayalam", "kor": "Korean", "korean": "Korean"
}

def clean_movie_title(filename):
    """Deep cleans junk, telegram hashes, site names and encoders"""
    name = re.sub(r"\.(mkv|mp4|avi|webm|zip|rar)$", "", str(filename), flags=re.IGNORECASE)
    name = re.sub(r"[\._\-\+]", " ", name)
    
    # Remove Telegram bot codes, junk hashes like P4T1787061599, X Pro, etc.
    name = re.sub(r"(?i)\b(p\d+t\d+|x\s*pro|pro|v\d+|ep?\d+)\b", " ", name)
    
    # Remove encoders, channels, quality tags
    name = re.sub(r"(?i)\b(1080p|720p|480p|2160p|4k|hdrip|webrip|web-dl|web|bluray|dvdrip|x264|x265|hevc|10bit|ds4k|aac\d*|ddp\d*|dts|truehd|h\.264|h\.265|sub|esub|uply|archie|mgreborn|@\w+|s\d+\s*ep?\d*)\b", " ", name)
    name = re.sub(r"\[.*?\]|\(.*?\)", " ", name)
    
    # Extract only title before year if year exists
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
        clean_title = clean_movie_title(raw_name)
        
        if not clean_title:
            clean_title = raw_name.split()[0]

        file_name_display = raw_name.replace('_', ' ')
        size_text = get_size(media.file_size)
        bot_uname = temp.U_NAME or (await bot.get_me()).username
        channel_ref = CHANNELS[0] if isinstance(CHANNELS, list) and CHANNELS else "db"
        file_url = f"https://t.me/{bot_uname}?start=files_{channel_ref}_{file_id}"
        
        new_file_entry = (file_url, file_name_display, size_text)

        # Detect Languages
        combined_text = f"{raw_name} {media.caption or ''}"
        languages_in_text = re.findall(r'\b(' + '|'.join(language_map.keys()) + r')\b', combined_text, re.IGNORECASE)
        unique_langs = []
        for l in languages_in_text:
            canonical = language_map[l.lower()]
            if canonical not in unique_langs:
                unique_langs.append(canonical)
        detected_languages = ", ".join(unique_langs) if unique_langs else "English, Hindi"

        target_channels = POST_CHANNELS if isinstance(POST_CHANNELS, list) else [POST_CHANNELS]

        # -------------------------------------------------------------
        # CASE 1: अगर इस मूवी की पोस्ट अभी हाल ही में गई है तो MERGE (EDIT) करें
        # -------------------------------------------------------------
        if clean_title in ACTIVE_POSTS:
            post_data = ACTIVE_POSTS[clean_title]
            
            # Avoid duplicate file link addition
            if not any(f[0] == file_url for f in post_data["files"]):
                post_data["files"].append(new_file_entry)

            # Rebuild full caption with all merged files
            urls_text = "\n\n".join([f"📁 [{size}] 👇\n<a href='{url}'>{name}</a>" for url, name, size in post_data["files"]])
            final_caption = f"{post_data['header']}\n\n{urls_text}"

            for channel_id, msg_id in post_data["msg_ids"].items():
                try:
                    await bot.edit_message_caption(
                        chat_id=int(channel_id),
                        message_id=int(msg_id),
                        caption=final_caption,
                        parse_mode=enums.ParseMode.HTML
                    )
                except Exception as e:
                    logging.error(f"Error merging/editing post in channel {channel_id}: {e}")
            return

        # -------------------------------------------------------------
        # CASE 2: नई मूवी है तो TMDb/IMDb से पोस्टर लाएं और NEW POST भेजें
        # -------------------------------------------------------------
        imdb_info = None
        try:
            imdb_info = await get_poster(clean_title)
        except Exception as e:
            logging.error(f"Error fetching IMDb for {clean_title}: {e}")

        if imdb_info:
            title = imdb_info.get('title', clean_title.title())
            genres = imdb_info.get('genres', 'Drama, Action')
            year = imdb_info.get('year', 'N/A')
            rating = imdb_info.get('rating', 'N/A')
            poster_url = imdb_info.get('poster', None)
        else:
            title = clean_title.title()
            genres = "Drama, Action"
            year = "N/A"
            rating = "N/A"
            poster_url = None

        header_text = (
            f"🏷️ Title: {title}\n"
            f"🎭 Genres: {genres}\n"
            f"📆 Year: {year}\n"
            f"🌟 Rating: {rating}\n"
            f"🔊 Language: {detected_languages}"
        )

        urls_text = f"📁 [{size_text}] 👇\n<a href='{file_url}'>{file_name_display}</a>"
        final_caption = f"{header_text}\n\n{urls_text}"

        sent_msg_ids = {}

        for channel in target_channels:
            try:
                if poster_url:
                    msg = await bot.send_photo(
                        chat_id=int(channel),
                        photo=poster_url,
                        caption=final_caption,
                        has_spoiler=True,
                        parse_mode=enums.ParseMode.HTML
                    )
                else:
                    msg = await bot.send_message(
                        chat_id=int(channel),
                        text=final_caption,
                        parse_mode=enums.ParseMode.HTML,
                        disable_web_page_preview=False
                    )
                sent_msg_ids[str(channel)] = msg.id
            except Exception as e:
                logging.error(f"Error sending new post to {channel}: {e}")

        # Store in cache so upcoming qualities of this movie get merged
        ACTIVE_POSTS[clean_title] = {
            "msg_ids": sent_msg_ids,
            "files": [new_file_entry],
            "header": header_text,
            "poster": poster_url
        }

    except Exception as e:
        logging.error(f"Auto post execution error: {str(e)}")
      
