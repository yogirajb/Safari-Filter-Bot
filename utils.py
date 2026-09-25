# This code has been modified by @MzBotz
# Please do not remove this credit
import os
import requests
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/original"
import logging
from pyrogram.errors import InputUserDeactivated, UserNotParticipant, FloodWait, UserIsBlocked, PeerIdInvalid, ChatAdminRequired, MessageIdInvalid, EmoticonInvalid, ReactionInvalid
from info import *
from imdb import Cinemagoer 
import asyncio
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import enums
from typing import Union
from urllib.parse import quote_plus
from Script import script
import pytz
import random 
from random import choice
from asyncio import sleep
import time
import re
from datetime import datetime, timedelta, date, time
import string
from typing import List
from database.users_chats_db import db
from bs4 import BeautifulSoup
import aiohttp
from types import SimpleNamespace
from shortzy import Shortzy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BTN_URL_REGEX = re.compile(
    r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))"
)

imdb = Cinemagoer()
BANNED = {}
SMART_OPEN = '“'
SMART_CLOSE = '”'
START_CHAR = ('\'', '"', SMART_OPEN)

class temp(object):
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    CURRENT = int(os.environ.get("SKIP", 2))
    CANCEL = False
    MELCOW = {}
    U_NAME = None
    B_NAME = None
    SETTINGS = {}
    KEYWORD = {}
    GETALL = {}
    SPELL_CHECK = {}
    IMDB_CAP = {}
    CHAT = {}

def ai_fix_query(query: str) -> str:
    try:
        query = (query or "").strip()
        if len(query) < 3:
            return query

        url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={requests.utils.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=3)
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 1 and data[1]:
                for item in data[1]:
                    cleaned = re.sub(r"(?i)\b(movie|film|full movie|download|watch online|hindi|tamil|telugu)\b", "", item).strip()
                    cleaned = " ".join(cleaned.split())
                    if cleaned and cleaned.lower() != query.lower():
                        return cleaned
        return query
    except Exception:
        return query

async def check_reset_time():
    tz = pytz.timezone('Asia/Kolkata')
    while True:
        now = datetime.now(tz)
        target_time = time(23, 59)
        target_datetime = tz.localize(datetime.combine(now.date(), target_time))
        if now > target_datetime:
            target_datetime += timedelta(days=1)
        time_diff = (target_datetime - now).total_seconds()
        hours = time_diff // 3600
        minutes = (time_diff % 3600) // 60
        seconds = time_diff % 60
        logging.info(f"Next reset in {int(hours)} hours, {int(minutes)} minutes, and {int(seconds)} seconds.")
        await asyncio.sleep(time_diff)
        await db.reset_all_files_count()
        await db.reset_allsend_files()
        logging.info("Files count and send count reset successfully")

async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        unit = ""

        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1

        unit = ts[index:].lstrip()

        if value:
            value = int(value)

        return value, unit

    value, unit = extract_value_and_unit(time_string)

    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hour':
        return value * 3600
    elif unit == 'day':
        return value * 86400
    elif unit == 'month':
        return value * 86400 * 30
    elif unit == 'year':
        return value * 86400 * 365
    else:
        return 0
        
async def is_req_subscribed(bot, query):
    if await db.find_join_req(query.from_user.id):
        return True
    try:
        user = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
    except UserNotParticipant:
        pass
    except Exception as e:
        print(e)
    else:
        if user.status != enums.ChatMemberStatus.BANNED:
            return True
    return False

async def is_subscribed(bot, user_id, channel_id):
    try:
        user = await bot.get_chat_member(channel_id, user_id)
    except UserNotParticipant:
        pass
    except Exception as e:
        pass
    else:
        if user.status != enums.ChatMemberStatus.BANNED:
            return True
    return False

