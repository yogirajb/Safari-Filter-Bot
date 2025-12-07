# This code has been modified by @Safaridev
# Please do not remove this credit
from fuzzywuzzy import process
from imdb import IMDb
from utils import temp
from info import REQ_CHANNEL, GRP_LNK
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import get_search_results, get_all_files


async def ai_spell_check(chat_id, wrong_name):
    """
    TMDb based simple AI spell check:
    - utils.ai_fix_query se sahi title/saal nikalta hai
    - fir us title se DB me files search karta hai
    - agar files mil gayi to corrected name return karta hai
    """
    try:
        fixed = ai_fix_query(wrong_name)
        if not fixed or fixed.lower() == wrong_name.lower():
            return None

        files, offset, total_results = await get_search_results(
            chat_id=chat_id,
            query=fixed
        )

        if files:
            return fixed

        return None

    except Exception as e:
        print(f"Error in ai_spell_check: {e}")
        return None

@Client.on_message(
    filters.command(["request", "Request"]) & filters.private
    | filters.regex("#request")
    | filters.regex("#Request")
)
async def requests(client, message):
    search = message.text
    requested_movie = (
        search.replace("/request", "")
        .replace("/Request", "")
        .strip()
    )
    user_id = message.from_user.id

    if not requested_movie:
        await message.reply_text(
            "🙅 (फिल्म रिक्वेस्ट करने के लिए कृपया फिल्म का नाम और साल साथ में लिखें\n"
            "कुछ इस तरह 👇\n"
            "<code>/request Pushpa 2021</code>"
        )
        return

    # Pehla try: jo user ne diya usi se DB search
    files, offset, total_results = await get_search_results(
        chat_id=message.chat.id,
        query=requested_movie
    )

    if files:
        file_name = files[0]['file_name']
        await message.reply_text(
            f"🎥 {file_name}\n\n"
            f"आपने जो मूवी रिक्वेस्ट की है वो ग्रुप में उपलब्ध हैं\n\n"
            f"ग्रुप लिंक = {GRP_LNK}"
        )
        return

    # Agar direct nahi mila to AI spell check (TMDb) se try
    closest_movie = await ai_spell_check(
        chat_id=message.chat.id,
        wrong_name=requested_movie
    )

    if closest_movie:
        files, offset, total_results = await get_search_results(
            chat_id=message.chat.id,
            query=closest_movie
        )
        if files:
            file_name = files[0]['file_name']
            await message.reply_text(
                f"🎥 {file_name}\n\n"
                f"आपने जो मूवी रिक्वेस्ट की है वो ग्रुप में उपलब्ध हैं\n\n"
                f"ग्रुप लिंक = {GRP_LNK}"
            )
            return

        # AI ne naam sahi kar diya, par DB me file nahi → admin ko bhejo
        await message.reply_text(
            f"✅ आपकी फिल्म <b>{closest_movie}</b> हमारे एडमिन के पास भेज दिया गया है.\n\n"
            "🚀 जैसे ही फिल्म अपलोड होती हैं हम आपको मैसेज देंगे.\n\n"
            "📌 ध्यान दे - एडमिन अपने काम में व्यस्त हो सकते है इसलिए फिल्म अपलोड होने में टाइम लग सकता हैं"
        )
        await client.send_message(
            REQ_CHANNEL,
            f"☏ #𝙍𝙀𝙌𝙐𝙀𝙎𝙏𝙀𝘿_𝘾𝙊𝙉𝙏𝙀𝙉𝙏 ☎︎\n\n"
            f"ʙᴏᴛ - {temp.B_NAME}\n"
            f"ɴᴀᴍᴇ - {message.from_user.mention} (<code>{message.from_user.id}</code>)\n"
            f"Rᴇǫᴜᴇꜱᴛ - <code>{closest_movie}</code>",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(
                        'ɴᴏᴛ ʀᴇʟᴇᴀsᴇ 📅',
                        callback_data=f"not_release:{user_id}:{requested_movie}"
                    ),
                    InlineKeyboardButton(
                        'ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ 🙅',
                        callback_data=f"not_available:{user_id}:{requested_movie}"
                    ),
                ], [
                    InlineKeyboardButton(
                        'ᴜᴘʟᴏᴀᴅᴇᴅ ✅',
                        callback_data=f"uploaded:{user_id}:{requested_movie}"
                    )
                ], [
                    InlineKeyboardButton(
                        'ɪɴᴠᴀʟɪᴅ ғᴏʀᴍᴀᴛ🙅',
                        callback_data=f"series:{user_id}:{requested_movie}"
                    ),
                    InlineKeyboardButton(
                        'sᴇʟʟ ᴍɪsᴛᴇᴋ✍️',
                        callback_data=f"spelling_error:{user_id}:{requested_movie}"
                    )
                ], [
                    InlineKeyboardButton('⦉ ᴄʟᴏsᴇ ⦊', callback_data="close_data")
                ]]
            )
        )
    else:
        # AI bhi kuch nahi kar paya → direct requested_movie admin ko
        await message.reply_text(
            f"✅ आपकी फिल्म <b>{requested_movie}</b> हमारे एडमिन के पास भेज दिया गया है.\n\n"
            "🚀 जैसे ही फिल्म अपलोड होती हैं हम आपको मैसेज देंगे.\n\n"
            "📌 ध्यान दे - एडमिन अपने काम में व्यस्त हो सकते है इसलिए फिल्म अपलोड होने में टाइम लग सकता हैं"
        )
        await client.send_message(
            REQ_CHANNEL,
            f"📝 #REQUESTED_CONTENT 📝\n\n"
            f"ʙᴏᴛ - {temp.B_NAME}\n"
            f"ɴᴀᴍᴇ - {message.from_user.mention} (<code>{message.from_user.id}</code>)\n"
            f"Rᴇǫᴜᴇsᴛ - <code>{requested_movie}</code>",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(
                        'ɴᴏᴛ ʀᴇʟᴇᴀsᴇ 📅',
                        callback_data=f"not_release:{user_id}:{requested_movie}"
                    ),
                    InlineKeyboardButton(
                        'ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ 🙅',
                        callback_data=f"not_available:{user_id}:{requested_movie}"
                    )
                ], [
                    InlineKeyboardButton(
                        'ᴜᴘʟᴏᴀᴅᴇᴅ ✅',
                        callback_data=f"uploaded:{user_id}:{requested_movie}"
                    )
                ], [
                    InlineKeyboardButton(
                        'ɪɴᴠᴀʟɪᴅ ғᴏʀᴍᴀᴛ🙅',
                        callback_data=f"series:{user_id}:{requested_movie}"
                    ),
                    InlineKeyboardButton(
                        'sᴇʟʟ ᴍɪsᴛᴇᴋ✍️',
                        callback_data=f"spelling_error:{user_id}:{requested_movie}"
                    )
                ], [
                    InlineKeyboardButton('⦉ ᴄʟᴏsᴇ ⦊', callback_data="close_data")
                ]]
            )
        )
