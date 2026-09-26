# This code has been modified by @MzBotz
# Universal Token Stream Parser - Quality Badges + Inline Button Support
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from info import CHANNELS, POST_CHANNELS, AUTO_POST
from database.ia_filterdb import save_file
from utils import get_poster, get_size, temp
from difflib import SequenceMatcher
from datetime import datetime
import logging
import os
import re
import html
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
    "chi": "Chinese", "chinese": "Chinese",
    "dual": "Dual Audio", "multi": "Multi Audio"
}

def extract_qualities(filename):
    """Detects video quality tags from the filename"""
    qualities = set()
    fn = str(filename).lower()
    
    if re.search(r"\b(2160p|4k)\b", fn):
        qualities.add("4K")
    if re.search(r"\b1080p\b", fn):
        qualities.add("1080p")
    if re.search(r"\b720p\b", fn):
        qualities.add("720p")
    if re.search(r"\b480p\b", fn):
        qualities.add("480p")
    if re.search(r"\b(hevc|x265|10bit)\b", fn):
        qualities.add("HEVC")
        
    order = ["480p", "720p", "1080p", "4K", "HEVC"]
    sorted_q = [q for q in order if q in qualities]
    return sorted_q

def clean_movie_title(filename):
    """
    Universal Title Parser:
    - Strips branding, channel names
    - Cuts exactly before Season/Episode tags
    - Handles numeric titles (e.g. 1917)
    - Year priority cut for titles with parts (e.g. Toy Story 5)
    - Full support for multi-episode ranges with/without brackets (e.g. [E413-E427], EP(13-16))
    """
    raw_str = str(filename)
    name = re.sub(r"\.(mkv|mp4|avi|webm|zip|rar)$", "", raw_str, flags=re.IGNORECASE)
    name = re.sub(r"^\s*(\[.*?\]|\(.*?\))\s*", "", name)
    name = re.sub(r"(?i)^\s*@\w+(\s+(movies|cinema|films|series|hub|channel|official|off|tv|network|media))?\s*", "", name)

    # 1. Episode Range Detection (Hyphen, en-dash, em-dash, ya 'to' - Space allowed nahi hai taaki 720p na jude)
    raw_bracket_range = re.search(r"(?i)[\[\(]?\s*(?:S(\d{1,2}))?\s*(?:E|EP|Episode|Episodes)?\s*\(?(\d{1,4})\)?\s*[\-\–\—]|(?:\bto\b)\s*(?:E|EP|Episode|Episodes)?\s*\(?(\d{1,4})\)?\s*[\]\)]?", name)
    
    season_tag = ""
    episodes_found = set()
    is_combined = bool(re.search(r"(?i)\b(combined|complete|all\s*episodes|full\s*season|pack|batch)\b", name))
    cut_positions = [len(name)]

    if raw_bracket_range and (raw_bracket_range.group(2) and raw_bracket_range.group(3)):
        if raw_bracket_range.group(1):
            s_num = int(raw_bracket_range.group(1))
            season_tag = f"S{s_num:02d}"
        s_ep = int(raw_bracket_range.group(2))
        e_ep = int(raw_bracket_range.group(3))
        for x in range(min(s_ep, e_ep), max(s_ep, e_ep) + 1):
            episodes_found.add(x)
        cut_positions.append(raw_bracket_range.start())

    # Standardize string for subsequent checks
    name = re.sub(r"[\._\-\+:]", " ", name)
    name = " ".join(name.split()).strip()

    # Season & Episode Detection (Fallback)
    se_range_match = re.search(r"(?i)\bS(\d{1,2})\s*(?:E|EP)\s*(\d{1,4})\s*(?:-|–|—|\bto\b)\s*(?:E|EP)?\s*(\d{1,4})\b", name)
    range_match = re.search(r"(?i)\b(?:e|ep|episode|episodes)\s*(\d{1,4})\s*(?:-|–|—|\bto\b)\s*(?:e|ep)?\s*(\d{1,4})\b", name)
    se_comb_match = re.search(r"(?i)\bS(\d{1,2})\s*(?:E|EP)\s*(\d{1,4})\b", name)
    s_match = re.search(r"(?i)\b(?:season\s*(\d{1,2})|S(\d{1,2}))\b", name)
    ep_match = re.search(r"(?i)\b(?:episode|ep)\s*(\d{1,4})\b|\bE(\d{1,4})\b", name)
    combined_match = re.search(r"(?i)\b(combined|complete|all\s*episodes|full\s*season|pack|batch)\b", name)

    if not episodes_found:
        if se_range_match:
            s_num = int(se_range_match.group(1))
            season_tag = f"S{s_num:02d}"
            s_ep = int(se_range_match.group(2))
            e_ep = int(se_range_match.group(3))
            for x in range(min(s_ep, e_ep), max(s_ep, e_ep) + 1):
                episodes_found.add(x)
            cut_positions.append(se_range_match.start())
        elif range_match:
            s_ep = int(range_match.group(1))
            e_ep = int(range_match.group(2))
            for x in range(min(s_ep, e_ep), max(s_ep, e_ep) + 1):
                episodes_found.add(x)
            cut_positions.append(range_match.start())

    if not season_tag and se_comb_match:
        s_num = int(se_comb_match.group(1))
        ep_num = int(se_comb_match.group(2))
        season_tag = f"S{s_num:02d}"
        if not episodes_found:
            episodes_found.add(ep_num)
        cut_positions.append(se_comb_match.start())
    elif not season_tag and s_match:
        s_num = int(s_match.group(1) or s_match.group(2))
        season_tag = f"S{s_num:02d}"
        cut_positions.append(s_match.start())

    if ep_match and not episodes_found:
        ep_num = int(ep_match.group(1) or ep_match.group(2))
        episodes_found.add(ep_num)
        if not season_tag:
            season_tag = "S01"
        cut_positions.append(ep_match.start())

    if combined_match:
        is_combined = True
        cut_positions.append(combined_match.start())

    # Smart Year Detection - Priority cut for Part Numbers (e.g. Toy Story 5)
    all_years = list(re.finditer(r"\b(19\d\d|20\d\d)\b", name))
    extracted_year = None
    year_cut = None

    if all_years:
        for ym in all_years:
            if ym.start() > 0:
                extracted_year = ym.group(1)
                year_cut = ym.start()
                break

    token_boundary = re.search(
        r"(?i)\b(480p|720p|1080p|2160p|4k|hdrip|webrip|web-dl|web|bluray|dvd|camrip|hdcam|"
        r"x264|x265|hevc|10bit|10\s*bit|ds4k|aac\d*|ddp\d*|dd\d*|dts|truehd|sub|esub|esubs|"
        r"kannada|hindi|english|telugu|tamil|malayalam|marathi|gujarati|punjabi|bengali|"
        r"hq|clean|hd|combined|sample|uncut|uply|archie|mgreborn|mkvcinemas|zee5|amzn|dual|audio|org|"
        r"sonyliv|sony|liv|itunes|hotstar|jiocinema|voot|altbalaji|aha|mxplayer|netflix|primevideo|"
        r"kukutv|kuku|storytv|story|pocketfm|dramabox|reelshort|shortmax|"
        r"hdr10plus|hdr10|hdr|dv|dovi|nf|hs|jhs|v\d+|psa|primexofficial|@\w+|\d+mb|\d+gb|\d+kbps)\b",
        name
    )

    if year_cut:
        first_cut = year_cut
    else:
        if token_boundary and token_boundary.start() > 0:
            cut_positions.append(token_boundary.start())
        first_cut = min(cut_positions)

    main_title = name[:first_cut]
    main_title = re.sub(r"[\(\[\{\)\]\}]", " ", main_title)
    clean_title = " ".join(main_title.split()).strip()

    if not clean_title:
        clean_title = name.split()[0]

    return clean_title, season_tag, episodes_found, is_combined, extracted_year

