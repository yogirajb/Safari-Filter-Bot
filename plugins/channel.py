# This code has been modified by @Safaridev
# Please do not remove this credit
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from info import CHANNELS, POST_CHANNELS
from database.ia_filterdb import save_file
from utils import get_poster, get_size, temp
from difflib import SequenceMatcher
import logging
import re
import asyncio

media_filter = filters.document | filters.video | filters.audio

ACTIVE_POSTS = {}
MERGE_LOCK = asyncio.Lock()

# Safe margin below Telegram's 1024 limit
MAX_CAPTION_LENGTH = 1000 

language_map = {
    "hin": "Hindi", "hindi": "Hindi",
    "eng": "English", "english": "English",
    "mar": "Marathi", "marathi": "Marathi",
    "kan": "Kannada", "kannada": "Kannada",
    "tel": "Telugu", "telugu": "Telugu",
    "tam": "Tamil", "tamil": "Tamil",
    "mal": "Malayalam", "malayalam": "Malayalam",
    "guj": "Gujarati", "gujarati": "Gujarati",
    "pun": "Punjabi", "punjabi": "Punjabi",
    "jap": "Japanese", "japanese": "Japanese",
    "kor": "Korean", "korean": "Korean"
}

def clean_movie_title(filename):
    """Accurately extracts clean base title, season tag, and year for auto-merging episodes"""
    name = re.sub(r"\.(mkv|mp4|avi|webm|zip|rar)$", "", str(filename), flags=re.IGNORECASE)
    name = re.sub(r"[\._\-\+]", " ", name)
    
    # 1. Detect Season & Episode (e.g. S01E01, Season 1, S1)
    se_match = re.search(r"(?i)\b(?:s|season\s*)(\d{1,2})\s*(?:e|ep|episode\s*)?(\d{1,3})?\b", name)
    
    season_tag = ""
    cut_pos = len(name)

    if se_match:
        s_num = int(se_match.group(1))
        season_tag = f"S{s_num:02d}"  # Standalone Season tag: S01
        cut_pos = se_match.start()
    else:
        # Check for standalone Year
        year_match = re.search(r"\b(19\d\d|20\d\d)\b", name)
        if year_match:
            cut_pos = min(cut_pos, year_match.start())

    year_match = re.search(r"\b(19\d\d|20\d\d)\b", name)
    year = year_match.group(1) if year_match else None

    main_title = name[:cut_pos]

    junk_patterns = (
        r"(?i)\b(1080p|720p|480p|360p|2160p|4k|hdrip|webrip|web-dl|web|bluray|dvdrip|predvd|dvd|camrip|hdcam|"
        r"x264|x265|hevc|10bit|ds4k|aac\d*|ddp\d*|dts|truehd|h\.264|h\.265|sub|esub|complete|zip|pack|"
        r"kannada|hindi|english|telugu|tamil|malayalam|marathi|gujarati|punjabi|bengali|"
        r"hq|clean|hd|combined|sample|uncut|uply|archie|mgreborn|mkvcinemas|zee5|amzn|dual|audio|p\d+t\d+|x\s*pro|pro|v\d+|@\w+)\b"
    )
    main_title = re.sub(junk_patterns, " ", main_title)
    main_title = re.sub(r"\[.*?\]|\(.*?\)", " ", main_title)
    clean_title = " ".join(main_title.split()).strip()

    return clean_title, season_tag, year


