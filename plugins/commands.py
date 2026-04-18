# This code has been modified by @Safaridev
# Please do not remove this credit
import os
import sys
import logging
import random
import asyncio
import pytz
import time as t
from telegram import InputMediaPhoto
import requests
import string
from Script import script
from datetime import datetime, timedelta, date, time
from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired, FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import Media, get_file_details, unpack_new_file_id, get_bad_files, get_search_results
from database.users_chats_db import db
from database.safari_reffer import sdb
from info import *
from .pm_filter import auto_filter
from utils import get_settings, get_size, is_subscribed, is_req_subscribed, save_group_settings, temp, get_shortlink, get_seconds, get_poster
from database.connections_mdb import active_connection
import re
import json
import base64
logger = logging.getLogger(__name__)

TIMEZONE = "Asia/Kolkata"

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    try: 
        await message.react(emoji=random.choice(REACTION), big=True)
        user_id = message.from_user.id
        send_count = await db.files_count(message.from_user.id, "send_all") or 0
        files_counts = await db.files_count(message.from_user.id, "files_count") or 0
        if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            buttons = [[
                        InlineKeyboardButton('☆ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ☆', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
                      ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            await message.reply_text(
                text="ᴏᴋ ɪ ᴄᴀɴ ʜᴇʟᴘ ʏᴏᴜ ᴊᴜsᴛ sᴛᴀʀᴛ ᴘᴍ", 
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            await asyncio.sleep(2) # 😢 https://github.com/EvamariaTG/EvaMaria/blob/master/plugins/p_ttishow.py#L17 😬 wait a bit, before checking.
            if not await db.get_chat(message.chat.id):
                total=await client.get_chat_members_count(message.chat.id)
                await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(temp.B_NAME, message.chat.title, message.chat.id, total, "Unknown"))       
                await db.add_chat(message.chat.id, message.chat.title, message.from_user.id)
            return 
        if not await db.is_user_exist(message.from_user.id):
            await db.add_user(message.from_user.id, message.from_user.first_name)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention, temp.B_NAME))
        if len(message.command) != 2:
            buttons = [[
                        InlineKeyboardButton('☆ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ☆', url=f'http://telegram.me/{temp.U_NAME}?startgroup=true')
                    ],[
                        InlineKeyboardButton('✪ ᴜᴘᴅᴀᴛᴇꜱ ✪', callback_data='channels'), 
                        InlineKeyboardButton('⚔️ғᴇᴀᴛᴜʀᴇs ⚔️', callback_data='features')
                    ],[
                        InlineKeyboardButton('🍀 Hᴇʟᴘ 🍀', callback_data='help'),
                        InlineKeyboardButton('🤖 ᴀʙᴏᴜᴛ 🤖', callback_data='about')
                    ],[
                        InlineKeyboardButton('🆓 ᴘʀᴇᴍɪᴜᴍ', callback_data="pm_reff"), 
                        InlineKeyboardButton('✨ ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ ✨', callback_data="premium_info")
                    ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            m=await message.reply_sticker("CAACAgQAAxkBAAEKeqNlIpmeUoOEsEWOWEiPxPi3hH5q-QACbg8AAuHqsVDaMQeY6CcRojAE") 
            await asyncio.sleep(2)
            await m.delete()
            await message.reply_photo(
                photo=random.choice(PICS),
                caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
                reply_markup=reply_markup,
                has_spoiler=True,
                parse_mode=enums.ParseMode.HTML
            )
            return
        if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
            buttons = [[
                        InlineKeyboardButton('☆ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ☆', url=f'http://telegram.me/{temp.U_NAME}?startgroup=true')
                    ],[
                        InlineKeyboardButton('✪ ᴜᴘᴅᴀᴛᴇꜱ ✪', callback_data='channels'), 
                        InlineKeyboardButton('⚔️ ғᴇᴀᴛᴜʀᴇs ⚔️', callback_data='features')
                    ],[
                        InlineKeyboardButton('🍀 Hᴇʟᴘ 🍀', callback_data='help'),
                        InlineKeyboardButton('🤖 ᴀʙᴏᴜᴛ 🤖', callback_data='about')
                    ],[
                        InlineKeyboardButton('🆓 ᴘʀᴇᴍɪᴜᴍ', callback_data="pm_reff"), 
                        InlineKeyboardButton('✨ ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ ✨', callback_data="premium_info")
                    ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            m=await message.reply_sticker("CAACAgQAAxkBAAEKeqNlIpmeUoOEsEWOWEiPxPi3hH5q-QACbg8AAuHqsVDaMQeY6CcRojAE") 
            await asyncio.sleep(2)
            await m.delete()
            await message.reply_photo(
                photo=random.choice(PICS),
                caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
                reply_markup=reply_markup,
                has_spoiler=True,
                parse_mode=enums.ParseMode.HTML
            )
            return
        if len(message.command) == 2 and message.command[1] in ["safaridev"]:
            buttons = [[
                        InlineKeyboardButton('📲 ꜱᴇɴᴅ ᴘᴀʏᴍᴇɴᴛ ꜱᴄʀᴇᴇɴꜱʜᴏᴛ', url=f"https://t.me/{OWNER_USER_NAME}")
                      ],[
                        InlineKeyboardButton('❌ ᴄʟᴏꜱᴇ ❌', callback_data='close_data')
                      ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            await message.reply_photo(
                photo=(PREMIUM_PIC),
                caption=script.PREMIUM_CMD,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            return  
        if message.command[1].startswith('getfile'):
            data = message.command[1].split("-", 1)
            file_name = data[1].replace('-', ' ')
            message.text = file_name 
            await auto_filter(client, message)
            return
    
        if message.command[1].startswith("reff_"):
            try:
                user_id = int(message.command[1].split("_")[1])
            except ValueError:
                await message.reply_text("Invalid refer!")
                return
            if user_id == message.from_user.id:
                await message.reply_text("Hᴇʏ Dᴜᴅᴇ, Yᴏᴜ Cᴀɴ'ᴛ Rᴇғᴇʀ Yᴏᴜʀsᴇʟғ 🤣!\n\nsʜᴀʀᴇ ʟɪɴᴋ ʏᴏᴜʀ ғʀɪᴇɴᴅ ᴀɴᴅ ɢᴇᴛ 5 ʀᴇғᴇʀʀᴀʟ ᴘᴏɪɴᴛ ɪғ ʏᴏᴜ ᴀʀᴇ ᴄᴏʟʟᴇᴄᴛɪɴɢ 50 ʀᴇғᴇʀʀᴀʟ ᴘᴏɪɴᴛs ᴛʜᴇɴ ʏᴏᴜ ᴄᴀɴ ɢᴇᴛ 1 ᴍᴏɴᴛʜ ғʀᴇᴇ ᴘʀᴇᴍɪᴜᴍ ᴍᴇᴍʙᴇʀsʜɪᴘ.")
                return
            if sdb.is_user_in_list(message.from_user.id):
                await message.reply_text("Yᴏᴜ ʜᴀᴠᴇ ʙᴇᴇɴ ᴀʟʀᴇᴀᴅʏ ɪɴᴠɪᴛᴇᴅ ❗")
                return
            try:
                uss = await client.get_users(user_id)
            except Exception:
                return 	    
            sdb.add_user(message.from_user.id)
            fromuse = sdb.get_refer_points(user_id) + 10
            sdb.add_refer_points(user_id, fromuse)
            await message.reply_text(f"You have been successfully invited by {uss.mention}!")
            await client.send_message(user_id, f"𝗖𝗼𝗻𝗴𝗿𝗮𝘁𝘂𝗹𝗮𝘁𝗶𝗼𝗻𝘀! 𝗬𝗼𝘂 𝘄𝗼𝗻 𝟭𝟬 𝗥𝗲𝗳𝗲𝗿𝗿𝗮𝗹 𝗽𝗼𝗶𝗻𝘁 𝗯𝗲𝗰𝗮𝘂𝘀𝗲 𝗬𝗼𝘂 𝗵𝗮𝘃𝗲 𝗯𝗲𝗲𝗻 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗜𝗻𝘃𝗶𝘁𝗲𝗱 ☞{message.from_user.mention}!") 
            if fromuse == REFFER_POINT:
                await db.give_referal(user_id)
                sdb.add_refer_points(user_id, 0) 
                await client.send_message(chat_id=user_id,
                    text=f"<b>Hᴇʏ {uss.mention}\n\nYᴏᴜ ɢᴏᴛ 1 ᴍᴏɴᴛʜ ᴘʀᴇᴍɪᴜᴍ sᴜʙsᴄʀɪᴘᴛɪᴏɴ ʙʏ ɪɴᴠɪᴛɪɴɢ 5 ᴜsᴇʀs ❗", disable_web_page_preview=True              
                    )
                for admin in ADMINS:
                    await client.send_message(chat_id=admin, text=f"Sᴜᴄᴄᴇss ғᴜʟʟʏ ᴛᴀsᴋ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ʙʏ ᴛʜɪs ᴜsᴇʀ:\n\nuser Nᴀᴍᴇ: {uss.mention}\n\nUsᴇʀ ɪᴅ: {uss.id}!")	
                return
        safari = message
        user_id = safari.from_user.id  
        if len(safari.command) == 2:
            if safari.command[1].startswith(('verify', 'sendall')):
                _, userid, verify_id, file_id = safari.command[1].split("_", 3)
                user_id = int(userid)
                grp_id = temp.CHAT.get(user_id, 0)
                settings = await get_settings(grp_id)         
                verify_id_info = await db.get_verify_id_info(user_id, verify_id)
                if not verify_id_info or verify_id_info["verified"]:
                    await message.reply("<b>ʟɪɴᴋ ᴇxᴘɪʀᴇᴅ ᴛʀʏ ᴀɢᴀɪɴ...</b>")
                    return
                
                ist_timezone = pytz.timezone('Asia/Kolkata')
                if await db.user_verified(user_id):
                    key = "third_verified"
                else:
                    key = "second_verified" if await db.is_user_verified(user_id) else "last_verified"
                current_time = datetime.now(tz=ist_timezone)
                result = await db.update_safari_user(user_id, {key:current_time})
                await db.update_verify_id_info(user_id, verify_id, {"verified":True})
                if key == "third_verified": 
                    num = 3 
                else: 
                    num =  2 if key == "second_verified" else 1
                if key == "third_verified":
                    msg = script.THIRDT_COMPLETE_TEXT
                else:
                    msg = script.SECOND_COMPLETE_TEXT if key == "second_verified" else script.VERIFY_COMPLETE_TEXT
                if safari.command[1].startswith('sendall'):
                    verify = f"https://telegram.me/{temp.U_NAME}?start=allfiles_{grp_id}_{file_id}"
                else:
                    verify = f"https://telegram.me/{temp.U_NAME}?start=files_{grp_id}_{file_id}"
                
                await client.send_message(settings['log'], script.VERIFIED_LOG_TEXT.format(safari.from_user.mention, user_id, datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d %B %Y'), num))
                btn = [[
                    InlineKeyboardButton("✅ ɢᴇᴛ ꜰɪʟᴇ ✅", url=verify),
                ]]
                reply_markup=InlineKeyboardMarkup(btn)
                dlt=await safari.reply_photo(
                    photo=(VERIFY_IMG),
                    caption=msg.format(message.from_user.mention),
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
                await asyncio.sleep(600)
                await dlt.delete()
                return
        
        data = message.command[1] if len(message.command) > 1 else ""

        try:
            pre, grp_id, file_id = data.split('_', 2)
        except:
            pre, grp_id, file_id = "", 0, data

# 🔥 MULTI FORCE SUB SYSTEM
        not_joined = []

        for channel in AUTH_CHANNELS:
            try:
                member = await client.get_chat_member(channel, message.from_user.id)
                if member.status in ["kicked", "left"]:
                    not_joined.append(channel)
            except Exception:
                not_joined.append(channel)

        # ✅ FORCE SUBSCRIBE BLOCK (FIXED)
        if not_joined:
            buttons = []

            for ch in not_joined:
                try:
                    invite_link = await client.create_chat_invite_link(
                        ch,
                        creates_join_request=True
                    )

                    buttons.append([
                        InlineKeyboardButton(
                            "⛔️ ᴊᴏɪɴ ɴᴏᴡ ⛔️",
                            url=invite_link.invite_link
                        )
                    ])
                except Exception:
                    continue

            if data != "subscribe":
                if data.startswith("allfiles"):
                    buttons.append([
                        InlineKeyboardButton(
                            "♻️ ᴛʀʏ ᴀɢᴀɪɴ ♻️",
                            url=f"https://t.me/{temp.U_NAME}?start=allfiles_{grp_id}_{file_id}"
                        )
                    ])
                else:
                    buttons.append([
                        InlineKeyboardButton(
                            "♻️ ᴛʀʏ ᴀɢᴀɪɴ ♻️",
                            url=f"https://t.me/{temp.U_NAME}?start=files_{grp_id}_{file_id}"
                        )
                    ])

            await client.send_message(
                chat_id=message.from_user.id,
                text=script.FSUB_TXT.format(message.from_user.mention),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=enums.ParseMode.HTML
            )
            return        
       
        if not await db.has_premium_access(user_id):
            settings = await get_settings(int(grp_id))
            is_verify = settings["is_verify"]
            if not is_verify:
                is_verify = await db.get_setting("IS_VERIFY", default=IS_VERIFY)
            user_verified = await db.is_user_verified(user_id)
            is_second_shortener = await db.use_second_shortener(user_id, settings.get('verify_time', TWO_VERIFY_GAP))
            is_third_shortener = await db.use_third_shortener(user_id, settings.get('verify_time', THIRD_VERIFY_GAP))     
            if (not user_verified or is_second_shortener or is_third_shortener) and is_verify:
                verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
                await db.create_verify_id(user_id, verify_id)
                temp.CHAT[user_id] = grp_id
                tutorial = settings.get('tutorial3', TUTORIAL3) if is_third_shortener else settings.get('tutorial2', TUTORIAL2) if is_second_shortener else settings.get('tutorial', TUTORIAL)
                
                if safari.command[1].startswith('allfiles'):
                    verify = await get_shortlink(f"https://telegram.me/{temp.U_NAME}?start=sendall_{user_id}_{verify_id}_{file_id}", grp_id, is_second_shortener, is_third_shortener)
                else:
                    verify = await get_shortlink(f"https://telegram.me/{temp.U_NAME}?start=verify_{user_id}_{verify_id}_{file_id}", grp_id, is_second_shortener, is_third_shortener)
                if not await db.check_trial_status(user_id):
                    buttons = [[
                        InlineKeyboardButton("✅️ ᴠᴇʀɪғʏ ✅️", url=verify)
                    ],[
                        InlineKeyboardButton("⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ ⁉️", url=tutorial)
                    ],[
                        InlineKeyboardButton("✨5ᴍɪɴ Pʀᴇᴍɪᴜᴍ Tʀᴀɪʟ✨", callback_data=f'give_trial')
                    ]]
                else:
                    buttons = [[
                        InlineKeyboardButton("✅️ ᴠᴇʀɪғʏ ✅️", url=verify)
                    ],[
                        InlineKeyboardButton("⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪғʏ ⁉️", url=tutorial)
                    ],[
                        InlineKeyboardButton("✨ ʀᴇᴍᴏᴠᴇ ᴠᴇʀɪғʏ ✨", callback_data=f'premium_info')
                    ]]
                reply_markup=InlineKeyboardMarkup(buttons) 
                if await db.user_verified(user_id): 
                    msg = script.THIRDT_VERIFICATION_TEXT   
                else:        
                    msg = script.SECOND_VERIFICATION_TEXT if is_second_shortener else script.VERIFICATION_TEXT
                d = await safari.reply_text(
                    text=msg.format(message.from_user.mention),
                    protect_content = False,
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
                await asyncio.sleep(600) 
                await d.delete()
                await safari.delete()
                return
        if data and data.startswith("allfiles"):
            files = temp.GETALL.get(file_id)
            if not files:
                return await message.reply('<b><i>Nᴏ Sᴜᴄʜ Fɪʟᴇ Eᴇxɪsᴛ.</b></i>')
            filesarr = []
            for file in files:
                file_id = file.file_id
                files_ = await get_file_details(file_id)
                files1 = files_[0]
                settings = await get_settings(int(grp_id))
                CAPTION = settings.get('caption', CUSTOM_FILE_CAPTION)
                f_caption = CAPTION.format(
                    file_name = files1.file_name,
                    file_size = get_size(files1.file_size),
                    file_caption=files1.caption
                )
                if not await db.has_premium_access(message.from_user.id):
                    limit = settings.get("all_limit", SEND_ALL_LIMITE)
                    if settings.get("filelock", LIMIT_MODE):
                        await db.update_files(message.from_user.id, "send_all", send_count + 1)
                        files_count=await db.files_count(message.from_user.id, "send_all")
                        f_caption += f"<b>\n\nAʟʟ Bᴜᴛᴛᴏɴ Lɪᴍɪᴛ : {files_count}/{limit}</b>"
                        if send_count is not None and send_count >= limit:
                            buttons = [[
                                       InlineKeyboardButton('✨ Rᴇᴍᴏᴠᴇ Lɪᴍɪᴛᴇ ✨', callback_data=f'premium_info')
                                      ]]
                            reply_markup = InlineKeyboardMarkup(buttons)
                            return await message.reply_text(script.BUTTON_LIMIT, 
                            reply_markup=reply_markup)
                button = [[
                    InlineKeyboardButton("🖥️ ᴡᴀᴛᴄʜ / ᴅᴏᴡɴʟᴏᴀᴅ 📥", callback_data=f"streaming#{file_id}#{grp_id}")
                    ]]
                reply_markup=InlineKeyboardMarkup(button)
                msg = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=file_id,
                    caption=f_caption,
                    protect_content=True if pre == 'filep' else False,
                    reply_markup=reply_markup
                )
                filesarr.append(msg)
            if await db.get_setting("AUTO_FILE_DELETE", default=AUTO_FILE_DELETE):
                k = await client.send_message(chat_id = message.from_user.id, text=f"<b><u>❗️❗️❗️IMPORTANT❗️️❗️❗️</u></b>\n\nThis Movie Files/Videos will be deleted in <b><u>10 mins</u> 🫥 <i></b>(Due to Copyright Issues)</i>.\n\n<b><i>Please forward this ALL Files/Videos to your Saved Messages and Start Download there</i></b>")
                await asyncio.sleep(900)
                for x in filesarr:
                    await x.delete()
                await k.edit_text("<b>Your All Files/Videos is successfully deleted!!!</b>")
            return
        files_ = await get_file_details(file_id)           
        if not files_:
            pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
            try:
                if not await db.has_premium_access(message.from_user.id):
                    limit = settings.get("file_limit", FILE_LIMITE)
                    if settings.get("filelock", LIMIT_MODE):
                        await db.update_files(message.from_user.id, "files_count", files_counts + 1)
                        files_count=await db.files_count(message.from_user.id, "files_count")
                        f_caption += f"<b>\n\nDᴀɪʟʏ Fɪʟᴇ Lɪᴍɪᴛ: {files_count}/{limit}</b>"      
                        if files_counts is not None and files_counts >= limit:
                            buttons = [[
                                       InlineKeyboardButton('✨ Rᴇᴍᴏᴠᴇ Lɪᴍɪᴛᴇ ✨', callback_data=f'premium_info')
                                      ]]
                            reply_markup = InlineKeyboardMarkup(buttons)
                            return await message.reply_text(script.FILE_LIMIT,
                            reply_markup=reply_markup)
                button = [[
                    InlineKeyboardButton("🖥️ ᴡᴀᴛᴄʜ / ᴅᴏᴡɴʟᴏᴀᴅ 📥", callback_data=f"streaming#{file_id}#{grp_id}")
                    ]]
                reply_markup=InlineKeyboardMarkup(button)
                msg = await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=file_id,
                    protect_content=True if pre == 'filep' else False,
                    reply_markup=reply_markup
                )
                filetype = msg.media
                file = getattr(msg, filetype.value)
                title = file.file_name
                size=get_size(file.file_size)
                f_caption = f"<code>{title}</code>"
                if CUSTOM_FILE_CAPTION:
                    try:
                        f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='')
                    except:
                        return
                await msg.edit_caption(f_caption)
                return
            except:
                pass
            return await message.reply('Nᴏ sᴜᴄʜ ғɪʟᴇ ᴇxɪsᴛ.')
        
        files = files_[0]
        settings = await get_settings(int(grp_id))
        CAPTION = settings.get('caption', CUSTOM_FILE_CAPTION)
        f_caption = CAPTION.format(
            file_name = files.file_name,
            file_size = get_size(files.file_size),
            file_caption=files.caption
        )
        if not await db.has_premium_access(message.from_user.id):
            limit = settings.get("file_limit", FILE_LIMITE)
            if settings.get("filelock", LIMIT_MODE):
                await db.update_files(message.from_user.id, "files_count", files_counts + 1)
                files_count=await db.files_count(message.from_user.id, "files_count")
                f_caption += f"<b>\n\nDᴀɪʟʏ Fɪʟᴇ Lɪᴍɪᴛ: {files_count}/{limit}</b>"      
                if files_counts is not None and files_counts >= limit:
                    buttons = [[
                               InlineKeyboardButton('✨ Rᴇᴍᴏᴠᴇ Lɪᴍɪᴛᴇ ✨', callback_data=f'premium_info')
                              ]]
                    reply_markup = InlineKeyboardMarkup(buttons)
                    return await message.reply_text(script.FILE_LIMIT,
                    reply_markup=reply_markup)
        button = [[
            InlineKeyboardButton("🖥️ ᴡᴀᴛᴄʜ / ᴅᴏᴡɴʟᴏᴀᴅ 📥", callback_data=f"streaming#{file_id}#{grp_id}")
            ]]
        reply_markup=InlineKeyboardMarkup(button)
        msg=await client.send_cached_media(
            chat_id=message.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if pre == 'filep' else False,
            reply_markup=reply_markup
        )
        if await db.get_setting("AUTO_FILE_DELETE", default=AUTO_FILE_DELETE):
            del_msg=await message.reply("<b>⚠️ᴛʜɪs ғɪʟᴇ ᴡɪʟʟ ʙᴇ ᴅᴇʟᴇᴛᴇᴅ ᴀғᴛᴇʀ 10 ᴍɪɴᴜᴛᴇs\n\nᴘʟᴇᴀsᴇ ғᴏʀᴡᴀʀᴅ ᴛʜᴇ ғɪʟᴇ sᴏᴍᴇᴡʜᴇʀᴇ ʙᴇғᴏʀᴇ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ..</b>") 
            safari = msg
            await asyncio.sleep(900)
            await safari.delete() 
            await del_msg.edit_text("<b>ʏᴏᴜʀ ғɪʟᴇ ᴡᴀs ᴅᴇʟᴇᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ᴀғᴛᴇʀ 10 ᴍɪɴᴜᴛᴇs ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ 📢</b>")
    except Exception as e:
        await message.reply(f"{e}")
        
@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info(bot, message):
           
    """Send basic information of channel"""
    if isinstance(CHANNELS, (int, str)):
        channels = [CHANNELS]
    elif isinstance(CHANNELS, list):
        channels = CHANNELS
    else:
        raise ValueError("Uɴᴇxᴘᴇᴄᴛᴇᴅ ᴛʏᴘᴇ ᴏғ CHANNELS")

    text = '📑 **Iɴᴅᴇxᴇᴅ ᴄʜᴀɴɴᴇʟs/ɢʀᴏᴜᴘs**\n'
    for channel in channels:
        chat = await bot.get_chat(channel)
        if chat.username:
            text += '\n@' + chat.username
        else:
            text += '\n' + chat.title or chat.first_name

    text += f'\n\n**Total:** {len(CHANNELS)}'

    if len(text) < 4096:
        await message.reply(text)
    else:
        file = 'Indexed channels.txt'
        with open(file, 'w') as f:
            f.write(text)
        await message.reply_document(file)
        os.remove(file)


@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    """Send log file"""
    try:
        await message.reply_document('Logs.txt')
    except Exception as e:
        await message.reply(str(e))

@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("Pʀᴏᴄᴇssɪɴɢ...⏳", quote=True)
    else:
        await message.reply('Rᴇᴘʟʏ ᴛᴏ ғɪʟᴇ ᴡɪᴛʜ /delete ᴡʜɪᴄʜ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴇʟᴇᴛᴇ', quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('Tʜɪs ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ғɪʟᴇ ғᴏʀᴍᴀᴛ')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)

    result = await Media.collection.delete_one({
        '_id': file_id,
    })
    if result.deleted_count:
        await msg.edit('Fɪʟᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ')
    else:
        file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
        result = await Media.collection.delete_many({
            'file_name': file_name,
            'file_size': media.file_size,
            'mime_type': media.mime_type
            })
        if result.deleted_count:
            await msg.edit('Fɪʟᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ')
        else:
            # files indexed before https://github.com/EvamariaTG/EvaMaria/commit/f3d2a1bcb155faf44178e5d7a685a1b533e714bf#diff-86b613edf1748372103e94cacff3b578b36b698ef9c16817bb98fe9ef22fb669R39 
            # have original file name.
            result = await Media.collection.delete_many({
                'file_name': media.file_name,
                'file_size': media.file_size,
                'mime_type': media.mime_type
            })
            if result.deleted_count:
                await msg.edit('Fɪʟᴇ ɪs sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ғʀᴏᴍ ᴅᴀᴛᴀʙᴀsᴇ')
            else:
                await msg.edit('Fɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ ɪɴ ᴅᴀᴛᴀʙᴀsᴇ')


@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text(
        'Tʜɪs ᴡɪʟʟ ᴅᴇʟᴇᴛᴇ ᴀʟʟ ɪɴᴅᴇxᴇᴅ ғɪʟᴇs.\nDᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ?',
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Yᴇs", callback_data="autofilter_delete"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Cᴀɴᴄᴇʟ", callback_data="close_data"
                    )
                ],
            ]
        ),
        quote=True,
    )


@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm(bot, message):
    await Media.collection.drop()
    await message.answer("Eᴠᴇʀʏᴛʜɪɴɢ's Gᴏɴᴇ")
    await message.message.edit('Sᴜᴄᴄᴇsғᴜʟʟʏ Dᴇʟᴇᴛᴇᴅ Aʟʟ Tʜᴇ Iɴᴅᴇxᴇᴅ Fɪʟᴇs.')


@Client.on_message(filters.command('settings'))
async def settings(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"Yᴏᴜ ᴀʀᴇ ᴀɴᴏɴʏᴍᴏᴜs ᴀᴅᴍɪɴ. Usᴇ /connect {message.chat.id} ɪɴ PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Mᴀᴋᴇ sᴜʀᴇ I'ᴍ ᴘʀᴇsᴇɴᴛ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ !", quote=True)
                return
        else:
            await message.reply_text("I'ᴍ ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴀɴʏ ɢʀᴏᴜᴘs !", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return
    
    settings = await get_settings(grp_id)

    try:
        if settings['max_btn']:
            settings = await get_settings(grp_id)
    except KeyError:
        await save_group_settings(grp_id, 'max_btn', False)
        settings = await get_settings(grp_id)
    else:
        pass

    if settings is not None:
        buttons = [
            [
                InlineKeyboardButton('Rᴇꜱᴜʟᴛ Pᴀɢᴇ', callback_data=f'setgs#button#{settings["button"]}#{grp_id}',),
                InlineKeyboardButton('Tᴇxᴛ' if settings["button"] else 'Bᴜᴛᴛᴏɴ', callback_data=f'setgs#button#{settings["button"]}#{grp_id}',),
            ],
            [
                InlineKeyboardButton('Iᴍᴅʙ', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',),
                InlineKeyboardButton('✔ Oɴ' if settings["imdb"] else '✘ Oғғ',callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',),
            ],
            [
                InlineKeyboardButton('Sᴘᴇʟʟ Cʜᴇᴄᴋ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',),
                InlineKeyboardButton('✔ Oɴ' if settings["spell_check"] else '✘ Oғғ', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',),
            ],
            [
                InlineKeyboardButton('Wᴇʟᴄᴏᴍᴇ Msɢ', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',),
                InlineKeyboardButton('✔ Oɴ' if settings["welcome"] else '✘ Oғғ',callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',),
            ],
            [
                InlineKeyboardButton('Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',),
                InlineKeyboardButton('10 Mɪɴs' if settings["auto_delete"] else '✘ Oғғ', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}',),
            ],
            [
                InlineKeyboardButton('Aᴜᴛᴏ-Fɪʟᴛᴇʀ', callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{grp_id}',),
                InlineKeyboardButton('✔ 𝕋𝕣𝕦𝕖' if settings["auto_ffilter"] else '✘ 𝔽𝕒𝕝𝕤𝕖', callback_data=f'setgs#auto_ffilter#{settings["auto_ffilter"]}#{grp_id}',),
            ],
            [
                InlineKeyboardButton('Mᴀx Bᴜᴛᴛᴏɴs', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{grp_id}',),
                InlineKeyboardButton('10' if settings["max_btn"] else f'{MAX_B_TN}', callback_data=f'setgs#max_btn#{settings["max_btn"]}#{grp_id}',),
            ],
            [
                InlineKeyboardButton('Fɪʟᴇ Lɪᴍɪᴛ', callback_data=f'setgs#filelock#{settings.get("filelock", LIMIT_MODE)}#{grp_id}'),
                InlineKeyboardButton('✔ Oɴ' if settings.get("filelock", LIMIT_MODE) else '✘ Oғғ', callback_data=f'setgs#filelock#{settings.get("filelock", LIMIT_MODE)}#{grp_id}'),
            ], 
            [
                InlineKeyboardButton('Sᴛʀᴇᴀᴍ Sʜᴏʀᴛ', callback_data=f'setgs#stream_mode#{settings.get("stream_mode", STREAM_MODE)}#{grp_id}'),
                InlineKeyboardButton('✔ Oɴ' if settings.get("stream_mode", STREAM_MODE) else '✘ Oғғ', callback_data=f'setgs#stream_mode#{settings.get("stream_mode", STREAM_MODE)}#{grp_id}'),
            ], 
            [
                InlineKeyboardButton('Vᴇʀɪғʏ', callback_data=f'setgs#is_verify#{settings.get("is_verify", IS_VERIFY)}#{grp_id}'),
                InlineKeyboardButton('✔ Oɴ' if settings.get("is_verify", IS_VERIFY) else '✘ Oғғ', callback_data=f'setgs#is_verify#{settings.get("is_verify", IS_VERIFY)}#{grp_id}'),
            ],
        ]
        btn = [[
                InlineKeyboardButton("Oᴘᴇɴ Hᴇʀᴇ ↓", callback_data=f"opnsetgrp#{grp_id}"),
                InlineKeyboardButton("Oᴘᴇɴ Iɴ PM ⇲", callback_data=f"opnsetpm#{grp_id}")
              ]]

        reply_markup = InlineKeyboardMarkup(buttons)
        if chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await message.reply_text(
                text="<b>Dᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴏᴘᴇɴ sᴇᴛᴛɪɴɢs ʜᴇʀᴇ ?</b>",
                reply_markup=InlineKeyboardMarkup(btn),
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=message.id
            )
        else:
            await message.reply_text(
                text=f"<b>Cʜᴀɴɢᴇ Yᴏᴜʀ Sᴇᴛᴛɪɴɢs Fᴏʀ {title} As Yᴏᴜʀ Wɪsʜ ⚙</b>",
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=message.id
            )

  
@Client.on_message(filters.command('set_tutorial')) 
async def set_tutorial_1(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text(f"<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...\n\nGroup Name: {title}\nGroup ID: {grp_id}\nGroup Invite Link: {invite_link}</b>")
    try:
        tutorial = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("<b>Command Incomplete!!\n\nuse like this -</b>\n\n<code>/set_tutorial https://t.me/safaribotts</code>")
    await save_group_settings(grp_id, 'tutorial', tutorial)
    await message.reply_text(f"<b>Successfully changed tutorial for {title}</b>\n\nLink - {tutorial}", disable_web_page_preview=True)
    await client.send_message(LOG_CHANNEL, f"Tutorial for {title} (Group ID: {grp_id}, Invite Link: {invite_link}) has been updated by {message.from_user.username}")

@Client.on_message(filters.command('set_tutorial_2'))
async def set_tutorial_2(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    try:
        tutorial = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("<b>Command Incomplete!!\n\nuse like this -</b>\n\n<code>/set_tutorial https://t.me/safaribotts</code>")
    await save_group_settings(grp_id, 'tutorial2', tutorial)
    await message.reply_text(f"<b>Successfully changed tutorial for {title}</b>\n\nLink - {tutorial}", disable_web_page_preview=True)
    await client.send_message(LOG_CHANNEL, f"Tutorial 2 for {title} (Group ID: {grp_id}, Invite Link: {invite_link}) has been updated by {message.from_user.username}")

@Client.on_message(filters.command('set_tutorial_3'))
async def set_tutorial_3(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    try:
        tutorial = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("<b>Command Incomplete!!\n\nuse like this -</b>\n\n<code>/set_tutorial https://t.me/safaribotts</code>")
    await save_group_settings(grp_id, 'tutorial3', tutorial)
    await message.reply_text(f"<b>Successfully changed tutorial for {title}</b>\n\nLink - {tutorial}", disable_web_page_preview=True)
    await client.send_message(LOG_CHANNEL, f"Tutorial 2 for {title} (Group ID: {grp_id}, Invite Link: {invite_link}) has been updated by {message.from_user.username}")

@Client.on_message(filters.command('set_verify'))
async def set_verify(c, m):
    chat_type = m.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = m.chat.id
    title = m.chat.title
    user = await c.get_chat_member(m.chat.id, m.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await m.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')        
    if len(m.text.split()) == 1:
        await m.reply("<b>Use this command like this - \n\n`/set_shortner ziplinker.net c992d5c6d3a74f6ceccbf9bc34aa27c8487c11d2`</b>")
        return        
    sts = await m.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    try:
        URL = m.command[1]
        API = m.command[2]
        resp = requests.get(f'https://{URL}/api?api={API}&url=https://telegram.dog/SafariBotts').json()
        if resp['status'] == 'success':
            SHORT_LINK = resp['shortenedUrl']
        await save_group_settings(grp_id, 'verify', URL)
        await save_group_settings(grp_id, 'verify_api', API)
        await sts.edit(f"<b><u>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ʏᴏᴜʀ sʜᴏʀᴛɴᴇʀ ɪs ᴀᴅᴅᴇᴅ</u>\n\nᴅᴇᴍᴏ - {SHORT_LINK}\n\nsɪᴛᴇ - `{URL}`\n\nᴀᴘɪ - `{API}`</b>")
        user_id = m.from_user.id
        user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
        link = (await c.get_chat(m.chat.id)).invite_link
        grp_link = f"[{m.chat.title}]({link})"
        log_message = f"#New_Shortner_Set_For_1st_Verify\n\nName - {user_info}\nId - `{user_id}`\n\nDomain name - {URL}\nApi - `{API}`\nGroup link - {grp_link}   `{grp_id}`"
        await c.send_message(LOG_CHANNEL, log_message, disable_web_page_preview=True)
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        await save_group_settings(grp_id, 'verify', VERIFY_URL)
        await save_group_settings(grp_id, 'verify_api', VERIFY_API)
        await sts.edit(f"<b><u>❌ ᴇʀʀᴏʀ ᴏᴄᴄᴏᴜʀᴇᴅ ❌</u>\n\nᴀᴜᴛᴏ ᴀᴅᴅᴇᴅ ᴅᴇꜰᴜʟᴛ sʜᴏʀᴛɴᴇʀ\n\nɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ ᴛʜᴇɴ ᴜsᴇ ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ ᴏʀ ᴀᴅᴅ ᴠᴀʟɪᴅ sʜᴏʀᴛʟɪɴᴋ ᴅᴏᴍᴀɪɴ ɴᴀᴍᴇ & ᴀᴘɪ\n\nʏᴏᴜ ᴄᴀɴ ᴀʟsᴏ ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ <a href=https://t.me/safarisuport>sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ</a> ꜰᴏʀ sᴏʟᴠᴇ ᴛʜɪs ɪssᴜᴇ...\n\nʟɪᴋᴇ -\n\n`/set_verify droplink.co 5c6377b71bb8c36629bad14b3c67d9749c4f62e6`\n\n💔 ᴇʀʀᴏʀ - <code>{e}</code></b>")

@Client.on_message(filters.command('set_verify2'))
async def set_verify2(c, m):
    chat_type = m.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = m.chat.id
    title = m.chat.title
    user = await c.get_chat_member(m.chat.id, m.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await m.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    if len(m.text.split()) == 1:
        await m.reply("<b>Use this command like this - \n\n`/set_shortner_2 tnshort.net 06b24eb6bbb025713cd522fb3f696b6d5de11354`</b>")
        return
    sts = await m.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    try:
        URL = m.command[1]
        API = m.command[2]
        resp = requests.get(f'https://{URL}/api?api={API}&url=https://telegram.dog/SafariBotts').json()
        if resp['status'] == 'success':
            SHORT_LINK = resp['shortenedUrl']
        await save_group_settings(grp_id, 'verify_2', URL)
        await save_group_settings(grp_id, 'verify_api2', API)
        await sts.edit(f"<b><u>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ʏᴏᴜʀ sʜᴏʀᴛɴᴇʀ ɪs ᴀᴅᴅᴇᴅ</u>\n\nᴅᴇᴍᴏ - {SHORT_LINK}\n\nsɪᴛᴇ - `{URL}`\n\nᴀᴘɪ - `{API}`</b>")
        user_id = m.from_user.id
        user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
        link = (await c.get_chat(m.chat.id)).invite_link
        grp_link = f"[{m.chat.title}]({link})"
        log_message = f"#New_Shortner_Set_For_2nd_Verify\n\nName - {user_info}\nId - `{user_id}`\n\nDomain name - {URL}\nApi - `{API}`\nGroup link - {grp_link}   `{grp_id}`"
        await c.send_message(LOG_CHANNEL, log_message, disable_web_page_preview=True)
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        await save_group_settings(grp_id, 'verify_2', VERIFY_URL2)
        await save_group_settings(grp_id, 'verify_api2', VERIFY_API2)
        await sts.edit(f"<b><u>❌ ᴇʀʀᴏʀ ᴏᴄᴄᴏᴜʀᴇᴅ ❌</u>\n\nᴀᴜᴛᴏ ᴀᴅᴅᴇᴅ ᴅᴇꜰᴜʟᴛ sʜᴏʀᴛɴᴇʀ\n\nɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ ᴛʜᴇɴ ᴜsᴇ ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ ᴏʀ ᴀᴅᴅ ᴠᴀʟɪᴅ sʜᴏʀᴛʟɪɴᴋ ᴅᴏᴍᴀɪɴ ɴᴀᴍᴇ & ᴀᴘɪ\n\nʏᴏᴜ ᴄᴀɴ ᴀʟsᴏ ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ <a href=https://t.me/safarisuport>sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ</a> ꜰᴏʀ sᴏʟᴠᴇ ᴛʜɪs ɪssᴜᴇ...\n\nʟɪᴋᴇ -\n\n`/set_verify2 shortyfi.link 465d89bf8d7b71277a822b890f7cc3e2489acf73`\n\n💔 ᴇʀʀᴏʀ - <code>{e}</code></b>")

@Client.on_message(filters.command('set_verify3'))
async def set_verify3(c, m):
    chat_type = m.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = m.chat.id
    title = m.chat.title
    user = await c.get_chat_member(m.chat.id, m.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await m.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    if len(m.text.split()) == 1:
        await m.reply("<b>Use this command like this - \n\n`/set_shortner_2 tnshort.net 06b24eb6bbb025713cd522fb3f696b6d5de11354`</b>")
        return
    sts = await m.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    try:
        URL = m.command[1]
        API = m.command[2]
        resp = requests.get(f'https://{URL}/api?api={API}&url=https://telegram.dog/SafariBotts').json()
        if resp['status'] == 'success':
            SHORT_LINK = resp['shortenedUrl']
        await save_group_settings(grp_id, 'verify_3', URL)
        await save_group_settings(grp_id, 'verify_api3', API)
        await sts.edit(f"<b><u>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ʏᴏᴜʀ sʜᴏʀᴛɴᴇʀ ɪs ᴀᴅᴅᴇᴅ</u>\n\nᴅᴇᴍᴏ - {SHORT_LINK}\n\nsɪᴛᴇ - `{URL}`\n\nᴀᴘɪ - `{API}`</b>")
        user_id = m.from_user.id
        user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
        link = (await c.get_chat(m.chat.id)).invite_link
        grp_link = f"[{m.chat.title}]({link})"
        log_message = f"#New_Shortner_Set_For_3nd_Verify\n\nName - {user_info}\nId - `{user_id}`\n\nDomain name - {URL}\nApi - `{API}`\nGroup link - {grp_link}   `{grp_id}`"
        await c.send_message(LOG_CHANNEL, log_message, disable_web_page_preview=True)
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        await save_group_settings(grp_id, 'verify_3', VERIFY_URL3)
        await save_group_settings(grp_id, 'verify_api3', VERIFY_API3)
        await sts.edit(f"<b><u>❌ ᴇʀʀᴏʀ ᴏᴄᴄᴏᴜʀᴇᴅ ❌</u>\n\nᴀᴜᴛᴏ ᴀᴅᴅᴇᴅ ᴅᴇꜰᴜʟᴛ sʜᴏʀᴛɴᴇʀ\n\nɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ ᴛʜᴇɴ ᴜsᴇ ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ ᴏʀ ᴀᴅᴅ ᴠᴀʟɪᴅ sʜᴏʀᴛʟɪɴᴋ ᴅᴏᴍᴀɪɴ ɴᴀᴍᴇ & ᴀᴘɪ\n\nʏᴏᴜ ᴄᴀɴ ᴀʟsᴏ ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ <a href=https://t.me/safarisuport>sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ</a> ꜰᴏʀ sᴏʟᴠᴇ ᴛʜɪs ɪssᴜᴇ...\n\nʟɪᴋᴇ -\n\n`/set_verify3 sharedisklinks.com 587f94f0e0b1813a52aed61290af6ea79d6ee464`\n\n💔 ᴇʀʀᴏʀ - <code>{e}</code></b>")

@Client.on_message(filters.command('set_stream'))
async def set_stream(c, m):
    chat_type = m.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await m.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = m.chat.id
    title = m.chat.title
    user = await c.get_chat_member(m.chat.id, m.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await m.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    if len(m.text.split()) == 1:
        await m.reply("<b>Use this command like this - \n\n`/set_stream tnshort.net 06b24eb6bbb025713cd522fb3f696b6d5de11354`</b>")
        return
    sts = await m.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    try:
        URL = m.command[1]
        API = m.command[2]
        resp = requests.get(f'https://{URL}/api?api={API}&url=https://telegram.dog/MzBotz').json()
        if resp['status'] == 'success':
            SHORT_LINK = resp['shortenedUrl']
        await save_group_settings(grp_id, 'streamsite', URL)
        await save_group_settings(grp_id, 'streamapi', API)
        await sts.edit(f"<b><u>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ ʏᴏᴜʀ sʜᴏʀᴛɴᴇʀ ɪs ᴀᴅᴅᴇᴅ</u>\n\nᴅᴇᴍᴏ - {SHORT_LINK}\n\nsɪᴛᴇ - `{URL}`\n\nᴀᴘɪ - `{API}`</b>")
        user_id = m.from_user.id
        user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
        link = (await c.get_chat(m.chat.id)).invite_link
        grp_link = f"[{m.chat.title}]({link})"
        log_message = f"#New_Stream_link_set\n\nName - {user_info}\nId - `{user_id}`\n\nDomain name - {URL}\nApi - `{API}`\nGroup link - {grp_link}   `{grp_id}`"
        await c.send_message(LOG_CHANNEL, log_message, disable_web_page_preview=True)
    except Exception as e:
        await save_group_settings(grp_id, 'streamsite', STREAM_SITE)
        await save_group_settings(grp_id, 'streamapi', STREAM_API)
        await sts.edit(f"<b><u>❌ ᴇʀʀᴏʀ ᴏᴄᴄᴏᴜʀᴇᴅ ❌</u>\n\nᴀᴜᴛᴏ ᴀᴅᴅᴇᴅ ᴅᴇꜰᴜʟᴛ sʜᴏʀᴛɴᴇʀ\n\nɪꜰ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄʜᴀɴɢᴇ ᴛʜᴇɴ ᴜsᴇ ᴄᴏʀʀᴇᴄᴛ ꜰᴏʀᴍᴀᴛ ᴏʀ ᴀᴅᴅ ᴠᴀʟɪᴅ sʜᴏʀᴛʟɪɴᴋ ᴅᴏᴍᴀɪɴ ɴᴀᴍᴇ & ᴀᴘɪ\n\nʏᴏᴜ ᴄᴀɴ ᴀʟsᴏ ᴄᴏɴᴛᴀᴄᴛ ᴏᴜʀ <a href=https://t.me/mzbotzsupport>sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ</a> ꜰᴏʀ sᴏʟᴠᴇ ᴛʜɪs ɪssᴜᴇ...\n\nʟɪᴋᴇ -\n\n`/set_stream sharedisklinks.com 587f94f0e0b1813a52aed61290af6ea79d6ee464`\n\n💔 ᴇʀʀᴏʀ - <code>{e}</code></b>")
           
@Client.on_message(filters.command('set_caption'))
async def save_caption(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    try:
        caption = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("<code>ɢɪᴠᴇ ᴍᴇ ᴀ ᴄᴀᴘᴛɪᴏɴ ᴀʟᴏɴɢ ᴡɪᴛʜ ɪᴛ.\n\nᴇxᴀᴍᴘʟᴇ -\n\nꜰᴏʀ ꜰɪʟᴇ ɴᴀᴍᴇ ꜱᴇɴᴅ <code>{file_name}</code>\nꜰᴏʀ ꜰɪʟᴇ ꜱɪᴢᴇ ꜱᴇɴᴅ <code>{file_size}</code>\n\n<code>/set_caption {file_name}</code></code>")
    await save_group_settings(grp_id, 'caption', caption)
    await message.reply_text(f"Successfully changed caption for {title}\n\nCaption - {caption}", disable_web_page_preview=True)
    await client.send_message(LOG_CHANNEL, f"Caption for {title} (Group ID: {grp_id}, Invite Link: {invite_link}) has been updated by {message.from_user.username}")

@Client.on_message(filters.command('set_fsub'))
async def set_fsub(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    try:
        channel_id = int(message.text.split(" ", 1)[1])
    except IndexError:
        return await message.reply_text("<b>ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ\n\nꜱᴇɴᴅ ᴍᴇ ᴄʜᴀɴɴᴇʟ ɪᴅ ᴡɪᴛʜ ᴄᴏᴍᴍᴀɴᴅ, ʟɪᴋᴇ <code>/set_fsub -100******</code></b>")
    except ValueError:
        return await message.reply_text('<b>ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴛʜᴇ ɪᴅ ɪꜱ ᴀɴ ɪɴᴛᴇɢᴇʀ.</b>')
    try:
        chat = await client.get_chat(channel_id)
    except Exception as e:
        return await message.reply_text(f"<b><code>{channel_id}</code> ɪꜱ ɪɴᴠᴀʟɪᴅ. ᴍᴀᴋᴇ ꜱᴜʀᴇ <a href=https://t.me/{temp.B_LINK} ʙᴏᴛ</a> ɪꜱ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ\n\n<code>{e}</code></b>")
    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply_text(f"🫥 <code>{channel_id}</code> ᴛʜɪꜱ ɪꜱ ɴᴏᴛ ᴄʜᴀɴɴᴇʟ, ꜱᴇɴᴅ ᴍᴇ ᴏɴʟʏ ᴄʜᴀɴɴᴇʟ ɪᴅ ɴᴏᴛ ɢʀᴏᴜᴘ ɪᴅ</b>")
    await save_group_settings(grp_id, 'fsub_id', channel_id)
    mention = message.from_user.mention
    await client.send_message(LOG_CHANNEL, f"#Fsub_Channel_set\n\nUser - {mention} set the force channel for {title}:\n\nFsub channel - {chat.title}\nId - `{channel_id}`")
    await message.reply_text(f"<b>ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ꜱᴇᴛ ꜰᴏʀᴄᴇ ꜱᴜʙꜱᴄʀɪʙᴇ ᴄʜᴀɴɴᴇʟ ꜰᴏʀ {title}\n\nᴄʜᴀɴɴᴇʟ ɴᴀᴍᴇ - {chat.title}\nɪᴅ - <code>{channel_id}</code></b>")

@Client.on_message(filters.command('remove_fsub'))
async def remove_fsub(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")       
    grp_id = message.chat.id
    title = message.chat.title
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    settings = await get_settings(grp_id)
    if settings["fsub_id"] == AUTH_CHANNEL:
        await message.reply_text("<b>ᴄᴜʀʀᴇɴᴛʟʏ ɴᴏ ᴀɴʏ ғᴏʀᴄᴇ ꜱᴜʙ ᴄʜᴀɴɴᴇʟ.... <code>[ᴅᴇғᴀᴜʟᴛ ᴀᴄᴛɪᴠᴀᴛᴇ]</code></b>")
    else:
        await save_group_settings(grp_id, 'fsub_id', AUTH_CHANNEL)
        mention = message.from_user.mention
        await client.send_message(LOG_CHANNEL, f"#Remove_Fsub_Channel\n\nUser - {mention} he remove fsub channel from {title}")
        await message.reply_text(f"<b>✅ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ ʀᴇᴍᴏᴠᴇᴅ ғᴏʀᴄᴇ ꜱᴜʙ ᴄʜᴀɴɴᴇʟ.</b>")         

@Client.on_message(filters.command('set_log'))
async def set_log(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    if len(message.text.split()) == 1:
        await message.reply("<b>Use this command like this - \n\n`/set_log -100******`</b>")
        return
    sts = await message.reply("<b>♻️ ᴄʜᴇᴄᴋɪɴɢ...</b>")
    await asyncio.sleep(1.2)
    await sts.delete()
    try:
        log = int(message.text.split(" ", 1)[1])
    except IndexError:
        return await message.reply_text("<b><u>ɪɴᴠᴀɪʟᴅ ꜰᴏʀᴍᴀᴛ!!</u>\n\nᴜsᴇ ʟɪᴋᴇ ᴛʜɪs - `/set_log -100xxxxxxxx`</b>")
    except ValueError:
        return await message.reply_text('<b>ᴍᴀᴋᴇ sᴜʀᴇ ɪᴅ ɪs ɪɴᴛᴇɢᴇʀ...</b>')
    try:
        t = await client.send_message(chat_id=log, text="<b>ʜᴇʏ ᴡʜᴀᴛ's ᴜᴘ!!</b>")
        await asyncio.sleep(3)
        await t.delete()
    except Exception as e:
        return await message.reply_text(f'<b><u>😐 ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜɪs ʙᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ...</u>\n\n💔 ᴇʀʀᴏʀ - <code>{e}</code></b>')
    await save_group_settings(grp_id, 'log', log)
    await message.reply_text(f"<b>✅ sᴜᴄᴄᴇssꜰᴜʟʟʏ sᴇᴛ ʏᴏᴜʀ ʟᴏɢ ᴄʜᴀɴɴᴇʟ ꜰᴏʀ {title}\n\nɪᴅ - `{log}`</b>", disable_web_page_preview=True)
    user_id = message.from_user.id
    user_info = f"@{m.from_user.username}" if m.from_user.username else f"{m.from_user.mention}"
    link = (await client.get_chat(message.chat.id)).invite_link
    grp_link = f"[{message.chat.title}]({link})"
    log_message = f"#New_Log_Channel_Set\n\nName - {user_info}\nId - `{user_id}`\n\nLog channel id - `{log}`\nGroup link - {grp_link}   `{grp_id}`"
    await client.send_message(LOG_CHANNEL, log_message, disable_web_page_preview=True)  

@Client.on_message(filters.command('details'))
async def all_settings(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    settings = await get_settings(grp_id)
    text = f"""<b><u>⚙️ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ꜰᴏʀ -</u> {title}

<u>✅️ 1sᴛ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ ɴᴀᴍᴇ/ᴀᴘɪ</u>
ɴᴀᴍᴇ - `{settings.get("verify", VERIFY_URL)}`
ᴀᴘɪ - `{settings.get("verify_api", VERIFY_API)}`

<u>✅️ 2ɴᴅ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ ɴᴀᴍᴇ/ᴀᴘɪ</u>
ɴᴀᴍᴇ - `{settings.get("verify_2", VERIFY_URL2)}`
ᴀᴘɪ - `{settings.get("verify_api2", VERIFY_API2)}`

u>✅️ ᴛʜɪʀᴅ ᴠᴇʀɪꜰʏ sʜᴏʀᴛɴᴇʀ ɴᴀᴍᴇ/ᴀᴘɪ</u>
ɴᴀᴍᴇ - `{settings.get("verify_3", VERIFY_URL3)}`
ᴀᴘɪ - `{settings.get("verify_api3", VERIFY_API3)}`

🧭 2ɴᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ ɢᴀᴘ - `{settings.get("verify_time", TWO_VERIFY_GAP)}`

🧭 ᴛʜɪʀᴅ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛɪᴍᴇ ɢᴀᴘ - `{settings.get("verify_time2", THIRD_VERIFY_GAP)}`

📝 ʟᴏɢ ᴄʜᴀɴɴᴇʟ ɪᴅ - `{settings.get('log', LOG_CHANNEL)}`

🌀 ғᴏʀᴄᴇ ᴄʜᴀɴɴᴇʟ - `{settings.get('fsub_id', AUTH_CHANNEL)}`

1️⃣ ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ 1 - {settings.get('tutorial', TUTORIAL)}

2️⃣ ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ 2 - {settings.get('tutorial2', TUTORIAL2)}

3️⃣ ᴛᴜᴛᴏʀɪᴀʟ ʟɪɴᴋ 3 - {settings.get('tutorial3', TUTORIAL3)}

📂 ꜰɪʟᴇ ᴄᴀᴘᴛɪᴏɴ - `{settings.get('caption', CUSTOM_FILE_CAPTION)}`

📁 ᴅᴀɪʟʏ ғɪʟᴇ ʟɪᴍɪᴛ - `{settings.get('file_limit', FILE_LIMITE)}`

📀 sᴇᴅɴ ᴀʟʟ ʙᴜᴛᴛᴏɴ ʟɪᴍɪᴛ - `{settings.get('all_limit', SEND_ALL_LIMITE)}`

🎯 ɪᴍᴅʙ ᴛᴇᴍᴘʟᴀᴛᴇ - `{settings.get('template', IMDB_TEMPLATE)}`"""

    
    btn = [[
        InlineKeyboardButton("ʀᴇꜱᴇᴛ ᴅᴀᴛᴀ", callback_data="reset_grp_data")
    ],[
        InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close_data")
    ]]
    reply_markup=InlineKeyboardMarkup(btn)
    dlt=await message.reply_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
    await asyncio.sleep(300)
    await dlt.delete()

@Client.on_message(filters.command('verify_gap'))
async def verify_gap(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")       
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    try:
        time = int(message.text.split(" ", 1)[1])
    except:
        return await message.reply_text("<b>ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ\n\nᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ʟɪᴋᴇ ᴛʜɪꜱ - <code>/verify_gap 600</code> [ ᴛɪᴍᴇ ᴍᴜꜱᴛ ʙᴇ ɪɴ ꜱᴇᴄᴏɴᴅꜱ ]</b>")   
    await save_group_settings(grp_id, 'verify_time', time)
    await message.reply_text(f"<b>✅️ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ꜱᴇᴛ 2ɴᴅ ᴠᴇʀɪꜰʏ ᴛɪᴍᴇ ꜰᴏʀ {title}\n\nᴛɪᴍᴇ - <code>{time}</code></b>")
    await client.send_message(LOG_CHANNEL, f"2nd verify time for {title} (Group ID: {grp_id}, Invite Link: {invite_link}) has been updated by {message.from_user.username}")

@Client.on_message(filters.command('verify_gap2'))
async def verify_gap2(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")       
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    try:
        time = int(message.text.split(" ", 1)[1])
    except:
        return await message.reply_text("<b>ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ\n\nᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ʟɪᴋᴇ ᴛʜɪꜱ - <code>/verify_gap2 600</code> [ ᴛɪᴍᴇ ᴍᴜꜱᴛ ʙᴇ ɪɴ ꜱᴇᴄᴏɴᴅꜱ ]</b>")   
    await save_group_settings(grp_id, 'verify_time2', time)
    await message.reply_text(f"<b>✅️ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ꜱᴇᴛ ᴛʜɪʀᴅ ᴠᴇʀɪꜰʏ ᴛɪᴍᴇ ꜰᴏʀ {title}\n\nᴛɪᴍᴇ - <code>{time}</code></b>")
    await client.send_message(LOG_CHANNEL, f"third verify time for {title} (Group ID: {grp_id}, Invite Link: {invite_link}) has been updated by {message.from_user.username}")


@Client.on_message(filters.command('set_file_limit'))
async def set_file_limit(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")       
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    try:
        limit = int(message.text.split(" ", 1)[1])
    except:
        return await message.reply_text("<b>ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ\n\nᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ʟɪᴋᴇ ᴛʜɪꜱ - <code>/set_file_limit 15</code></b>")   
    await save_group_settings(grp_id, 'file_limit', limit)
    await message.reply_text(f"<b>✅️ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ꜱᴇᴛ ғɪʟᴇ ʟɪᴍɪᴛ ꜰᴏʀ {title}\n\nғɪʟᴇ ʟɪᴍɪᴛ - <u><code>{limit}</code></u></b>")
    await client.send_message(LOG_CHANNEL, f"file limit seted <b>`{limit}`</b> for {title} (Group ID: {grp_id}, Invite Link: {invite_link}) has been updated by {message.from_user.username}")

@Client.on_message(filters.command('set_send_limit'))
async def set_send_limit(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")       
    grp_id = message.chat.id
    title = message.chat.title
    invite_link = await client.export_chat_invite_link(grp_id)
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    try:
        limit = int(message.text.split(" ", 1)[1])
    except:
        return await message.reply_text("<b>ᴄᴏᴍᴍᴀɴᴅ ɪɴᴄᴏᴍᴘʟᴇᴛᴇ\n\nᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ʟɪᴋᴇ ᴛʜɪꜱ - <code>/set_allfiles_limit 3</code></b>")   
    await save_group_settings(grp_id, 'all_limit', limit)
    await message.reply_text(f"<b>✅️ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ꜱᴇᴛ sᴇɴᴅ ʙᴜᴛᴛᴏɴ ʟɪᴍɪᴛ ꜰᴏʀ {title}\n\nsᴇɴᴅ ʙᴜᴛᴛᴏɴ ʟɪᴍɪᴛ - <u><code>{limit}</code></u></b>")
    await client.send_message(LOG_CHANNEL, f"send button limit seted <b>`{limit}`</b> for {title} (Group ID: {grp_id}, Invite Link: {invite_link}) has been updated by {message.from_user.username}")

@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    chat_type = message.chat.type
    if chat_type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        return await message.reply_text("<b>ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ɪɴ ɢʀᴏᴜᴘ...</b>")
    grp_id = message.chat.id
    title = message.chat.title
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    owner=user.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(message.from_user.id) in ADMINS
    if not owner:
        return await message.reply_text('<b>ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ ɪɴ ᴛʜɪꜱ ɢʀᴏᴜᴘ</b>')
    try:
        template = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text("Command Incomplete!")    
    await save_group_settings(grp_id, 'template', template)
    await message.reply_text(f"Successfully changed template for {title} to\n\n{template}", disable_web_page_preview=True)
    
@Client.on_message(filters.command('del_template'))
async def delete_template(client, message):
    sts = await message.reply("Dᴇʟᴇᴛɪɴɢ ᴛᴇᴍᴘʟᴀᴛᴇ...")
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"Yᴏᴜ ᴀʀᴇ ᴀɴᴏɴʏᴍᴏᴜs ᴀᴅᴍɪɴ. Usᴇ /connect {message.chat.id} ɪɴ PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Mᴀᴋᴇ sᴜʀᴇ I'ᴍ ᴘʀᴇsᴇɴᴛ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ!!", quote=True)
                return
        else:
            await message.reply_text("I'ᴍ ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴀɴʏ ɢʀᴏᴜᴘs!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return

    # Reset the template to the default or remove it
    await save_group_settings(grp_id, 'template', IMDB_TEMPLATE)
    await sts.edit(f"Sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴛᴇᴍᴘʟᴀᴛᴇ ғᴏʀ {title}.")

@Client.on_message(filters.command("send") & filters.user(ADMINS))
async def send_msg(bot, message):
    if message.reply_to_message:
        target_id = message.text.split(" ", 1)[1]
        out = "Usᴇʀs Sᴀᴠᴇᴅ Iɴ DB Aʀᴇ:\n\n"
        success = False
        try:
            user = await bot.get_users(target_id)
            users = await db.get_all_users()
            async for usr in users:
                out += f"{usr['id']}"
                out += '\n'
            if str(user.id) in str(out):
                await message.reply_to_message.copy(int(user.id))
                success = True
            else:
                success = False
            if success:
                await message.reply_text(f"<b>Yᴏᴜʀ ᴍᴇssᴀɢᴇ ʜᴀs ʙᴇᴇɴ sᴜᴄᴄᴇssғᴜʟʟʏ sᴇɴᴅ ᴛᴏ {user.mention}.</b>")
            else:
                await message.reply_text("<b>Tʜɪs ᴜsᴇʀ ᴅɪᴅɴ'ᴛ sᴛᴀʀᴛᴇᴅ ᴛʜɪs ʙᴏᴛ ʏᴇᴛ!</b>")
        except Exception as e:
            await message.reply_text(f"<b>Eʀʀᴏʀ: {e}</b>")
    else:
        await message.reply_text("<b>Usᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴀs ᴀ ʀᴇᴘʟʏ ᴛᴏ ᴀɴʏ ᴍᴇssᴀɢᴇ ᴜsɪɴɢ ᴛʜᴇ ᴛᴀʀɢᴇᴛ ᴄʜᴀᴛ ɪᴅ. Fᴏʀ ᴇɢ: /send ᴜsᴇʀɪᴅ</b>")

@Client.on_message(filters.command("deletefiles") & filters.user(ADMINS))
async def deletemultiplefiles(bot, message):
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hᴇʏ {message.from_user.mention}, Tʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴡᴏɴ'ᴛ ᴡᴏʀᴋ ɪɴ ɢʀᴏᴜᴘs. Iᴛ ᴏɴʟʏ ᴡᴏʀᴋs ᴏɴ ᴍʏ PM!</b>")
    else:
        pass
    try:
        keyword = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text(f"<b>Hᴇʏ {message.from_user.mention}, Gɪᴠᴇ ᴍᴇ ᴀ ᴋᴇʏᴡᴏʀᴅ ᴀʟᴏɴɢ ᴡɪᴛʜ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ ᴛᴏ ᴅᴇʟᴇᴛᴇ ғɪʟᴇs.</b>")
    btn = [[
       InlineKeyboardButton("Yᴇs, Cᴏɴᴛɪɴᴜᴇ !", callback_data=f"killfilesdq#{keyword}")
       ],[
       InlineKeyboardButton("Nᴏ, Aʙᴏʀᴛ ᴏᴘᴇʀᴀᴛɪᴏɴ !", callback_data="close_data")
    ]]
    await message.reply_text(
        text="<b>Aʀᴇ ʏᴏᴜ sᴜʀᴇ? Dᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ?\n\nNᴏᴛᴇ:- Tʜɪs ᴄᴏᴜʟᴅ ʙᴇ ᴀ ᴅᴇsᴛʀᴜᴄᴛɪᴠᴇ ᴀᴄᴛɪᴏɴ!</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        parse_mode=enums.ParseMode.HTML
    )

@Client.on_message(filters.command("restart") & filters.user(ADMINS))
async def stop_button(bot, message):
    msg = await bot.send_message(text="<b><i>ʙᴏᴛ ɪꜱ ʀᴇꜱᴛᴀʀᴛɪɴɢ</i></b>", chat_id=message.chat.id)       
    await asyncio.sleep(3)
    await msg.edit("<b><i><u>ʙᴏᴛ ɪꜱ ʀᴇꜱᴛᴀʀᴛᴇᴅ</u> ✅</i></b>")
    os.execl(sys.executable, sys.executable, *sys.argv)

@Client.on_message(filters.command("set_value") & filters.user(ADMINS))
async def set_mode(client, message):
    try:
        args = message.text.split()   
        if len(args) == 3:
            mode_name = args[1]
            value = args[2].lower() == 'true'  # Convert string to boolean     
            valid_modes = ["PM_FILTER", "IS_VERIFY", "LIMIT_MODE", "AUTO_FILE_DELETE"]  
            if mode_name in valid_modes:
                await db.set_setting(mode_name, value)
                await message.reply(f"{mode_name} has been set to {value}.")
            else:
                await message.reply("Invalid mode name. Please use one of the following:\n\nPM_FILTER\n\nIS_VERIFY\nLIMIT_MODE\nAUTO_FILE_DELETE")
        else:
            await message.reply("Please specify the mode name and 'True' or 'False' as arguments. Example: /set_value PM_FILTER True")
    except Exception as e:
        await message.reply(f"An error occurred: {e}")