async def broadcast_messages(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.x)
        return await broadcast_messages(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        logging.info(f"{user_id} - Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception:
        return False, "Error"

async def fetch_web_poster(show_name):
    """
    Direct Cloud CDN image fetcher for Indian TV serials & Micro dramas.
    Never blocked on Koyeb/Cloud IPs.
    """
    try:
        clean_name = re.sub(r"[^a-zA-Z0-9 ]", " ", str(show_name)).strip()
        # Double quotes se Bing exact phrase search karega, aadha naam nahi uthayega
        search_query = f'"{clean_name}" serial drama poster'

        url = "https://tse1.mm.bing.net/th"
        params = {
            "q": search_query,
            "w": "500",
            "h": "700",
            "c": "7",
            "rs": "1",
            "p": "0"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    return str(resp.url)
    except Exception as e:
        logger.error(f"fetch_web_poster error: {e}")

    return None

async def get_poster(query, bulk=False, id=False, file=None, year=None):
    """
    TMDb + TV Serial Smart Matcher + Web Fallback
    """
    try:
        media_type = "movie"
        q = str(query or "").strip()
        search_year = str(year).strip() if year else None

        api_key = TMDB_API_KEY or os.environ.get("TMDB_API_KEY", "").strip()
        if not api_key:
            try:
                from info import TMDB_API_KEY as info_key
                api_key = str(info_key or "").strip()
            except Exception:
                pass

        if not id:
            file_and_q = f"{file or ''} {q}".lower()

            # 1. Season & Serial Detection
            season_tag = ""
            s_match = re.search(r"\b(s\d+|season\s*\d+)\b", file_and_q, re.IGNORECASE)
            if s_match:
                s_str = s_match.group(0).upper().replace("EASON", "").replace(" ", "")
                season_tag = f" {s_str}"

            is_series_file = bool(re.search(
                r"\b(season|s\d+|episode|ep\d+|e\d+|serial|drama|series|zee5|sonyliv|hotstar|jiocinema|daily|starplus|colors|dangal)\b",
                file_and_q, re.IGNORECASE
            ))

            is_indian_tagged = bool(re.search(
                r"\b(hindi|hin|tamil|tam|telugu|tel|malayalam|mal|kannada|kan|bengali|marathi|punjabi|dubbed|dub|dual|multi|south)\b",
                file_and_q, re.IGNORECASE
            ))

            raw_title = q
            raw_title = re.sub(r"\.(mkv|mp4|avi|webm)$", "", raw_title, flags=re.IGNORECASE)

            # TV Serials ke liye Episode tags ke pehle ka naam lein aur Year filter bypass karein
            if is_series_file:
                clean_q = re.split(r"(?i)\b(s\d+|e\d+|season\s*\d+|episode\s*\d+)\b", raw_title)[0]
                search_year = None
            else:
                year_match = re.search(r"[\. \-_(\[]((?:19|20)\d\d)[\. \-_)\]]", raw_title)
                if year_match:
                    search_year = year_match.group(1)
                    clean_q = raw_title[:year_match.start()]
                else:
                    clean_q = raw_title

            clean_q = re.sub(r"(?i)\b(480p|720p|1080p|2160p|4k|uhd|fhd|hd|hevc|x264|x265|h264|h265|10bit|8bit|bluray|blu-ray|web-dl|webdl|webrip|hdrip|dvdrip|aac|ac3|ddp|dts|esub|subs?|hindi|tamil|telugu|malayalam|kannada|dual|multi|dubbed|psa|primexofficial|zee5|hotstar|jiocinema|sonyliv)\b", " ", clean_q)
            clean_q = re.sub(r"\[.*?\]|\(.*?\)", " ", clean_q)
            clean_q = re.sub(r"[:\-_.]", " ", clean_q)
            clean_q = " ".join(clean_q.split()).strip()

            if not clean_q:
                clean_q = str(query or "").strip()

            # Progressive Query Tries (Full name, 4 words, 3 words)
            queries_to_try = [clean_q]
            words = clean_q.split()
            if len(words) > 4:
                queries_to_try.append(" ".join(words[:4]))
            if len(words) > 3:
                queries_to_try.append(" ".join(words[:3]))
            if len(words) > 2:
                queries_to_try.append(" ".join(words[:2]))

            results = []
            if api_key:
                async with aiohttp.ClientSession() as session:
                    for q_str in queries_to_try:
                        endpoint = "tv" if is_series_file else "movie"
                        params = {"api_key": api_key, "query": q_str, "include_adult": "false"}

                        if search_year and not is_series_file:
                            params["year"] = int(search_year)

                        async with session.get(f"{TMDB_API_BASE}/search/{endpoint}", params=params, timeout=8) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                res_list = data.get("results", [])
                                if res_list:
                                    for r in res_list:
                                        r["media_type"] = endpoint
                                    results = res_list
                                    break

            if bulk:
                if results:
                    movies = []
                    for res in results[:10]:
                        movies.append(
                            SimpleNamespace(
                                movieID=res.get("id"),
                                get=lambda key, r=res: r.get(key),
                                title=res.get("title") or res.get("name"),
                            )
                        )
                    return movies
                return []

            best_match = None
            if results:
                target_type = "tv" if is_series_file else "movie"
                type_matched = [r for r in results if r.get("media_type") == target_type] or results

                # 1. Exact Match Priority (Outer Banks, The Boys etc.)
                q_clean = re.sub(r"[^a-zA-Z0-9]", "", clean_q).lower()
                for r in type_matched:
                    r_title = (r.get("name") if target_type == "tv" else r.get("title")) or ""
                    r_clean = re.sub(r"[^a-zA-Z0-9]", "", r_title).lower()
                    
                    if q_clean == r_clean:
                        best_match = r
                        break

                # 2. Movies ke liye Normal Fallback, Series ke liye Half-name Bilkul Match Mat Karo
                if not best_match and not is_series_file:
                    type_matched.sort(key=lambda x: (
                        3 if (is_indian_tagged and x.get("original_language") in ["hi", "te", "ta", "ml", "kn", "bn", "mr", "pa"]) else 0,
                        x.get("vote_count", 0) > 30,
                        x.get("popularity", 0),
                        x.get("vote_count", 0)
                    ), reverse=True)
                    best_match = type_matched[0]

            if best_match:
                movie_id = best_match.get("id")
                media_type = best_match.get("media_type", "tv" if is_series_file else "movie")
            else:
                movie_id = None
        else:
            movie_id = int(query)
            media_type = "movie"
            season_tag = ""

        # TMDb Details Fetch
        if movie_id and api_key:
            params = {
                "api_key": api_key,
                "append_to_response": "credits,images",
                "include_image_language": "hi,en,te,ta,ml,kn,mr,null"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{TMDB_API_BASE}/{media_type}/{movie_id}", params=params, timeout=8) as resp:
                    if resp.status == 200:
                        movie = await resp.json()
                    else:
                        movie = None

            if movie and movie.get("success") is not False:
                fetched_title = movie.get("name") if media_type == "tv" else movie.get("title")
                fetched_title = fetched_title or movie.get("original_name") or clean_q
                final_display_title = f"{fetched_title}{season_tag}".strip()

                release_date = movie.get("first_air_date") if media_type == "tv" else movie.get("release_date")
                release_date = release_date or ""
                movie_year = release_date[:4] if release_date else (str(search_year) if search_year else "N/A")

                images = movie.get("images", {})
                posters = images.get("posters", [])
                poster_path = None
                if posters:
                    lang_posters = [p["file_path"] for p in posters if p.get("iso_639_1") in ["hi", "mr", "te", "ta", "ml", "kn"]]
                    en_posters = [p["file_path"] for p in posters if p.get("iso_639_1") == "en"]
                    if lang_posters:
                        poster_path = lang_posters[0]
                    elif en_posters:
                        poster_path = en_posters[0]
                    else:
                        poster_path = posters[0].get("file_path")

                if not poster_path:
                    poster_path = movie.get("poster_path") or movie.get("backdrop_path")

                poster_url = f"{TMDB_IMG_BASE}{poster_path}" if poster_path else None
                overview = movie.get("overview") or "No description available for this content."
                genres = ", ".join([g.get("name") for g in movie.get("genres", [])]) or "Drama, Series"
                rating = movie.get("vote_average", "0.0")

                return {
                    "title": final_display_title,
                    "votes": movie.get("vote_count", "N/A"),
                    "aka": "N/A",
                    "seasons": str(movie.get("number_of_seasons", "N/A")),
                    "box_office": movie.get("revenue", "N/A"),
                    "localized_title": final_display_title,
                    "kind": media_type,
                    "imdb_id": movie.get("imdb_id") or f"tmdb-{movie_id}",
                    "cast": ", ".join([c.get("name") for c in movie.get("credits", {}).get("cast", [])][:10]) or "N/A",
                    "runtime": str(movie.get("runtime") or "N/A"),
                    "countries": "India",
                    "certificates": "N/A",
                    "languages": "Hindi",
                    "director": "N/A",
                    "writer": "N/A",
                    "producer": "N/A",
                    "composer": "N/A",
                    "cinematographer": "N/A",
                    "music_team": "N/A",
                    "distributors": "N/A",
                    "release_date": release_date or "N/A",
                    "year": movie_year,
                    "genres": genres,
                    "poster": poster_url,
                    "plot": overview,
                    "rating": str(rating) if rating is not None else "0.0",
                    "url": f"https://www.themoviedb.org/{media_type}/{movie_id}",
                }

        # TV SERIALS & MICRO DRAMAS STRICT FALLBACK
        # Bing CDN ke galat / repeated posters ko rokne ke liye poster ko None rakhein
        if is_series_file:
            final_display_title = f"{clean_q.title()}{season_tag}".strip()
            return {
                "title": final_display_title,
                "votes": "N/A",
                "aka": "N/A",
                "seasons": "1",
                "box_office": "N/A",
                "localized_title": final_display_title,
                "kind": "tv",
                "imdb_id": "N/A",
                "cast": "N/A",
                "runtime": "N/A",
                "countries": "India",
                "certificates": "N/A",
                "languages": "Hindi",
                "director": "N/A",
                "writer": "N/A",
                "producer": "N/A",
                "composer": "N/A",
                "cinematographer": "N/A",
                "music_team": "N/A",
                "distributors": "N/A",
                "release_date": "N/A",
                "year": "2026",
                "genres": "Drama, Series",
                "poster": None,  # <--- ISKO NONE KAREIN
                "plot": f"{clean_q.title()} is a trending short drama series. Stream all episodes now.",
                "rating": "7.5",
                "url": "https://www.themoviedb.org",
            }

        # Agar Series/Serial file hai toh movie fallback par bilkul mat jao
        if is_series_file:
            return None
            
        # MOVIES FALLBACK (Cinemagoer) - Only for Movies
        loop = asyncio.get_running_loop()
        search_results = None
        for q_try in queries_to_try:
            try:
                search_results = await loop.run_in_executor(None, imdb.search_movie, q_try)
                if search_results:
                    break
            except Exception:
                pass

        if not search_results:
            return None

        best_imdb = search_results[0]
        try:
            full_movie = await loop.run_in_executor(None, imdb.get_movie, best_imdb.movieID)
            plot_list = full_movie.get("plot", [])
            raw_plot = plot_list[0] if plot_list else full_movie.get("plot outline", "No description available for this content.")
            if "::" in raw_plot:
                raw_plot = raw_plot.split("::")[0]

            return {
                "title": full_movie.get("title", clean_q),
                "votes": str(full_movie.get("votes", "N/A")),
                "aka": "N/A",
                "seasons": "N/A",
                "box_office": "N/A",
                "localized_title": full_movie.get("title", clean_q),
                "kind": "movie",
                "imdb_id": f"tt{best_imdb.movieID}",
                "cast": ", ".join([c.get("name") for c in full_movie.get("cast", [])][:10]) or "N/A",
                "runtime": "N/A",
                "countries": "India",
                "certificates": "N/A",
                "languages": "Hindi",
                "director": "N/A",
                "writer": "N/A",
                "producer": "N/A",
                "composer": "N/A",
                "cinematographer": "N/A",
                "music_team": "N/A",
                "distributors": "N/A",
                "release_date": str(full_movie.get("year", "N/A")),
                "year": str(full_movie.get("year", search_year or "N/A")),
                "genres": ", ".join(full_movie.get("genres", ["Drama"])),
                "poster": full_movie.get("full-size cover url") or full_movie.get("cover url"),
                "plot": raw_plot,
                "rating": str(full_movie.get("rating", "0.0")),
                "url": f"https://www.imdb.com/title/tt{best_imdb.movieID}",
            }
        except Exception:
            return None

    except Exception as e:
        logger.error(f"get_poster error: {e}")
        return None
        
async def get_settings(group_id):
    settings = temp.SETTINGS.get(group_id)
    if not settings:
        settings = await db.get_settings(group_id)
        temp.SETTINGS[group_id] = settings
    return settings
    
async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current[key] = value
    temp.SETTINGS[group_id] = current
    await db.update_settings(group_id, current)

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])
    
def list_to_str(k): 
    if not k:
        return "N/A"
    elif len(k) == 1:
        return str(k[0])
    else:
        return ' '.join(f'{elem}, ' for elem in k)
        
def get_file_id(msg: Message):
    if msg.media:
        for message_type in (
            "photo",
            "animation",
            "audio",
            "document",
            "video",
            "video_note",
            "voice",
            "sticker"
        ):
            obj = getattr(msg, message_type)
            if obj:
                setattr(obj, "message_type", message_type)
                return obj

def extract_user(message: Message) -> Union[int, str]:
    user_id = None
    user_first_name = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_first_name = message.reply_to_message.from_user.first_name

    elif len(message.command) > 1:
        if (
            len(message.entities) > 1 and
            message.entities[1].type == enums.MessageEntityType.TEXT_MENTION
        ):
            required_entity = message.entities[1]
            user_id = required_entity.user.id
            user_first_name = required_entity.user.first_name
        else:
            user_id = message.command[1]
            user_first_name = user_id
        try:
            user_id = int(user_id)
        except ValueError:
            pass
    else:
        user_id = message.from_user.id
        user_first_name = message.from_user.first_name
    return (user_id, user_first_name)

async def stream_site(link, grp_id):
    try:
        settings = await get_settings(grp_id) if await get_settings(grp_id) else {}
        api_key, site_key = ('streamapi', 'streamsite')
        default_api, default_site = STREAM_API, STREAM_SITE
        
        api = settings.get(api_key, default_api)
        site = settings.get(site_key, default_site)

        shortzy = Shortzy(api, site)

        try:
            link = await shortzy.convert(link)
        except Exception:
            link = await shortzy.get_quick_link(link)
        return link
    except Exception as e:
        logger.error(e)

async def get_shortlink(link, grp_id, is_second_shortener=False, is_third_shortener=False):
    settings = await get_settings(grp_id) if await get_settings(grp_id) else {}
    if is_third_shortener:
        api_key, site_key = ('verify_api3', 'verify_3')
        default_api, default_site = VERIFY_API3, VERIFY_URL3
    elif is_second_shortener:
        api_key, site_key = ('verify_api2', 'verify_2')
        default_api, default_site = VERIFY_API2, VERIFY_URL2
    else:
        api_key, site_key = ('verify_api', 'verify')
        default_api, default_site = VERIFY_API, VERIFY_URL

    api = settings.get(api_key, default_api)
    site = settings.get(site_key, default_site)
    shortzy = Shortzy(api, site)
    try:
        link = await shortzy.convert(link)
    except Exception:
        link = await shortzy.get_quick_link(link)
    return link

async def get_users():
    count  = await user_col.count_documents({})
    cursor = user_col.find({})
    list   = await cursor.to_list(length=int(count))
    return count, list

async def get_text(settings, remaining_seconds, files, query, total_results, search):
    try:
        if settings["imdb"]:
            IMDB_CAP = temp.IMDB_CAP.get(query.from_user.id)
            CAPTION = f"☠️ ᴛɪᴛʟᴇ : <code>{search}</code>\n📂 ᴛᴏᴛᴀʟ ꜰɪʟᴇꜱ : <code>{total_results}</code>\n📝 ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ : {query.from_user.first_name}\n⏰ ʀᴇsᴜʟᴛ ɪɴ : <code>{remaining_seconds} Sᴇᴄᴏɴᴅs</code>\n\n</b>"
            if IMDB_CAP:
                cap = IMDB_CAP
                for file in files:
                    cap += f"\n\n<b><a href='https://telegram.me/{temp.U_NAME}?start=files_{query.message.chat.id}_{file.file_id}'>📁 {get_size(file.file_size)} ▷ {file.file_name}</a></b>"
            else:
                imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
                if imdb:
                    TEMPLATE = script.IMDB_TEMPLATE_TXT
                    cap = TEMPLATE.format(
                        qurey=search,
                        title=imdb['title'],
                        votes=imdb['votes'],
                        aka=imdb["aka"],
                        seasons=imdb["seasons"],
                        box_office=imdb['box_office'],
                        localized_title=imdb['localized_title'],
                        kind=imdb['kind'],
                        imdb_id=imdb["imdb_id"],
                        cast=imdb["cast"],
                        runtime=imdb["runtime"],
                        countries=imdb["countries"],
                        certificates=imdb["certificates"],
                        languages=imdb["languages"],
                        director=imdb["director"],
                        writer=imdb["writer"],
                        producer=imdb["producer"],
                        composer=imdb["composer"],
                        cinematographer=imdb["cinematographer"],
                        music_team=imdb["music_team"],
                        distributors=imdb["distributors"],
                        release_date=imdb['release_date'],
                        year=imdb['year'],
                        genres=imdb['genres'],
                        poster=imdb['poster'],
                        plot=imdb['plot'],
                        rating=imdb['rating'],
                        url=imdb['url'],
                        **locals()
                    )
                    for file in files:
                        cap += f"\n\n<b><a href='https://telegram.me/{temp.U_NAME}?start=files_{query.message.chat.id}_{file.file_id}'>📁 {get_size(file.file_size)} ▷ {file.file_name}</a></b>"
                else:
                    cap = f"{CAPTION}"
                    cap+="<b>📚 <u>Your Requested Files</u> 👇\n\n</b>"
                    for file in files:
                        cap += f"<b><a href='https://telegram.me/{temp.U_NAME}?start=files_{query.message.chat.id}_{file.file_id}'>📁 {get_size(file.file_size)} ▷ {file.file_name}\n\n</a></b>"
        else:
            cap = f"☠️ ᴛɪᴛʟᴇ : <code>{search}</code>\n📂 ᴛᴏᴛᴀʟ ꜰɪʟᴇꜱ : <code>{total_results}</code>\n📝 ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ : {query.from_user.first_name}\n⏰ ʀᴇsᴜʟᴛ ɪɴ : <code>{remaining_seconds}\n\n</b>"
            cap+="<b>📚 <u>Your Requested Files</u> 👇\n\n</b>"
            for file in files:
                cap += f"<b><a href='https://telegram.me/{temp.U_NAME}?start=files_{query.message.chat.id}_{file.file_id}'>📁 {get_size(file.file_size)} ▷ {file.file_name}\n\n</a></b>"
        return cap
    except Exception as e:
        await query.answer(f"{e}", show_alert=True)
        return cap
