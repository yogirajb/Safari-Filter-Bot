# This code has been modified by @Safaridev
# Please do not remove this credit
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from info import CHANNELS, POST_CHANNELS
from database.ia_filterdb import save_file, get_file_details
from utils import get_poster, get_size, temp
from difflib import SequenceMatcher
import logging
import re
import asyncio

media_filter = filters.document | filters.video | filters.audio

# Memory cache for Auto-Merging
ACTIVE_POSTS = {}
MERGE_LOCK = asyncio.Lock()

# Telegram Photo Caption Limit is 1024 characters
MAX_CAPTION_LENGTH = 950 

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
    """Accurately extracts clean movie/series title, season/ep tags and year"""
    name = re.sub(r"\.(mkv|mp4|avi|webm|zip|rar)$", "", str(filename), flags=re.IGNORECASE)
    name = re.sub(r"[\._\-\+]", " ", name)
    
    # Detect TV Episode or Season (e.g. S01E21, S01, Season 1)
    ep_match = re.search(r"(?i)\b(s\d+\s*e\d+|ep?\d+)\b", name)
    ep_tag = ep_match.group(0).upper().replace(" ", "") if ep_match else None

    season_match = re.search(r"(?i)\b(s\d+|season\s*\d+)\b", name)
    season_tag = season_match.group(0).upper().replace(" ", "") if (season_match and not ep_tag) else None

    year_match = re.search(r"\b(19\d\d|20\d\d)\b", name)
    year = year_match.group(1) if year_match else None

    cut_pos = len(name)
    if ep_match:
        cut_pos = min(cut_pos, ep_match.start())
    elif season_match:
        cut_pos = min(cut_pos, season_match.start())
    elif year_match:
        cut_pos = min(cut_pos, year_match.start())

    main_title = name[:cut_pos]

    junk_patterns = (
        r"(?i)\b(1080p|720p|480p|360p|2160p|4k|hdrip|webrip|web-dl|web|bluray|dvdrip|predvd|dvd|camrip|hdcam|"
        r"x264|x265|hevc|10bit|ds4k|aac\d*|ddp\d*|dts|truehd|h\.264|h\.265|sub|esub|complete|zip|pack|"
        r"kannada|hindi|english|telugu|tamil|malayalam|marathi|gujarati|punjabi|bengali|"
        r"hq|clean|hd|combined|sample|uncut|uply|archie|mgreborn|mkvcinemas|zee5|amzn|p\d+t\d+|x\s*pro|pro|v\d+|@\w+)\b"
    )
    main_title = re.sub(junk_patterns, " ", main_title)
    main_title = re.sub(r"\[.*?\]|\(.*?\)", " ", main_title)
    clean_title = " ".join(main_title.split()).strip()

    extra_tag = ep_tag or season_tag or ""
    return clean_title, extra_tag, year


