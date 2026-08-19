from aiohttp import web
import re
import math
import logging
import secrets
import time
import mimetypes
from aiohttp.http_exceptions import BadStatusLine
from SAFARI.utils import multi_clients, work_loads, SafariBot
from SAFARI.utils.exceptions import FIleNotFound, InvalidHash
from SAFARI import StartTime, __version__
from SAFARI.utils.custom_dl import ByteStreamer
from SAFARI.utils.time_format import get_readable_time
from SAFARI.utils.render_template import render_page
from info import *
from utils import get_shortlink, temp

routes = web.RouteTableDef()

home_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Safaribotts</title>
    <style>
        .chatbot-title {
            text-align: center;
            font-size: 24px;
            margin-top: 20px;
        }

        .chatbot-image {
            display: block;
            margin: 0 auto;
            max-width: 300px;
        }
    </style>
</head>
<body>
    <img src="https://graph.org/file/a97d39a6aa4a1317d430b.jpg" alt="Chatbot Image" class="chatbot-image">

    <h1 class="chatbot-title">Safaribotts</h1>
</body>
</html>
"""

# Global Cache Variable
class_cache = {}

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.Response(text=home_template, content_type='text/html')


# --------------------------------------------------------------------------
# ANTI-BYPASS GATEWAY (5s Verification Screen & Redirect)
# --------------------------------------------------------------------------

@routes.get("/verify", allow_head=True)
async def verify_page_handler(request: web.Request):
    token = request.rel_url.query.get("token")
    if not token:
        return web.Response(text="Invalid or Expired Verification Link!", status=400)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Security Check | Safe Verification</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background-color: #0b0f19;
                color: #ffffff;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            .card {{
                background: #1e293b;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                text-align: center;
                max-width: 350px;
                width: 90%;
            }}
            .loader {{
                border: 4px solid #334155;
                border-top: 4px solid #38bdf8;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }}
            @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            .btn {{
                display: none;
                background-color: #38bdf8;
                color: #0f172a;
                text-decoration: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 16px;
                margin-top: 15px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🛡️ Anti-Bot Protection</h2>
            <p id="msg">Please wait <b><span id="timer">5</span>s</b> to verify...</p>
            <div id="spinner" class="loader"></div>
            <a id="verifyBtn" href="/redirect_shortner?token={token}" class="btn">Click Here to Continue ➔</a>
        </div>

        <script>
            let timeLeft = 5;
            let timerSpan = document.getElementById('timer');
            let countdown = setInterval(() => {{
                timeLeft--;
                timerSpan.textContent = timeLeft;
                if(timeLeft <= 0) {{
                    clearInterval(countdown);
                    document.getElementById('msg').innerHTML = "Verification Successful! Proceed to link.";
                    document.getElementById('spinner').style.display = 'none';
                    document.getElementById('verifyBtn').style.display = 'inline-block';
                }}
            }}, 1000);
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type="text/html")


@routes.get("/redirect_shortner", allow_head=True)
async def redirect_shortner_handler(request: web.Request):
    token = request.rel_url.query.get("token")
    if not token:
        return web.Response(text="Invalid Token", status=400)
    
    parts = token.split("_")
    if parts[0] == "all":
        _, user_id, grp_id, step, verify_id, file_id = parts
        target_start_url = f"https://t.me/{temp.U_NAME}?start=sendall_{user_id}_{verify_id}_{file_id}"
    else:
        user_id, grp_id, step, verify_id, file_id = parts
        target_start_url = f"https://t.me/{temp.U_NAME}?start=verify_{user_id}_{verify_id}_{file_id}"
    
    grp_id = int(grp_id) if grp_id.lstrip("-").isdigit() else 0
    step = int(step) if step.isdigit() else 1
    
    is_second = (step == 2)
    is_third = (step == 3)
    
    try:
        real_shortlink = await get_shortlink(
            link=target_start_url,
            grp_id=grp_id,
            is_second_shortener=is_second,
            is_third_shortener=is_third
        )
    except Exception as e:
        logging.error(f"Shortlink Error: {e}")
        real_shortlink = target_start_url
        
    raise web.HTTPFound(location=real_shortlink)


# --------------------------------------------------------------------------
# STREAMING & DOWNLOAD ROUTES
# --------------------------------------------------------------------------

@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        
        clean_path = path.split('/')[0]
        id = int(clean_path)
        secure_hash = request.rel_url.query.get("hash")

        index = min(work_loads, key=work_loads.get)
        faster_client = multi_clients[index]
        
        if faster_client in class_cache:
            tg_connect = class_cache[faster_client]
        else:
            tg_connect = ByteStreamer(faster_client)
            class_cache[faster_client] = tg_connect
            
        file_id = await tg_connect.get_file_properties(id)
        file_name = file_id.file_name or f"{secrets.token_hex(2)}.mp4"
        
        file_url = f"{request.url.origin}/{id}?hash={secure_hash}"
        
        page_html = await render_page(id, secure_hash, file_name)
        
        if page_html and isinstance(page_html, str):
            page_html = page_html.replace("{{file_url}}", file_url).replace("{{file_name}}", file_name)
        
        return web.Response(
            text=page_html, 
            content_type='text/html'
        )
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message if hasattr(e, 'message') else "Invalid Hash")
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message if hasattr(e, 'message') else "File Not Found")
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

@routes.get(r"/{path:\S+}", allow_head=True)
async def download_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        
        if "favicon.ico" in path:
            return web.Response(status=200)
            
        clean_path = path.split('/')[0]
        id = int(clean_path)
        
        secure_hash = request.rel_url.query.get("hash")
        return await media_streamer(request, id, secure_hash)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message if hasattr(e, 'message') else "Invalid Hash")
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message if hasattr(e, 'message') else "File Not Found")
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))


async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    
    if MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logging.debug(f"Using cached ByteStreamer object for client {index}")
    else:
        logging.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
        
    logging.debug("before calling get_file_properties")
    file_id = await tg_connect.get_file_properties(id)
    logging.debug("after calling get_file_properties")
    
    if file_id.unique_id[:6] != secure_hash:
        logging.debug(f"Invalid hash for message with ID {id}")
        raise InvalidHash
    
    file_size = file_id.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1

    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_size = 1024 * 1024
    until_bytes = min(until_bytes, file_size - 1)

    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1

    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
    )

    mime_type = file_id.mime_type
    file_name = file_id.file_name
    disposition = "attachment"

    if mime_type:
        if not file_name:
            try:
                file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
            except (IndexError, AttributeError):
                file_name = f"{secrets.token_hex(2)}.unknown"
    else:
        if file_name:
            mime_type = mimetypes.guess_type(file_id.file_name)
        else:
            mime_type = "application/octet-stream"
            file_name = f"{secrets.token_hex(2)}.unknown"

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
  )
      
