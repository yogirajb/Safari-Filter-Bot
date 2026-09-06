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
    "kor": "Korean", "korean": "Korean", 
    "ben": "Bengali", "bengali": "Bengali", 
    "chi": "Chinese", "chinese": "Chinese"
}

def clean_movie_title(filename):
    """
    Universal Title Parser:
    - Strips leading channel usernames, branding & bracket tags
    - Converts dots/underscores to spaces
    - Detects Season, Episode, Year, Quality
    """
    name = re.sub(r"\.(mkv|mp4|avi|webm|zip|rar)$", "", str(filename), flags=re.IGNORECASE)
    name = re.sub(r"^\s*(\[.*?\]|\(.*?\))\s*", "", name)
    name = re.sub(r"(?i)^\s*@\w+(\s+(movies|cinema|films|series|hub|channel|official|off|tv|network|media))?\s*", "", name)
    name = re.sub(r"[\._\-\+:]", " ", name)
    name = " ".join(name.split()).strip()

    year_match = re.search(r"\b(19\d\d|20\d\d)\b", name)
    extracted_year = year_match.group(1) if year_match else None

    se_comb_match = re.search(r"(?i)\bS(\d{1,2})\s*(?:E|EP)\s*\d{1,4}\b", name)
    s_match = re.search(r"(?i)\b(?:season\s*(\d{1,2})|S(\d{1,2}))\b", name)
    ep_match = re.search(r"(?i)\b(?:episode|ep)\s*(\d{1,4})\b|\bE(\d{1,4})\b", name)

    season_tag = ""
    cut_positions = [len(name)]

    if se_comb_match:
        s_num = int(se_comb_match.group(1))
        season_tag = f"S{s_num:02d}"
        cut_positions.append(se_comb_match.start())
    elif s_match:
        s_num = int(s_match.group(1) or s_match.group(2))
        season_tag = f"S{s_num:02d}"
        cut_positions.append(s_match.start())
    elif ep_match:
        season_tag = "S01"
        cut_positions.append(ep_match.start())

    if year_match:
        cut_positions.append(year_match.start())

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

    first_cut = min(cut_positions)
    main_title = name[:first_cut]
    main_title = re.sub(r"[\(\[\{\)\]\}]", " ", main_title)
    clean_title = " ".join(main_title.split()).strip()

    return clean_title, season_tag, extracted_year


def find_similar_key(new_key):
    """Deterministic merge matching - combines all qualities of the same movie/season"""
    norm_new = re.sub(r"[^a-zA-Z0-9]", "", new_key).lower()
    for existing_key in ACTIVE_POSTS.keys():
        norm_exist = re.sub(r"[^a-zA-Z0-9]", "", existing_key).lower()
        if norm_new == norm_exist:
            return existing_key
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
        
        if not extracted_year and caption_text:
            cap_year_match = re.search(r"\b(19\d\d|20\d\d)\b", caption_text)
            if cap_year_match:
                extracted_year = cap_year_match.group(1)

        if not clean_title:
            clean_title = raw_name.split()[0]

        bot_uname = temp.U_NAME or (await bot.get_me()).username
        
        # Ek single search query link taaki click karte hi bot me saari files mil jayein
        search_query = f"{clean_title} {season_tag}".strip()
        single_all_files_link = f"https://t.me/{bot_uname}?start=getfile-{search_query.replace(' ', '-')}"

        # Detect Languages
        combined_text = f"{raw_name} {caption_text}"
        languages_in_text = re.findall(r'\b(' + '|'.join(language_map.keys()) + r')\b', combined_text, re.IGNORECASE)
        unique_langs = []
        for l in languages_in_text:
            canonical = language_map[l.lower()]
            if canonical not in unique_langs:
                unique_langs.append(canonical)
        detected_languages = ", ".join(unique_langs) if unique_langs else "Hindi"

        # Unique Key for Merging
        current_merge_key = f"{clean_title.lower()}_{season_tag.lower()}_{extracted_year or ''}".strip()
        target_channels = POST_CHANNELS if isinstance(POST_CHANNELS, list) else [POST_CHANNELS]

        async with MERGE_LOCK:
            matched_key = find_similar_key(current_merge_key)

            # Agar post pehle se published hai (dusri quality aayi), to duplicate post nahi banega
            if matched_key:
                return

            # TMDb Details Fetching
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
                rating = imdb_info.get('rating', '0.0')
                poster_url = imdb_info.get('poster', None)
                plot = imdb_info.get('plot', 'No description available for this content.')
            else:
                title = display_title
                genres = "Drama, Series" if season_tag else "Drama, Action"
                year = extracted_year or current_yr
                rating = "0.0"
                poster_url = None
                plot = "No description available for this content."

            # Trim Plot if too long
            if len(plot) > 280:
                plot = plot[:275].rstrip() + "..."

            # Screenshot wala exact caption format
            final_caption = (
                f"🏷️Title: {title}\n"
                f"🎬 Genres: {genres}\n"
                f"⭐ Rating: {rating}/10\n"
                f"📆 Year: {year}\n"
                f"🌐 Language: {detected_languages}\n\n"
                f"📕 Story: {plot}\n\n"
                f"🔗 <a href='{single_all_files_link}'>Click Here To Get Files</a>\n\n"
                f"⚡ Powered By : <a href='https://t.me/mzmoviiez'>MzMoviiez</a>"
            )

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
                            disable_web_page_preview=True
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
                            parse_mode=enums.ParseMode.HTML,
                            disable_web_page_preview=True
                        )
                    sent_msg_ids[str(channel)] = msg.id
                except Exception as e:
                    logging.error(f"Error sending post: {e}")

            ACTIVE_POSTS[current_merge_key] = {
                "msg_ids": sent_msg_ids,
                "title": title
            }

    except Exception as e:
        logging.error(f"Auto post execution error: {str(e)}")
  
