# This code has been modified by @Safaridev
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

# temp db for banned 
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
    """
    TMDb ki help se galat spelling ko sahi movie title me convert karta hai.
    Agar kuch na mile ya error aaye to original query hi return karega.
    """
    try:
        if not TMDB_API_KEY:
            return query

        query = (query or "").strip()
        if len(query) < 3:
            return query

        # Year alag nikaal lo (jaise "avatr 2009")
        year = None
        m = re.findall(r"[1-2]\d{3}$", query)
        if m:
            year = m[0]
            title = query.replace(year, "").strip()
        else:
            title = query

        params = {
            "api_key": TMDB_API_KEY,
            "query": title,
            "include_adult": False,
        }
        if year:
            params["year"] = int(year)

        r = requests.get(f"{TMDB_API_BASE}/search/movie", params=params, timeout=10)
        if r.status_code != 200:
            return query

        data = r.json()
        results = data.get("results") or []
        if not results:
            return query

        best = results[0]
        fixed_title = best.get("title") or best.get("name")
        release_date = (best.get("release_date") or "")[:4]

        if not fixed_title:
            return query

        if release_date:
            return f"{fixed_title} {release_date}"
        return fixed_title
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


# ... imports ke upar/neeche jo bhi hai, sirf get_poster ko replace karna hai

