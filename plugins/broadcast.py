# This code has been modified by @Safaridev
# Please do not remove credits

from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait,
    UserIsBlocked,
    InputUserDeactivated,
    PeerIdInvalid
)

import asyncio
import datetime
import time

from database.users_chats_db import db
from info import ADMINS


# =========================
# BROADCAST FUNCTION
# =========================

async def broadcast_messages(user_id, b_msg):

    try:

        await b_msg.copy(chat_id=user_id)

        return True, "Success"

    except FloodWait as e:

        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, b_msg)

    except UserIsBlocked:

        # Auto remove blocked user
        await db.delete_user(user_id)

        print(f"Blocked User Removed -> {user_id}")

        return False, "Blocked"

    except InputUserDeactivated:

        # Auto remove deleted account
        await db.delete_user(user_id)

        print(f"Deleted User Removed -> {user_id}")

        return False, "Deleted"

    except PeerIdInvalid:

        # Invalid user remove
        await db.delete_user(user_id)

        print(f"Invalid User Removed -> {user_id}")

        return False, "Deleted"

    except Exception as e:

        print(f"Broadcast Error {user_id} -> {e}")

        return False, "Error"


# =========================
# USER BROADCAST
# =========================

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def verupikkals(bot, message):

    users = await db.get_all_users()

    b_msg = message.reply_to_message

    sts = await message.reply_text(
        text="Broadcast Started..."
    )

    start_time = time.time()

    total_users = await db.total_users_count()

    done = 0
    blocked = 0
    deleted = 0
    failed = 0
    success = 0

    async for user in users:

        user_id = int(user['id'])

        try:

            pti, sh = await broadcast_messages(user_id, b_msg)

            if pti:

                success += 1

            else:

                if sh == "Blocked":

                    blocked += 1

                elif sh == "Deleted":

                    deleted += 1

                else:

                    failed += 1

        except Exception as e:

            failed += 1

            print(f"MAIN LOOP ERROR {user_id} -> {e}")

        done += 1

        # Safe speed for Telegram
        await asyncio.sleep(0.08)

        # Update after every 50 users
        if done % 50 == 0:

            try:

                await sts.edit_text(
                    f"Broadcast In Progress\n\n"
                    f"Total Users: {total_users}\n"
                    f"Completed: {done}/{total_users}\n\n"
                    f"Success: {success}\n"
                    f"Blocked: {blocked}\n"
                    f"Deleted: {deleted}\n"
                    f"Failed: {failed}"
                )

            except Exception:
                pass

    time_taken = datetime.timedelta(
        seconds=int(time.time() - start_time)
    )

    await sts.edit_text(
        f"Broadcast Completed\n\n"
        f"Time Taken: {time_taken}\n\n"
        f"Total Users: {total_users}\n"
        f"Completed: {done}/{total_users}\n\n"
        f"Success: {success}\n"
        f"Blocked: {blocked}\n"
        f"Deleted: {deleted}\n"
        f"Failed: {failed}"
    )


# =========================
# GROUP BROADCAST
# =========================

@Client.on_message(filters.command("grp_broadcast") & filters.user(ADMINS) & filters.reply)
async def grp_broadcast(bot, message):

    chats = await db.get_all_chats()

    b_msg = message.reply_to_message

    sts = await message.reply_text(
        text="Group Broadcast Started..."
    )

    start_time = time.time()

    total_chats = await db.total_chat_count()

    done = 0
    success = 0
    failed = 0

    async for chat in chats:

        chat_id = int(chat['id'])

        try:

            pti, sh = await broadcast_messages(chat_id, b_msg)

            if pti:

                success += 1

            else:

                failed += 1

        except Exception as e:

            failed += 1

            print(f"GROUP ERROR {chat_id} -> {e}")

        done += 1

        # Group safe delay
        await asyncio.sleep(1)

        if done % 20 == 0:

            try:

                await sts.edit_text(
                    f"Group Broadcast In Progress\n\n"
                    f"Total Chats: {total_chats}\n"
                    f"Completed: {done}/{total_chats}\n\n"
                    f"Success: {success}\n"
                    f"Failed: {failed}"
                )

            except Exception:
                pass

    time_taken = datetime.timedelta(
        seconds=int(time.time() - start_time)
    )

    await sts.edit_text(
        f"Group Broadcast Completed\n\n"
        f"Time Taken: {time_taken}\n\n"
        f"Total Chats: {total_chats}\n"
        f"Completed: {done}/{total_chats}\n\n"
        f"Success: {success}\n"
        f"Failed: {failed}"
    )
