import jinja2
import urllib.parse
import logging
import mimetypes
from info import *
from SAFARI.utils import SafariBot
from SAFARI.utils.human_readable import humanbytes
from SAFARI.utils.file_properties import get_file_ids
from SAFARI.utils.exceptions import InvalidHash

async def render_page(id, secure_hash, src=None):
    # 1. BIN_CHANNEL se file details fetch karna
    file = await SafariBot.get_messages(int(BIN_CHANNEL), int(id))
    file_data = await get_file_ids(SafariBot, int(BIN_CHANNEL), int(id))
    
    # 2. Hash verification
    if file_data.unique_id[:6] != secure_hash:
        logging.debug(f"link hash: {secure_hash} - {file_data.unique_id[:6]}")
        logging.debug(f"Invalid hash for message with - ID {id}")
        raise InvalidHash

    # 3. Clean Direct Stream/Download URL
    base_clean_url = URL.rstrip('/')
    clean_filename = urllib.parse.quote(file_data.file_name or "video.mp4")
    src = f"{base_clean_url}/{id}/{clean_filename}?hash={secure_hash}"

    # 4. Accurate Video/Audio Detection (Even for MKV Document files)
    mime_type = file_data.mime_type or mimetypes.guess_type(file_data.file_name)[0] or "video/mp4"
    is_video = (
        mime_type.startswith("video") or 
        mime_type.startswith("audio") or 
        str(file_data.file_name).lower().endswith(('.mkv', '.mp4', '.avi', '.webm', '.mov', '.mp3', '.m4a'))
    )

    file_size = humanbytes(file_data.file_size)

    if is_video:
        template_file = "SAFARI/template/req.html"
    else:
        template_file = "SAFARI/template/dl.html"

    with open(template_file, "r", encoding="utf-8") as f:
        template = jinja2.Template(f.read())

    display_name = (file_data.file_name or "Media Video").replace("_", " ")

    return template.render(
        file_name=display_name,
        file_url=src,
        file_size=file_size,
        file_unique_id=file_data.unique_id,
    )