def find_similar_key(new_key):
    """Fuzzy matching to attach episodes to existing season posts"""
    for existing_key in ACTIVE_POSTS.keys():
        if new_key == existing_key:
            return existing_key
        ratio = SequenceMatcher(None, new_key, existing_key).ratio()
        if ratio >= 0.80:
            return existing_key
    return None


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

    try:
        res = save_file(media)
        if asyncio.iscoroutine(res):
            res = await res
        success, file_id = res
    except Exception as e:
        logging.error(f"Error saving to DB: {e}")
        return
    
    if not success or not file_id:
        return

    if not POST_CHANNELS:
        return

    try:
        raw_name = getattr(media, "file_name", None) or "Media"
        clean_title, season_tag, extracted_year = clean_movie_title(raw_name)
        
        if not clean_title:
            clean_title = raw_name.split()[0]

        file_name_display = raw_name.replace('_', ' ')
        if len(file_name_display) > 60:
            file_name_display = file_name_display[:57] + "..."

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
        detected_languages = ", ".join(unique_langs) if unique_langs else "Hindi"

        # Unique Key per Season (Ex: "the dinner s01")
        current_merge_key = f"{clean_title.lower()} {season_tag.lower()}".strip()
        target_channels = POST_CHANNELS if isinstance(POST_CHANNELS, list) else [POST_CHANNELS]

        async with MERGE_LOCK:
            matched_key = find_similar_key(current_merge_key)

            # -------------------------------------------------------------
            # CASE 1: Merge Mode (Episodes merge into this existing post)
            # -------------------------------------------------------------
            if matched_key:
                post_data = ACTIVE_POSTS[matched_key]
                temp_files = list(post_data["files"])
                
                if not any(f[0] == file_url for f in temp_files):
                    temp_files.append(new_file_entry)

                urls_text = "\n\n".join([f"📁 [{size}] ⚡\n<a href='{url}'>{name}</a>" for url, name, size in temp_files])
                final_caption = f"{post_data['header']}\n\n{urls_text}"

                if len(final_caption) <= MAX_CAPTION_LENGTH:
                    post_data["files"] = temp_files
                    for channel_id in post_data["msg_ids"].keys():
                        msg_id = post_data["msg_ids"][channel_id]
                        try:
                            await bot.edit_message_caption(
                                chat_id=int(channel_id),
                                message_id=int(msg_id),
                                caption=final_caption,
                                parse_mode=enums.ParseMode.HTML
                            )
                        except FloodWait as fw:
                            await asyncio.sleep(fw.value)
                            await bot.edit_message_caption(
                                chat_id=int(channel_id),
                                message_id=int(msg_id),
                                caption=final_caption,
                                parse_mode=enums.ParseMode.HTML
                            )
                        except Exception as e:
                            logging.error(f"Error editing post: {e}")
                    return

            # -------------------------------------------------------------
            # CASE 2: New Post (First episode or Movie)
            # -------------------------------------------------------------
            imdb_info = None
            try:
                imdb_info = await get_poster(clean_title)
            except Exception as e:
                logging.error(f"Error fetching Poster: {e}")

            display_title = f"{clean_title.title()} {season_tag}".strip()

            if imdb_info:
                title = imdb_info.get('title', display_title)
                genres = imdb_info.get('genres', 'Drama, Action')
                year = imdb_info.get('year', extracted_year or '2024')
                rating = imdb_info.get('rating', 'N/A')
                poster_url = imdb_info.get('poster', None)
            else:
                title = display_title
                genres = "Drama, Series"
                year = extracted_year or "2024"
                rating = "N/A"
                poster_url = None

            header_text = (
                f"🏷️ Title: {title}\n"
                f"🎭 Genres: {genres}\n"
                f"📆 Year: {year}\n"
                f"🌟 Rating: {rating}\n"
                f"🔊 Language: {detected_languages}"
            )

            urls_text = f"📁 [{size_text}] ⚡\n<a href='{file_url}'>{file_name_display}</a>"
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
                except FloodWait as fw:
                    await asyncio.sleep(fw.value)
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
                            parse_mode=enums.ParseMode.HTML
                        )
                    sent_msg_ids[str(channel)] = msg.id
                except Exception as e:
                    logging.error(f"Error sending post: {e}")

            ACTIVE_POSTS[current_merge_key] = {
                "msg_ids": sent_msg_ids,
                "files": [new_file_entry],
                "header": header_text,
                "poster": poster_url
            }

    except Exception as e:
        logging.error(f"Auto post execution error: {str(e)}")
  