def find_similar_key(new_key):
    """Finds if a similar movie/series already exists in ACTIVE_POSTS (Fuzzy Match)"""
    for existing_key in ACTIVE_POSTS.keys():
        if new_key == existing_key:
            return existing_key
        ratio = SequenceMatcher(None, new_key, existing_key).ratio()
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

    # --- Safe Coroutine Handler for save_file ---
    try:
        res = save_file(media)
        if asyncio.iscoroutine(res):
            res = await res
        success, file_id = res
    except TypeError:
        res = save_file(bot, media)
        if asyncio.iscoroutine(res):
            res = await res
        success, file_id = res
    except Exception as e:
        logging.error(f"Error saving to DB: {e}")
        return
    
    if not success or not file_id:
        return

    file_details = await get_file_details(file_id)[span_3](start_span)[span_3](end_span)
    if file_details:
        file_id = file_details[0]['file_id'][span_4](start_span)[span_4](end_span)
        
    if not POST_CHANNELS:
        return

    try:
        raw_name = getattr(media, "file_name", None) or "Movie"
        clean_title, extra_tag, extracted_year = clean_movie_title(raw_name)
        
        if not clean_title:
            clean_title = raw_name.split()[0]

        file_name_display = raw_name.replace('_', ' ')
        size_text = get_size(media.file_size)[span_5](start_span)[span_5](end_span)
        bot_uname = temp.U_NAME or (await bot.get_me()).username[span_6](start_span)[span_6](end_span)
        channel_ref = CHANNELS[0] if isinstance(CHANNELS, list) and CHANNELS else "db[span_7](start_span)"[span_7](end_span)
        file_url = f"https://t.me/{bot_uname}?start=files_{channel_ref}_{file_id}[span_8](start_span)"[span_8](end_span)
        
        new_file_entry = (file_url, file_name_display, size_text)

        # Detect Languages
        combined_text = f"{raw_name} {media.caption or ''}[span_9](start_span)"[span_9](end_span)
        languages_in_text = re.findall(r'\b(' + '|'.join(language_map.keys()) + r')\b', combined_text, re.IGNORECASE)
        unique_langs = []
        for l in languages_in_text:
            canonical = language_map[l.lower()]
            if canonical not in unique_langs:
                unique_langs.append(canonical)
        detected_languages = ", ".join(unique_langs) if unique_langs else "Hindi"

        current_merge_key = f"{clean_title.lower()} {extra_tag.lower()}".strip()
        target_channels = POST_CHANNELS if isinstance(POST_CHANNELS, list) else [POST_CHANNELS][span_10](start_span)[span_10](end_span)

        async with MERGE_LOCK:
            matched_key = find_similar_key(current_merge_key)

            # -------------------------------------------------------------
            # CASE 1: अगर पोस्ट पहले से मौजूद है और कैप्शन में जगह है (Merge)
            # -------------------------------------------------------------
            if matched_key:
                post_data = ACTIVE_POSTS[matched_key]
                temp_files = list(post_data["files"])
                
                if not any(f[0] == file_url for f in temp_files):
                    temp_files.append(new_file_entry)

                urls_text = "\n\n".join([f"📁 [{size}] 👇\n<a href='{url}'>{name}</a>" for url, name, size in temp_files])
                final_caption = f"{post_data['header']}\n\n{urls_text}"

                # अगर कैप्शन 1024 की लिमिट के अंदर है तो एडिट करें
                if len(final_caption) <= MAX_CAPTION_LENGTH:
                    post_data["files"] = temp_files
                    for channel_id, msg_id in post_data["msg_ids"].items():
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
                            logging.error(f"Error editing post in channel {channel_id}: {e}")
                    return

            # -------------------------------------------------------------
            # CASE 2: नई पोस्ट बनाएं (अगर नई मूवी हो या पिछला कैप्शन फुल हो गया हो)
            # -------------------------------------------------------------
            imdb_info = None
            try:
                imdb_info = await get_poster(clean_title)[span_11](start_span)[span_11](end_span)
            except Exception as e:
                logging.error(f"Error fetching IMDb: {e}")

            display_title = f"{clean_title.title()} {extra_tag}".strip()

            if imdb_info:
                title = imdb_info.get('title', display_title)[span_12](start_span)[span_12](end_span)
                genres = imdb_info.get('genres', 'Drama, Action')[span_13](start_span)[span_13](end_span)
                year = imdb_info.get('year', extracted_year or '2024')[span_14](start_span)[span_14](end_span)
                rating = imdb_info.get('rating', 'N/A')[span_15](start_span)[span_15](end_span)
                poster_url = imdb_info.get('poster', None)[span_16](start_span)[span_16](end_span)
            else:
                title = display_title
                genres = "Drama, Action"
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
                    logging.error(f"Error sending new post to {channel}: {e}")

            # Save in memory cache
            ACTIVE_POSTS[current_merge_key] = {
                "msg_ids": sent_msg_ids,
                "files": [new_file_entry],
                "header": header_text,
                "poster": poster_url
            }

    except Exception as e:
        logging.error(f"Auto post execution error: {str(e)}")
                   
