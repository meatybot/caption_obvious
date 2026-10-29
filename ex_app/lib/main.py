"""Caption Obvious: an imgflip meme entry in the Nextcloud Smart Picker, with link previews.

The picker script (js/caption_obvious-reference.js, built from src/ with webpack) runs in the browser and
reaches this app through the AppAPI proxy. It registers the Smart Picker element and the link preview widget
the way the memegen app does. The picker searches templates, draws the caption with Konva, and posts the
finished JPEG to /api/upload, which hosts
it on imgflip. The Smart Picker inserts the returned i.imgflip.com link, and AppAPI asks
/reference/resolve to turn imgflip links into a rich object that the picker script renders as an image.
"""

import base64
import binascii
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import imgflip
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from limits import BodySizeLimitMiddleware
from nc_py_api import AsyncNextcloudApp, NextcloudExceptionNotFound
from nc_py_api.ex_app import AppAPIAuthMiddleware, LogLvl, run_app, set_handlers

PROVIDER_ID = "caption_obvious_meme"
# AppAPI's OCS endpoint for reference providers. Released nc_py_api has no helper for it yet, so the app
# calls it directly, on the same /ocs/v1.php/apps/app_api/api/v1 base that nc_py_api uses.
REFERENCE_PROVIDER_ENDPOINT = "/ocs/v1.php/apps/app_api/api/v1/ui/reference-provider"
# The same links in PHP (AppAPI's reference provider) and in resolve_reference() below.
MATCH_PATTERNS = [r"#^https://i\.imgflip\.com/[0-9a-z]+\.(jpg|png)$#", r"#^https://imgflip\.com/i/[0-9a-z]+$#"]
REFERENCE_RE = re.compile(r"^https://(?:i\.imgflip\.com/([0-9a-z]+)\.(jpg|png)|imgflip\.com/i/([0-9a-z]+))$")

MAX_IMAGE_BYTES = 10 * 1024 * 1024
TOO_LARGE = f"the image is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB"
# The image arrives base64-encoded in JSON: 4/3 of its size, plus the texts and boxes.
MAX_UPLOAD_BODY_BYTES = MAX_IMAGE_BYTES * 4 // 3 + 64 * 1024
# Template data and images never change for an ID; a day keeps a stale copy short-lived anyway.
CACHE_A_DAY = "public, max-age=86400"
# Font file names carry a content hash (webpack.config.js), so a file at a given URL never changes.
CACHE_IMMUTABLE = "public, max-age=31536000, immutable"

SESSION: imgflip.Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    global SESSION
    storage = os.environ.get("APP_PERSISTENT_STORAGE", str(Path(__file__).parent))
    SESSION = imgflip.Session(os.path.join(storage, "imgflip_session.json"))
    set_handlers(app, enabled_handler)
    yield


APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)  # every request comes from AppAPI or its proxy, signed with the app secret
# Counts the body while it streams in, so an oversized upload is refused before it is buffered.
APP.add_middleware(BodySizeLimitMiddleware, max_bytes=MAX_UPLOAD_BODY_BYTES, paths=("/api/upload",), error=TOO_LARGE)


@APP.middleware("http")
async def cache_fonts(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/js/fonts/") and response.status_code == 200:
        response.headers["Cache-Control"] = CACHE_IMMUTABLE
    return response


async def enabled_handler(enabled: bool, nc: AsyncNextcloudApp) -> str:
    if not enabled:
        # AppAPI already hides the provider of a disabled app and deletes it when the app is removed.
        # Deleting it here as well keeps the table in step with what users see.
        try:
            await nc.ocs("DELETE", REFERENCE_PROVIDER_ENDPOINT, params={"providerId": PROVIDER_ID})
        except NextcloudExceptionNotFound:
            pass
        except Exception as e:  # noqa: BLE001  disabling must not fail because of this
            await nc.log(LogLvl.WARNING, f"Could not unregister the reference provider: {e}")
        return ""
    try:
        await nc.ocs(
            "POST",
            REFERENCE_PROVIDER_ENDPOINT,
            json={
                "providerId": PROVIDER_ID,
                "title": "Meme (imgflip)",
                "iconUrl": "img/app.svg",
                "order": 10,
                "matchPatterns": MATCH_PATTERNS,
                "scriptPath": "js/caption_obvious-reference.js",
            },
        )
    except Exception as e:  # noqa: BLE001  the error string is shown to the Nextcloud administrator
        await nc.log(LogLvl.ERROR, f"Could not register the reference provider: {e}")
        return f"Could not register the reference provider: {e}"
    return ""


@APP.get("/api/search")
async def search(q: str = "", limit: int = 40):
    try:
        return {"ok": True, "data": await imgflip.search(q, limit)}
    except Exception as e:  # noqa: BLE001  upstream failure
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)