async def get_poster(query, bulk=False, id=False, file=None, year=None):
    """
    TMDb se Movies aur Web Series dono ka poster + details laata hai.
    """
    if not TMDB_API_KEY:
        return None

    try:
        media_type = "movie"
        if not id:
            q = (query or "").strip()
            title = q
            search_year = year

            # Query ke end me 4-digit year ho to (e.g. "avatar 2009")
            if not search_year:
                m = re.findall(r"\b(19\d\d|20\d\d)\b", q)
                if m:
                    search_year = m[-1]
                    title = re.sub(r"\b(19\d\d|20\d\d)\b", "", q).strip()
                elif file is not None:
                    m = re.findall(r"\b(19\d\d|20\d\d)\b", str(file))
                    if m:
                        search_year = m[-1]

            params = {
                "api_key": TMDB_API_KEY,
                "query": title,
                "include_adult": "false",
            }
            if search_year:
                try:
                    params["year"] = int(search_year)
                    params["primary_release_year"] = int(search_year)
                    params["first_air_date_year"] = int(search_year)
                except ValueError:
                    pass

            # /search/multi se Movie aur TV dono search honge
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{TMDB_API_BASE}/search/multi", params=params, timeout=10) as resp:
                    if resp.status != 200:
                        logger.error(f"TMDb search error: {resp.status}")
                        return None
                    data = await resp.json()

            results = [r for r in data.get("results", []) if r.get("media_type") in ["movie", "tv"]]
            if not results:
                return None

            if bulk:
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

            best_match = results[0]
            movie_id = best_match.get("id")
            media_type = best_match.get("media_type", "movie")
        else:
            movie_id = int(query)
            media_type = "movie"

        # ----- TMDb Detailed Info -----
        params = {
            "api_key": TMDB_API_KEY,
            "append_to_response": "credits",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{TMDB_API_BASE}/{media_type}/{movie_id}", params=params, timeout=10) as resp:
                if resp.status != 200 and media_type == "movie":
                    # Fallback to TV if movie failed on direct ID
                    async with session.get(f"{TMDB_API_BASE}/tv/{movie_id}", params=params, timeout=10) as tv_resp:
                        movie = await tv_resp.json()
                        media_type = "tv"
                else:
                    movie = await resp.json()

        if not movie or movie.get("success") is False:
            return None

        # Basic fields
        title = movie.get("title") or movie.get("name")
        release_date = movie.get("release_date") or movie.get("first_air_date") or ""
        movie_year = release_date[:4] if release_date else (str(year) if year else "N/A")

        poster_path = movie.get("poster_path")
        poster_url = f"{TMDB_IMG_BASE}{poster_path}" if poster_path else None

        overview = movie.get("overview") or "N/A"
        if overview and len(overview) > 800:
            overview = overview[:800] + "..."

        genres = ", ".join([g.get("name") for g in movie.get("genres", [])]) or "Drama, Action"
        countries = ", ".join([c.get("name") for c in movie.get("production_countries", [])]) or "N/A"
        languages = ", ".join([l.get("english_name") for l in movie.get("spoken_languages", [])]) or "Hindi, English"

        votes = movie.get("vote_count", "N/A")
        rating = movie.get("vote_average", "N/A")
        runtime = movie.get("runtime") or (movie.get("episode_run_time", [None])[0] if movie.get("episode_run_time") else "N/A")

        credits = movie.get("credits", {})
        cast_list = [c.get("name") for c in credits.get("cast", [])][:10]
        cast = ", ".join(cast_list) or "N/A"

        crew = credits.get("crew", [])
        directors = [c.get("name") for c in crew if c.get("job") == "Director"] or [c.get("name") for c in movie.get("created_by", [])]
        writers = [c.get("name") for c in crew if c.get("department") == "Writing"]
        producer = ", ".join([c.get("name") for c in crew if c.get("job") == "Producer"]) or "N/A"
        composer = ", ".join([c.get("name") for c in crew if "Music" in (c.get("department") or "")]) or "N/A"

        director = ", ".join(directors) or "N/A"
        writer = ", ".join(writers) or "N/A"

        imdb_id = movie.get("imdb_id")
        if imdb_id:
            url = f"https://www.imdb.com/title/{imdb_id}"
            imdb_id_str = imdb_id
        else:
            url = f"https://www.themoviedb.org/{media_type}/{movie_id}"
            imdb_id_str = f"tmdb-{movie_id}"

        return {
            "title": title,
            "votes": votes,
            "aka": "N/A",
            "seasons": str(movie.get("number_of_seasons", "N/A")),
            "box_office": movie.get("revenue", "N/A"),
            "localized_title": movie.get("original_title") or movie.get("original_name") or title,
            "kind": media_type,
            "imdb_id": imdb_id_str,
            "cast": cast,
            "runtime": str(runtime),
            "countries": countries,
            "certificates": "N/A",
            "languages": languages,
            "director": director,
            "writer": writer,
            "producer": producer,
            "composer": composer,
            "cinematographer": "N/A",
            "music_team": "N/A",
            "distributors": "N/A",
            "release_date": release_date or "N/A",
            "year": movie_year,
            "genres": genres,
            "poster": poster_url,
            "plot": overview,
            "rating": str(rating) if rating is not None else "N/A",
            "url": url,
        }
    except Exception as e:
        logger.error(f"TMDb get_poster error: {e}")
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
    """Get size in readable format"""

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
    """extracts the user from a message"""
    # https://github.com/SpEcHiDe/PyroGramBot/blob/f30e2cca12002121bad1982f68cd0ff9814ce027/pyrobot/helper_functions/extract_user.py#L7
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
            # don't want to make a request -_-
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
                for file in files: #shortlink = false, imdb = true
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
                    cap = f"{CAPTION}" #imdb = false
                    cap+="<b>📚 <u>Your Requested Files</u> 👇\n\n</b>"
                    for file in files:
                        cap += f"<b><a href='https://telegram.me/{temp.U_NAME}?start=files_{query.message.chat.id}_{file.file_id}'>📁 {get_size(file.file_size)} ▷ {file.file_name}\n\n</a></b>"
    
        else:
            #imdb = false
            cap = f"☠️ ᴛɪᴛʟᴇ : <code>{search}</code>\n📂 ᴛᴏᴛᴀʟ ꜰɪʟᴇꜱ : <code>{total_results}</code>\n📝 ʀᴇǫᴜᴇsᴛᴇᴅ ʙʏ : {query.from_user.first_name}\n⏰ ʀᴇsᴜʟᴛ ɪɴ : <code>{remaining_seconds}\n\n</b>"
            cap+="<b>📚 <u>Your Requested Files</u> 👇\n\n</b>"
            for file in files:
                cap += f"<b><a href='https://telegram.me/{temp.U_NAME}?start=files_{query.message.chat.id}_{file.file_id}'>📁 {get_size(file.file_size)} ▷ {file.file_name}\n\n</a></b>"
        return cap
    except Exception as e:
        await query.answer(f"{e}", show_alert=True)
        return cap
