# This code has been modified by @MzBotz
# Universal Token Stream Parser - Production Stable with Dynamic Episode Range
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

# Telegram photo caption maximum limit is 1024 chars
SAFE_MAX_CAPTION_LENGTH = 980

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
    - Strips leading channel tags, branding & brackets
    - Extracts Year, Season, Episode, Multi-Episode Range & Combined tags
    """
    name = re.sub(r"\.(mkv|mp4|avi|webm|zip|rar)$", "", str(filename), flags=re.IGNORECASE)
    name = re.sub(r"^\s*(\[.*?\]|\(.*?\))\s*", "", name)
    name = re.sub(r"(?i)^\s*@\w+(\s+(movies|cinema|films|series|hub|channel|official|off|tv|network|media))?\s*", "", name)
    name = re.sub(r"[\._\-\+:]", " ", name)
    name = " ".join(name.split()).strip()

    year_match = re.search(r"\b(19\d\d|20\d\d)\b", name)
    extracted_year = year_match.group(1) if year_match else None

    # Season & Episode Detection
    se_comb_match = re.search(r"(?i)\bS(\d{1,2})\s*(?:E|EP)\s*(\d{1,4})\b", name)
    range_match = re.search(r"(?i)\b(?:e|ep|episode|episodes)\s*(\d{1,4})\s*(?:-|to)\s*(?:e|ep)?\s*(\d{1,4})\b", name)
    s_match = re.search(r"(?i)\b(?:season\s*(\d{1,2})|S(\d{1,2}))\b", name)
    ep_match = re.search(r"(?i)\b(?:episode|ep)\s*(\d{1,4})\b|\bE(\d{1,4})\b", name)
    combined_match = re.search(r"(?i)\b(combined|complete|all\s*episodes|full\s*season|pack|batch)\b", name)

    season_tag = ""
    episodes_found = set()
    is_combined = False
    cut_positions = [len(name)]

    if range_match:
        s_ep = int(range_match.group(1))
        e_ep = int(range_match.group(2))
        for x in range(min(s_ep, e_ep), max(s_ep, e_ep) + 1):
            episodes_found.add(x)
        cut_positions.append(range_match.start())

    if se_comb_match:
        s_num = int(se_comb_match.group(1))
        ep_num = int(se_comb_match.group(2))
        season_tag = f"S{s_num:02d}"
        episodes_found.add(ep_num)
        cut_positions.append(se_comb_match.start())
    elif s_match:
        s_num = int(s_match.group(1) or s_match.group(2))
        season_tag = f"S{s_num:02d}"
        cut_positions.append(s_match.start())

    if ep_match:
        ep_num = int(ep_match.group(1) or ep_match.group(2))
        episodes_found.add(ep_num)
        if not season_tag:
            season_tag = "S01"
        cut_positions.append(ep_match.start())

    if combined_match:
        is_combined = True
        cut_positions.append(combined_match.start())

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

    return clean_title, season_tag, episodes_found, is_combined, extracted_year


def format_episode_string(episodes_set, is_combined):
    """Generates formatted string e.g. Episode 01 or Episode 01-05"""
    if is_combined and not episodes_set:
        return "Combined (All Episodes)"
    if not episodes_set:
        return ""
    sorted_eps = sorted(list(episodes_set))
    if len(sorted_eps) == 1:
        return f"Episode {sorted_eps[0]:02d}"
    min_ep = sorted_eps[0]
    max_ep = sorted_eps[-1]
    return f"Episode {min_ep:02d}-{max_ep:02d}"


def build_safe_caption(title, genres, rating, year, ep_string, languages, plot, single_all_files_link):
    """Builds caption and ensures it strictly stays well under 1024 Telegram limit"""
    ep_line = f"📺 Episode: {ep_string}\n" if ep_string else ""
    
    # Safe trim on plot
    if len(plot) > 450:
        plot = plot[:445].rstrip() + "..."

    caption = (
        f"🏷️Title: {title}\n"
        f"🎬 Genres: {genres}\n"
        f"⭐ Rating: {rating}/10\n"
        f"📆 Year: {year}\n"
        f"{ep_line}"
        f"🌐 Language: {languages}\n\n"
        f"📕 Story: {plot}\n\n"
        f"🔗 <a href='{single_all_files_link}'>Click Here To Get Files</a>\n\n"
        f"⚡ Powered By : <a href='https://t.me/mzmoviiez'>MzMoviiez</a>"
    )

    # Hard emergency guard against length overflow
    if len(caption) > SAFE_MAX_CAPTION_LENGTH:
        overflow = len(caption) - SAFE_MAX_CAPTION_LENGTH
        trimmed_plot = plot[:-overflow - 5].rstrip() + "..."
        caption = (
            f"🏷️Title: {title}\n"
            f"🎬 Genres: {genres}\n"
            f"⭐ Rating: {rating}/10\n"
            f"📆 Year: {year}\n"
            f"{ep_line}"
            f"🌐 Language: {languages}\n\n"
            f"📕 Story: {trimmed_plot}\n\n"
            f"🔗 <a href='{single_all_files_link}'>Click Here To Get Files</a>\n\n"
            f"⚡ Powered By : <a href='https://t.me/mzmoviiez'>MzMoviiez</a>"
        )
    return caption


def find_similar_key(new_key):
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

    # 1. Save File to Database
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

        clean_title, season_tag, new_eps, is_comb, extracted_year = clean_movie_title(raw_name)
        
        if not extracted_year and caption_text:
            cap_year_match = re.search(r"\b(19\d\d|20\d\d)\b", caption_text)
            if cap_year_match:
                extracted_year = cap_year_match.group(1)

        if not clean_title:
            clean_title = raw_name.split()[0]

        bot_uname = temp.U_NAME or (await bot.get_me()).username
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

        # Unique Season Key for Merging
        current_merge_key = f"{clean_title.lower()}_{season_tag.lower()}_{extracted_year or ''}".strip()
        target_channels = POST_CHANNELS if isinstance(POST_CHANNELS, list) else [POST_CHANNELS]

        async with MERGE_LOCK:
            matched_key = find_similar_key(current_merge_key)

            # -------------------------------------------------------------
            # CASE 1: Season Post Exists -> Auto-edit with Updated Episodes
            # -------------------------------------------------------------
            if matched_key:
                post_data = ACTIVE_POSTS[matched_key]
                old_eps_count = len(post_data["episodes"])
                post_data["episodes"].update(new_eps)
                if is_comb:
                    post_data["is_combined"] = True

                # Edit post only if new episodes were actually added
                if len(post_data["episodes"]) > old_eps_count or (is_comb and not post_data.get("edited_for_comb")):
                    post_data["edited_for_comb"] = True
                    new_ep_str = format_episode_string(post_data["episodes"], post_data["is_combined"])
                    
                    updated_caption = build_safe_caption(
                        post_data["title"], post_data["genres"], post_data["rating"],
                        post_data["year"], new_ep_str, post_data["languages"],
                        post_data["plot"], single_all_files_link
                    )

                    for channel_id, msg_id in post_data["msg_ids"].items():
                        try:
                            await bot.edit_message_caption(
                                chat_id=int(channel_id),
                                message_id=int(msg_id),
                                caption=updated_caption,
                                parse_mode=enums.ParseMode.HTML
                            )
                        except FloodWait as fw:
                            await asyncio.sleep(fw.value)
                            await bot.edit_message_caption(
                                chat_id=int(channel_id),
                                message_id=int(msg_id),
                                caption=updated_caption,
                                parse_mode=enums.ParseMode.HTML
                            )
                        except Exception as e:
                            logging.error(f"Error updating post caption: {e}")
                return

            # -------------------------------------------------------------
            # CASE 2: New Movie or New Season First Post
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

            ep_str = format_episode_string(new_eps, is_comb)
            final_caption = build_safe_caption(
                title, genres, rating, year, ep_str, detected_languages, plot, single_all_files_link
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
                "title": title,
                "genres": genres,
                "rating": rating,
                "year": year,
                "languages": detected_languages,
                "plot": plot,
                "episodes": set(new_eps),
                "is_combined": is_comb,
                "edited_for_comb": False
            }

    except Exception as e:
        logging.error(f"Auto post execution error: {str(e)}")
  
