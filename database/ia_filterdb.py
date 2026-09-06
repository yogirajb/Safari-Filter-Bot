# This code has been modified by @Safaridev
# Please do not remove this credit
import logging
from struct import pack
import re
import base64
import asyncio
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError, AutoReconnect, ServerSelectionTimeoutError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URI, DATABASE_NAME, COLLECTION_NAME, USE_CAPTION_FILTER, MAX_B_TN
from utils import get_settings, save_group_settings
from fuzzywuzzy import process
from Script import script

# Set up logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Connection Pool aur Timeouts: Lag aur timeout errors ko prevent karne ke liye
client = AsyncIOMotorClient(
    DATABASE_URI,
    maxPoolSize=50,
    minPoolSize=10,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=15000,
    socketTimeoutMS=30000,
    waitQueueTimeoutMS=5000
)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)

@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME


async def save_file(media):
    """Save file in database with auto-retry on network drop"""

    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    try:
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
        )
    except ValidationError:
        logger.exception('Error occurred while saving file in database')
        return False, None

    # Connection drop hone par 3 baar auto-retry karega
    for attempt in range(3):
        try:
            await file.commit()
            logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to database')
            return True, file_id
        except DuplicateKeyError:      
            logger.warning(
                f'{getattr(media, "file_name", "NO_FILE")} is already saved in database'
            )
            return False, file_id
        except (AutoReconnect, ServerSelectionTimeoutError) as e:
            logger.warning(f"MongoDB retry {attempt + 1}/3 due to connection lag: {e}")
            await asyncio.sleep(1.5)
        except Exception as e:
            logger.error(f"Error saving to MongoDB: {e}")
            return False, None

    return False, None


async def get_search_results(chat_id, query, file_type=None, max_results=10, offset=0, filter=False):
    """For given query return (results, next_offset)"""
    banned_words = script.BLACKLIST
    if chat_id is not None:
        settings = await get_settings(int(chat_id))
        try:
            if settings['max_btn']:
                max_results = 10
            else:
                max_results = int(MAX_B_TN)
        except KeyError:
            await save_group_settings(int(chat_id), 'max_btn', False)
            settings = await get_settings(int(chat_id))
            if settings['max_btn']:
                max_results = 10
            else:
                max_results = int(MAX_B_TN)
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return []

    if USE_CAPTION_FILTER:
        filter_dict = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        filter_dict = {'file_name': regex}

    if file_type:
        filter_dict['file_type'] = file_type

    total_results = 0
    files = []
    next_offset = ''

    # Retry guard for reading search results
    for attempt in range(3):
        try:
            total_results = await Media.count_documents(filter_dict)
            next_offset = offset + max_results
            if next_offset > total_results:
                next_offset = ''

            cursor = Media.find(filter_dict)
            cursor.sort('$natural', -1)
            cursor.skip(offset).limit(max_results)
            files = await cursor.to_list(length=max_results)
            break
        except (AutoReconnect, ServerSelectionTimeoutError) as e:
            logger.warning(f"MongoDB search retry {attempt + 1}/3: {e}")
            await asyncio.sleep(1.0)
        except Exception as e:
            logger.error(f"Search query error: {e}")
            return [], '', 0

    for file in files:
        for banned_word in banned_words:
            pattern = re.compile(re.escape(banned_word), re.IGNORECASE)
            file['file_name'] = pattern.sub('', file['file_name']).strip()

    return files, next_offset, total_results


async def get_all_files():
    try:
        cursor = Media.find() 
        all_files = await cursor.to_list(length=10000)  
        return [file['file_name'] for file in all_files]
    except Exception as e:
        logger.error(f"Error fetching all files: {e}")
        return []


async def get_bad_files(query, file_type=None, filter=False):
    """For given query return (results, next_offset)"""
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-_])' + query + r'(\b|[\.\+\-_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-_]')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except:
        return [], 0

    if USE_CAPTION_FILTER:
        filter_dict = {'$or': [{'file_name': regex}, {'caption': regex}]}
    else:
        filter_dict = {'file_name': regex}

    if file_type:
        filter_dict['file_type'] = file_type

    try:
        total_results = await Media.count_documents(filter_dict)
        cursor = Media.find(filter_dict)
        cursor.sort('$natural', -1)
        files = await cursor.to_list(length=total_results)
        return files, total_results
    except Exception as e:
        logger.error(f"Error getting bad files: {e}")
        return [], 0


async def get_file_details(query):
    try:
        banned_words = script.BLACKLIST
        filter_dict = {'file_id': query}
        cursor = Media.find(filter_dict)
        filedetails = await cursor.to_list(length=1)
        if filedetails:
            file = filedetails[0]
            original_file_name = getattr(file, 'file_name', '')
            modified_file_name = original_file_name
            for banned_word in banned_words:
                pattern = re.compile(re.escape(banned_word), re.IGNORECASE)
                modified_file_name = pattern.sub('', modified_file_name).strip()
            if not modified_file_name:
                modified_file_name = "DefaultFileName"
            setattr(file, 'file_name', modified_file_name)
        return filedetails
    except Exception as e:
        logging.error("An error occurred:", exc_info=True)
        return None


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0

    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0

            r += bytes([i])

    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref
  
