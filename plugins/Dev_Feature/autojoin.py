# This code has been modified by @Safaridev
# Please do not remove this credit
import pyrogram
from pyrogram import Client, filters

from info import AUTH_CHANNELS

@Client.on_chat_join_request()
async def auto_accept_request(client, chat_member_update):
    chat_id = chat_member_update.chat.id
    user_id = chat_member_update.from_user.id

    # ❌ in sab channels me auto approve band
    if chat_id in AUTH_CHANNELS:
        return

    try:
        await client.approve_chat_join_request(chat_id, user_id)
    except Exception as e:
        print(e)
