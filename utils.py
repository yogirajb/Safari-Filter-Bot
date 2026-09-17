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
        if not TMDB_API_KEY:
            return query

        query = (query or "").strip()
        if len(query) < 3:
            return query

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

async def get_poster(query, bulk=False, id=False, file=None, year=None):
    """
    TMDb + IMDb (Cinemagoer) Smart Search Engine.
    Smartly distinguishes Indian vs Hollywood/Dubbed movies and TV serials.
    """
    try:
        media_type = "movie"
        q = (query or "").strip()
        search_year = year

        if not id:
            if not search_year:
                if file is not None:
                    m = re.findall(r"\b(19\d\d|20\d\d)\b", str(file))
                    if m:
                        search_year = m[-1]
                if not search_year:
                    m = re.findall(r"\b(19\d\d|20\d\d)\b", q)
                    if m:
                        search_year = m[-1]
                        q = re.sub(r"\b(19\d\d|20\d\d)\b", "", q).strip()

            clean_q = re.sub(r"\[.*?\]|\(.*?\)", " ", q)
            clean_q = re.sub(r"[:\-_]", " ", clean_q)
            clean_q = " ".join(clean_q.split()).strip()

            queries_to_try = [clean_q]
            words = clean_q.split()
            if len(words) > 3:
                queries_to_try.append(" ".join(words[:3]))
            if len(words) > 2:
                queries_to_try.append(" ".join(words[:2]))

            is_series_file = False
            check_str = f"{file or ''} {q}".lower()
            if re.search(r"\b(season|s\d+|episode|ep\d+|e\d+|serial|drama)\b", check_str):
                is_series_file = True

            results = []
            if TMDB_API_KEY:
                async with aiohttp.ClientSession() as session:
                    for q_str in queries_to_try:
                        if is_series_file:
                            tv_params = {"api_key": TMDB_API_KEY, "query": q_str, "include_adult": "false"}
                            if search_year:
                                tv_params["first_air_date_year"] = int(search_year)
                            async with session.get(f"{TMDB_API_BASE}/search/tv", params=tv_params, timeout=8) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    res_list = data.get("results", [])
                                    if res_list:
                                        for r in res_list:
                                            r["media_type"] = "tv"
                                        results = res_list
                                        break
                        else:
                            params = {"api_key": TMDB_API_KEY, "query": q_str, "include_adult": "false"}
                            if search_year:
                                try:
                                    params["year"] = int(search_year)
                                    params["primary_release_year"] = int(search_year)
                                except ValueError:
                                    pass
                            async with session.get(f"{TMDB_API_BASE}/search/multi", params=params, timeout=8) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    res_list = [r for r in data.get("results", []) if r.get("media_type") in ["movie", "tv"]]
                                    if res_list:
                                        results = res_list
                                        break

            if bulk and results:
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

            best_match = None
            if results:
                file_str = f"{file or ''} {clean_q}".lower()
                is_explicit_dub = bool(re.search(r"\b(dubbed|dub|dual|multi)\b", file_str))
                has_hindi_tag = bool(re.search(r"\b(hindi|hin)\b", file_str))

                # 1. TV Series Priority
                if is_series_file:
                    for r in results:
                        if r.get("media_type") == "tv":
                            best_match = r
                            break

                # 2. Year Matching with Smart Language vs Popularity
                if not best_match and search_year:
                    year_matched = []
                    for r in results:
                        r_date = r.get("release_date") or r.get("first_air_date") or ""
                        r_year = r_date[:4]
                        if r_year and abs(int(r_year) - int(search_year)) <= 1:
                            year_matched.append(r)

                    if year_matched:
                        # Case A: Agar file me Hindi hai aur Dubbed/Dual nahi hai (Bollywood priority)
                        if has_hindi_tag and not is_explicit_dub:
                            for r in year_matched:
                                if r.get("original_language") in ["hi", "ta", "te", "mr", "bn", "ml"]:
                                    best_match = r
                                    break
                        # Case B: Agar Hollywood film hai ya Dubbed hai (Highest vote/popularity priority)
                        if not best_match:
                            year_matched.sort(key=lambda x: (x.get("vote_count", 0), x.get("popularity", 0)), reverse=True)
                            best_match = year_matched[0]

                # 3. Exact Title Match
                if not best_match:
                    for r in results:
                        r_title = (r.get("title") or r.get("name") or "").strip().lower()
                        if clean_q.lower() == r_title:
                            best_match = r
                            break

                # 4. Final Fallback: Sort by votes/popularity
                if not best_match:
                    results.sort(key=lambda x: (x.get("vote_count", 0), x.get("popularity", 0)), reverse=True)
                    best_match = results[0]

            if best_match:
                movie_id = best_match.get("id")
                media_type = best_match.get("media_type", "tv" if is_series_file else "movie")
            else:
                movie_id = None
        else:
            movie_id = int(query)
            media_type = "movie"

        # -------------------------------------------------------------
        # 1. TMDb Detail Retrieval
        # -------------------------------------------------------------
        if movie_id and TMDB_API_KEY:
            params = {
                "api_key": TMDB_API_KEY,
                "append_to_response": "credits,images",
                "include_image_language": "hi,en,null"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{TMDB_API_BASE}/{media_type}/{movie_id}", params=params, timeout=8) as resp:
                    if resp.status == 200:
                        movie = await resp.json()
                    else:
                        movie = None

            if movie and movie.get("success") is not False:
                title = movie.get("title") or movie.get("name")
                release_date = movie.get("release_date") or movie.get("first_air_date") or ""
                movie_year = release_date[:4] if release_date else (str(year) if year else "N/A")

                images = movie.get("images", {})
                posters = images.get("posters", [])
                poster_path = None
                if posters:
                    hi_posters = [p["file_path"] for p in posters if p.get("iso_639_1") == "hi"]
                    en_posters = [p["file_path"] for p in posters if p.get("iso_639_1") == "en"]
                    if hi_posters:
                        poster_path = hi_posters[0]
                    elif en_posters:
                        poster_path = en_posters[0]
                    else:
                        poster_path = posters[0].get("file_path")
                
                if not poster_path:
                    poster_path = movie.get("poster_path") or movie.get("backdrop_path")

                poster_url = f"{TMDB_IMG_BASE}{poster_path}" if poster_path else None
                overview = movie.get("overview") or "No description available for this content."
                genres = ", ".join([g.get("name") for g in movie.get("genres", [])]) or "Drama, Family"
                countries = ", ".join([c.get("name") for c in movie.get("production_countries", [])]) or "India"
                languages = ", ".join([l.get("english_name") for l in movie.get("spoken_languages", [])]) or "Hindi"
                rating = movie.get("vote_average", "0.0")

                credits = movie.get("credits", {})
                cast_list = [c.get("name") for c in credits.get("cast", [])][:10]
                cast = ", ".join(cast_list) or "N/A"
                crew = credits.get("crew", [])
                directors = [c.get("name") for c in crew if c.get("job") == "Director"] or [c.get("name") for c in movie.get("created_by", [])]
                writers = [c.get("name") for c in crew if c.get("department") == "Writing"]

                imdb_id = movie.get("imdb_id")
                url = f"https://www.imdb.com/title/{imdb_id}" if imdb_id else f"https://www.themoviedb.org/{media_type}/{movie_id}"

                return {
                    "title": title,
                    "votes": movie.get("vote_count", "N/A"),
                    "aka": "N/A",
                    "seasons": str(movie.get("number_of_seasons", "N/A")),
                    "box_office": movie.get("revenue", "N/A"),
                    "localized_title": movie.get("original_title") or movie.get("original_name") or title,
                    "kind": media_type,
                    "imdb_id": imdb_id or f"tmdb-{movie_id}",
                    "cast": cast,
                    "runtime": str(movie.get("runtime") or (movie.get("episode_run_time", [None])[0] if movie.get("episode_run_time") else "N/A")),
                    "countries": countries,
                    "certificates": "N/A",
                    "languages": languages,
                    "director": ", ".join(directors) or "N/A",
                    "writer": ", ".join(writers) or "N/A",
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
                    "url": url,
                }

        # -------------------------------------------------------------
        # 2. IMDb (Cinemagoer) Fallback
        # -------------------------------------------------------------
        loop = asyncio.get_running_loop()
        search_results = None
        for q_try in queries_to_try:
            search_results = await loop.run_in_executor(None, imdb.search_movie, q_try)
            if search_results:
                break

        if not search_results:
            return None

        best_imdb = None
        for item in search_results:
            kind = item.get("kind", "")
            if is_series_file and kind in ["tv series", "tv mini series", "episode"]:
                best_imdb = item
                break
            elif not is_series_file and kind in ["movie", "tv movie"]:
                best_imdb = item
                break

        if not best_imdb:
            best_imdb = search_results[0]

        full_movie = await loop.run_in_executor(None, imdb.get_movie, best_imdb.movieID)
        plot_list = full_movie.get("plot", [])
        raw_plot = plot_list[0] if plot_list else full_movie.get("plot outline", "No description available for this content.")
        if "::" in raw_plot:
            raw_plot = raw_plot.split("::")[0]

        cast_list = [c.get("name") for c in full_movie.get("cast", [])][:10]
        directors = [d.get("name") for d in full_movie.get("director", [])]
        writers = [w.get("name") for w in full_movie.get("writer", [])]

        return {
            "title": full_movie.get("title"),
            "votes": str(full_movie.get("votes", "N/A")),
            "aka": "N/A",
            "seasons": str(full_movie.get("number of seasons", "N/A")),
            "box_office": "N/A",
            "localized_title": full_movie.get("title"),
            "kind": full_movie.get("kind", "tv series" if is_series_file else "movie"),
            "imdb_id": f"tt{best_imdb.movieID}",
            "cast": ", ".join(cast_list) or "N/A",
            "runtime": str(full_movie.get("runtimes", ["N/A"])[0]),
            "countries": ", ".join(full_movie.get("countries", ["India"])),
            "certificates": "N/A",
            "languages": ", ".join(full_movie.get("languages", ["Hindi"])),
            "director": ", ".join(directors) or "N/A",
            "writer": ", ".join(writers) or "N/A",
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

    except Exception as e:
        logger.error(f"get_poster error: {e}")
        return None

async def get_settings(group_id):
    settin
