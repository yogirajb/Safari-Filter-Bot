# This code has been modified by @MzBotz
# Universal Token Stream Parser - Production Stable
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from info import CHANNELS, POST_CHANNELS, AUTO_POST
from database.ia_filterdb import save_file
from utils import get_poster, get_size, temp
from difflib import SequenceMatcher
from datetime import datetime
import logging
import re
import asyncio

media_filter = filters.document | filters.video | filters.audio

ACTIVE_POSTS = {}
MERGE_LOCK = asyncio.Lock()

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
    """
    Universal Parser (Token Stream Boundary Engine):
    Guarantees pure base title, normalized season tag, and exact year.
    Never leaks codecs, quality tags, or episode numbers into titles.
    """
    # 1. Remove extension
    name = re.sub(r"\.(mkv|mp4|avi|webm|zip|rar)$", "", str(filename), flags=re.IGNORECASE)
    
    # 2. Strip leading bracket tags e.g. [@MZ_Botz], [Channel]
    name = re.sub(r"^\s*(\[.*?\]|\(.*?\))\s*", "", name)

    # 3. Extract Year
    year_match = re.search(r"\b(19\d\d|20\d\d)\b", name)
    extracted_year = year_match.group(1) if year_match else None

    # 4. Extract Season & Episode (Rock-Solid Universal Detection)
    s_match = re.search(r"(?i)\b(?:season|s)\s*(\d{1,2})\b", name)
    ep_match = re.search(r"(?i)\b(?:episode|ep|e)\s*(\d{1,3})\b", name)

    season_tag = ""
    cut_positions = [len(name)]

    if s_match:
        s_num = int(s_match.group(1))
        season_tag = f"S{s_num:02d}"
        cut_positions.append(s_match.start())
    elif ep_match:
        season_tag = "S01"
        cut_positions.append(ep_match.start())

    if year_match:
        cut_positions.append(year_match.start())

    # 5. Token Cut Boundary: Quality, Audio, Codecs, OTT Platforms & Tech Tags
    token_boundary = re.search(
        r"(?i)\b(480p|720p|1080p|2160p|4k|hdrip|webrip|web-dl|web|bluray|dvd|camrip|hdcam|"
        r"x264|x265|hevc|10bit|10\s*bit|ds4k|aac\d*|ddp\d*|dd\d*|dts|truehd|sub|esub|esubs|"
        r"kannada|hindi|english|telugu|tamil|malayalam|marathi|gujarati|punjabi|bengali|"
        r"hq|clean|hd|combined|sample|uncut|uply|archie|mgreborn|mkvcinemas|zee5|amzn|dual|audio|org|"
        r"sonyliv|sony|liv|itunes|hotstar|jiocinema|voot|altbalaji|aha|mxplayer|netflix|primevideo|"
        r"hdr10plus|hdr10|hdr|dv|dovi|nf|hs|jhs|v\d+|@\w+|\d+mb|\d+gb|\d+kbps)\b",
        name
    )
    if token_boundary:
        cut_positions.append(token_boundary.start())

    # 6. Hard cut strictly at the first encounter
    first_cut = min(cut_positions)
    main_title = name[:first_cut]

    # 7. Clean punctuation & special chars
    main_title = re.sub(r"[\._\-\+:]", " ", main_title)
    main_title = re.sub(r"[\(\[\{\)\]\}]", " ", main_title)
    clean_title = " ".join(main_title.split()).strip()

    return clean_title, season_tag, extracted_year


def find_similar_key(new_key):
    """Deterministic merge matching - combines all episodes/qualities of the same season"""
    norm_new = re.sub(r"[^a-zA-Z0-9]", "", new_key).lower()
    for existing_key in ACTIVE_POSTS.keys():
        norm_exist = re.sub(r"[^a-zA-Z0-9]", "", existing_key).lower()
        if norm_new == norm_exist:
            return existing_key
        # Fuzzy fallback for minor naming variations
        ratio = SequenceMatcher(None, norm_new, norm_exist).ratio()
        if ratio >= 0.85:
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

    # 1. Save to Database
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

    # 2. Check Auto Post status
    if not AUTO_POST or not POST_CHANNELS:
        return

    try:
        raw_name = getattr(media, "file_name", None) or "Media"
        caption_text = media.caption or ""

        clean_title, season_tag, extracted_year = clean_movie_title(raw_name)
        
        # Fallback for year extraction from Caption if missing in Filename
        if not extracted_year and caption_text:
            cap_year_match = re.search(r"\b(19\d\d|20\d\d)\b", caption_text)
            if cap_year_match:
                extracted_year = cap_year_match.group(1)

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
        combined_text = f"{raw_name} {caption_text}"
        languages_in_text = re.findall(r'\b(' + '|'.join(language_map.keys()) + r')\b', combined_text, re.IGNORECASE)
        unique_langs = []
        for l in languages_in_text:
            canonical = language_map[l.lower()]
            if canonical not in unique_langs:
                unique_langs.append(canonical)
        detected_languages = ", ".join(unique_langs) if unique_langs else "Hindi"

        # Unique Key for Merging (Guarantees all qualities & episodes bundle together)
        current_merge_key = f"{clean_title.lower()}_{season_tag.lower()}_{extracted_year or ''}".strip()
        target_channels = POST_CHANNELS if isinstance(POST_CHANNELS, list) else [POST_CHANNELS]

        async with MERGE_LOCK:
            matched_key = find_similar_key(current_merge_key)

            # -------------------------------------------------------------
            # CASE 1: Merge Mode (Append files to existing Telegram post)
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
            # CASE 2: New Post (First File or New Season)
            # -------------------------------------------------------------
            imdb_info = None
            try:
                imdb_info = await get_poster(clean_title, year=extracted_year, file=raw_name)
            except Exception as e:
                logging.error(f"Error fetching Poster: {e}")

            display_title = f"{clean_title.title()} {season_tag}".strip()
            current_yr = str(datetime.now().year)

            if imdb_info:
                raw_imdb_title = imdb_info.get('title', clean_title.title())
                raw_imdb_title = re.sub(r"[\(\[\{\)\]\}]", "", raw_imdb_title).strip()
                title = f"{raw_imdb_title} {season_tag}".strip() if season_tag else raw_imdb_title
                genres = imdb_info.get('genres', 'Drama, Action')
                year = imdb_info.get('year', extracted_year or current_yr)
                rating = imdb_info.get('rating', 'N/A')
                poster_url = imdb_info.get('poster', None)
            else:
                title = display_title
                genres = "Drama, Series" if season_tag else "Drama, Action"
                year = extracted_year or current_yr
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
  