def format_episode_string(episodes_set, is_combined):
    """Generates formatted string e.g. Episode 01, Episode 01-50, Episode 413-427"""
    if is_combined and not episodes_set:
        return "Combined (All Episodes)"
    if not episodes_set:
        return ""
    sorted_eps = sorted(list(episodes_set))
    if len(sorted_eps) == 1:
        ep = sorted_eps[0]
        return f"Episode {ep:02d}" if ep < 100 else f"Episode {ep}"
    min_ep = sorted_eps[0]
    max_ep = sorted_eps[-1]
    min_str = f"{min_ep:02d}" if min_ep < 100 else str(min_ep)
    max_str = f"{max_ep:02d}" if max_ep < 100 else str(max_ep)
    return f"Episode {min_str}-{max_str}"

def build_safe_caption(title, genres, rating, year, ep_string, qualities, languages, plot, single_all_files_link):
    """Guaranteed clean HTML Bold rendering without parser drops"""
    try:
        clean_rating = f"{float(rating):.1f}"
    except Exception:
        clean_rating = str(rating)

    s_title = html.escape(str(title))
    s_genres = html.escape(str(genres))
    s_langs = html.escape(str(languages))
    
    raw_plot = re.sub(r"<[^>]+>", "", str(plot))
    safe_plot = html.escape(raw_plot)
    if len(safe_plot) > 380:
        safe_plot = safe_plot[:375].rstrip() + "..."

    ep_line = f"📺 <b>Episode :</b> <b>{html.escape(ep_string)}</b>\n" if ep_string else ""
    q_str = " | ".join(qualities) if qualities else ""
    quality_line = f"🎛️ <b>Quality :</b> <b>{html.escape(q_str)}</b>\n" if q_str else ""

    caption = (
        f"🏷️ <b>Title :</b> <b>{s_title}</b>\n"
        f"🎬 <b>Genres :</b> <b>{s_genres}</b>\n"
        f"⭐ <b>Rating :</b> <b>{clean_rating}/10</b>\n"
        f"📆 <b>Year :</b> <b>{year}</b>\n"
        f"{ep_line}"
        f"{quality_line}"
        f"🌐 <b>Language :</b> <b>{s_langs}</b>\n\n"
        f"📕 <b>Story :</b> <b>{safe_plot}</b>\n\n"
        f"🔗 <b><a href='{single_all_files_link}'>Click Here To Get Files</a></b>\n\n"
        f"⚡ <b>Powered By :</b> <b><a href='https://t.me/mzmoviiez'>𝐌𝐳𝐌𝐨𝐯𝐢𝐢𝐞𝐳</a></b>"
    )

    if len(caption) > SAFE_MAX_CAPTION_LENGTH:
        overflow = len(caption) - SAFE_MAX_CAPTION_LENGTH
        safe_plot = safe_plot[:-overflow - 10].rstrip() + "..."
        caption = (
            f"🏷️ <b>Title :</b> <b>{s_title}</b>\n"
            f"🎬 <b>Genres :</b> <b>{s_genres}</b>\n"
            f"⭐ <b>Rating :</b> <b>{clean_rating}/10</b>\n"
            f"📆 <b>Year :</b> <b>{year}</b>\n"
            f"{ep_line}"
            f"{quality_line}"
            f"🌐 <b>Language :</b> <b>{s_langs}</b>\n\n"
            f"📕 <b>Story :</b> <b>{safe_plot}</b>\n\n"
            f"🔗 <b><a href='{single_all_files_link}'>Click Here To Get Files</a></b>\n\n"
            f"⚡ <b>Powered By :</b> <b><a href='https://t.me/mzmoviiez'>𝐌𝐳𝐌𝐨𝐯𝐢𝐢𝐞𝐳</a></b>"
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

    # Check if embedded thumbnail exists
    has_thumb = bool(getattr(media, "thumbs", None))

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
        new_qualities = extract_qualities(f"{raw_name} {caption_text}")
        
        if not extracted_year and caption_text:
            cap_year_match = re.search(r"\b(19\d\d|20\d\d)\b", caption_text)
            if cap_year_match:
                extracted_year = cap_year_match.group(1)

        bot_uname = temp.U_NAME or (await bot.get_me()).username
        search_query = f"{clean_title} {season_tag}".strip()
        single_all_files_link = f"https://t.me/{bot_uname}?start=getfile-{search_query.replace(' ', '-')}"

        post_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ Get All Files Now ⚡", url=single_all_files_link)]
        ])

        # Detect Languages
        combined_text = f"{raw_name} {caption_text}"
        searchable_lang_text = re.sub(r"[\._\-\+:]", " ", combined_text)

        is_dual = bool(re.search(r"(?i)\b(dual|dual\s*audio)\b", searchable_lang_text))
        is_multi = bool(re.search(r"(?i)\b(multi|multi\s*audio)\b", searchable_lang_text))

        languages_in_text = re.findall(
            r"(?i)\b(" + "|".join(language_map.keys()) + r")\b", 
            searchable_lang_text
        )
        unique_langs = []
        for l in languages_in_text:
            canonical = language_map[l.lower()]
            if canonical not in unique_langs:
                unique_langs.append(canonical)

        if is_multi:
            detected_languages = "Multi Audio"
        elif is_dual:
            detected_languages = "Dual Audio"
        elif unique_langs:
            detected_languages = ", ".join(unique_langs)
        else:
            detected_languages = None

        # -----------------------------------------------------------------
        # DAILY TV SERIAL vs WEB SERIES/MOVIE MERGE KEY LOGIC
        # -----------------------------------------------------------------
        # ep_tag hata diya taaki Episode 01 ke baad Episode 02 usi post me merge ho sake
        current_merge_key = f"{clean_title.lower()}_{season_tag.lower()}_{extracted_year or ''}".strip()
        target_channels = POST_CHANNELS if isinstance(POST_CHANNELS, list) else [POST_CHANNELS]

        async with MERGE_LOCK:
            matched_key = find_similar_key(current_merge_key)

            # CASE 1: Post Exists -> Auto-edit
            if matched_key:
                post_data = ACTIVE_POSTS[matched_key]
                old_eps_count = len(post_data["episodes"])
                old_q_count = len(post_data["qualities"])
                
                post_data["episodes"].update(new_eps)
                post_data["qualities"].update(new_qualities)
                if is_comb:
                    post_data["is_combined"] = True

                has_new_ep = len(post_data["episodes"]) > old_eps_count
                has_new_q = len(post_data["qualities"]) > old_q_count
                comb_updated = is_comb and not post_data.get("edited_for_comb")

                if has_new_ep or has_new_q or comb_updated:
                    if comb_updated:
                        post_data["edited_for_comb"] = True
                        
                    new_ep_str = format_episode_string(post_data["episodes"], post_data["is_combined"])
                    
                    order = ["480p", "720p", "1080p", "4K", "HEVC"]
                    sorted_q = [q for q in order if q in post_data["qualities"]]

                    updated_caption = build_safe_caption(
                        post_data["title"], post_data["genres"], post_data["rating"],
                        post_data["year"], new_ep_str, sorted_q, post_data["languages"],
                        post_data["plot"], single_all_files_link
                    )

                    for channel_id, msg_id in post_data["msg_ids"].items():
                        try:
                            await bot.edit_message_caption(
                                chat_id=int(channel_id),
                                message_id=int(msg_id),
                                caption=updated_caption,
                                parse_mode=enums.ParseMode.HTML,
                                reply_markup=post_markup
                            )
                        except FloodWait as fw:
                            await asyncio.sleep(fw.value)
                            await bot.edit_message_caption(
                                chat_id=int(channel_id),
                                message_id=int(msg_id),
                                caption=updated_caption,
                                parse_mode=enums.ParseMode.HTML,
                                reply_markup=post_markup
                            )
                        except Exception as e:
                            logging.error(f"Error updating post caption: {e}")
                return

            # CASE 2: New Post Creation
            imdb_info = None
            try:
                # 1. Base clean title nikalein (Season / Episode tags ke pehle ka hissa)
                pure_search_title = re.split(r"(?i)\b(s\d{1,2}|e\d{1,4}|season\s*\d+|episode\s*\d+)\b", clean_title)[0].strip()
                if not pure_search_title:
                    pure_search_title = clean_title

                search_yr = extracted_year
                
                # Attempt 1: Full cleaned title se search
                imdb_info = await get_poster(pure_search_title, year=search_yr, file=f"{pure_search_title} {season_tag}")
                if not imdb_info and search_yr:
                    imdb_info = await get_poster(pure_search_title, year=None, file=f"{pure_search_title} {season_tag}")

                # Attempt 2: Agar nahi mila aur title lamba hai (Tagline/Subtitle laga hai)
                # Jaise "Maharashtrachi Hasyajatra Comedycha 5G" -> pehle 2 words "Maharashtrachi Hasyajatra" se dhoondo
                if not imdb_info and season_tag:
                    words = pure_search_title.split()
                    if len(words) > 2:
                        short_title = " ".join(words[:2])
                        imdb_info = await get_poster(short_title, year=None, file=f"{short_title} {season_tag}")
                        if not imdb_info and len(words) > 3:
                            short_title = " ".join(words[:3])
                            imdb_info = await get_poster(short_title, year=None, file=f"{short_title} {season_tag}")
            except Exception as e:
                logging.error(f"Error fetching Poster: {e}")

            if imdb_info and imdb_info.get("title"):
                title = imdb_info.get("title")
                if season_tag and season_tag.lower() not in title.lower():
                    title = f"{title} {season_tag}".strip()
            else:
                title = f"{pure_search_title.title()} {season_tag}".strip()

            current_yr = str(datetime.now().year)

            if imdb_info:
                imdb_year = str(imdb_info.get('year', ''))
                year = extracted_year or imdb_year or current_yr
                genres = imdb_info.get('genres', 'Drama, Action')
                rating = imdb_info.get('rating', '0.0')
                poster_url = imdb_info.get('poster', None)
                plot = imdb_info.get('plot', 'No description available for this content.')
                
                imdb_lang = imdb_info.get('languages') or imdb_info.get('language')
                if isinstance(imdb_lang, list):
                    imdb_lang = ", ".join(imdb_lang)
                final_languages = detected_languages or imdb_lang or "Hindi"
            else:
                genres = "Drama, Series" if season_tag else "Drama, Action"
                year = extracted_year or current_yr
                rating = "0.0"
                poster_url = None
                plot = "No description available for this content."
                final_languages = detected_languages or "Hindi"

            ep_str = format_episode_string(new_eps, is_comb)
            final_caption = build_safe_caption(
                title, genres, rating, year, ep_str, new_qualities, final_languages, plot, single_all_files_link
            )

            sent_msg_ids = {}

            # Thumbnail download agar web/tmdb poster na ho
            local_thumb_path = None
            if not poster_url and has_thumb:
                try:
                    local_thumb_path = await bot.download_media(media.thumbs[0])
                except Exception as e:
                    logging.error(f"Error downloading thumb: {e}")
                    local_thumb_path = None

            final_photo = poster_url or local_thumb_path

            for channel in target_channels:
                try:
                    if final_photo:
                        msg = await bot.send_photo(
                            chat_id=int(channel),
                            photo=final_photo,
                            caption=final_caption,
                            has_spoiler=True,
                            parse_mode=enums.ParseMode.HTML,
                            reply_markup=post_markup
                        )
                    else:
                        msg = await bot.send_message(
                            chat_id=int(channel),
                            text=final_caption,
                            parse_mode=enums.ParseMode.HTML,
                            disable_web_page_preview=True,
                            reply_markup=post_markup
                        )
                    sent_msg_ids[str(channel)] = msg.id
                except FloodWait as fw:
                    await asyncio.sleep(fw.value)
                    if final_photo:
                        msg = await bot.send_photo(
                            chat_id=int(channel),
                            photo=final_photo,
                            caption=final_caption,
                            has_spoiler=True,
                            parse_mode=enums.ParseMode.HTML,
                            reply_markup=post_markup
                        )
                    else:
                        msg = await bot.send_message(
                            chat_id=int(channel),
                            text=final_caption,
                            parse_mode=enums.ParseMode.HTML,
                            disable_web_page_preview=True,
                            reply_markup=post_markup
                        )
                    sent_msg_ids[str(channel)] = msg.id
                except Exception as e:
                    logging.error(f"Error sending post: {e}")

            # Temp thumb cleanup taaki server storage fill na ho
            if local_thumb_path and os.path.exists(local_thumb_path):
                try:
                    os.remove(local_thumb_path)
                except Exception:
                    pass

            ACTIVE_POSTS[current_merge_key] = {
                "msg_ids": sent_msg_ids,
                "title": title,
                "genres": genres,
                "rating": rating,
                "year": year,
                "languages": final_languages,
                "plot": plot,
                "episodes": set(new_eps),
                "qualities": set(new_qualities),
                "is_combined": is_comb,
                "edited_for_comb": False
            }

    except Exception as e:
        logging.error(f"Auto post execution error: {e}")