@APP.get("/api/template")
async def template(template_id: Annotated[int, Query(alias="id")]):
    try:
        data = await imgflip.template(template_id)
    except LookupError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=404)
    return JSONResponse({"ok": True, "data": data}, headers={"Cache-Control": CACHE_A_DAY})


@APP.get("/api/template-image/{name}")
async def template_image(name: str):
    """Template images through this app: same origin as the editor, so the canvas stays exportable."""
    template_id, _, ext = name.partition(".")
    if not template_id.isdigit():
        raise HTTPException(404)
    return await _image(f"{imgflip.b36(int(template_id))}.{ext}")


@APP.get("/image/{name}")
async def hosted_image(name: str):
    """Hosted memes for the link preview. Nextcloud's CSP does not allow images from i.imgflip.com."""
    return await _image(name)


async def _image(path: str) -> Response:
    try:
        body, content_type = await imgflip.image(path)
    except LookupError as e:
        raise HTTPException(404) from e
    return Response(body, media_type=content_type, headers={"Cache-Control": CACHE_A_DAY})


@APP.post("/api/upload")
async def upload(request: Request, payload: Annotated[dict, Body()]):
    try:
        image_b64 = payload["image"].split(",")[-1]
        image_bytes = len(base64.b64decode(image_b64, validate=True))
    except (KeyError, AttributeError, binascii.Error) as e:
        return JSONResponse({"ok": False, "error": f"bad request: {e}"}, status_code=400)
    if image_bytes > MAX_IMAGE_BYTES:
        return JSONResponse({"ok": False, "error": TOO_LARGE}, status_code=413)
    try:
        entry = await SESSION.upload(
            image_b64,
            int(payload["template_id"]),
            [str(t) for t in payload["texts"]],
            payload["boxes"],
            request.scope.get("username", ""),
        )
    except (KeyError, ValueError) as e:
        return JSONResponse({"ok": False, "error": f"bad request: {e}"}, status_code=400)
    except Exception as e:  # noqa: BLE001  upstream failure
        return JSONResponse({"ok": False, "error": str(e)}, status_code=502)
    return {"ok": True, **entry}


@APP.post("/reference/resolve")
async def resolve_reference(payload: Annotated[dict, Body()]):
    """Called by AppAPI for links matching MATCH_PATTERNS. Any status but 200 means "no preview".

    AppAPIAuthMiddleware has already checked that the request comes from AppAPI.
    """
    m = REFERENCE_RE.match(str(payload.get("reference", "")))
    if not m:
        raise HTTPException(404)
    slug, ext = m[1] or m[3], m[2] or "jpg"
    entry = SESSION.find(slug)
    text = entry["text"] if entry else ""
    return {
        "title": text or "imgflip meme",
        "description": "Meme hosted on imgflip.com",
        "url": f"{imgflip.SITE}/i/{slug}",
        "rich_object_type": PROVIDER_ID,
        "rich_object": {
            "slug": slug,
            "ext": ext,
            "image_url": f"{imgflip.IMG}/{slug}.{ext}",
            "page_url": f"{imgflip.SITE}/i/{slug}",
            "text": text,
        },
    }


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    run_app("main:APP", log_level="info")
