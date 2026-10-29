"""Imgflip client: template search, template lookup, and anonymous meme hosting.

With imgflip's web generator, the browser draws the text on a canvas and POSTs
the finished JPEG to /ajax_meme_done_canvas, guarded only by a double-submit
CSRF token (any 32 characters, sent as both the `doge` cookie and the `__tok` field).
This module replays that request. The picker draws the image in the browser, so no server-side rendering is needed.

imgflip ties anonymous uploads to its `claim_key` cookie, and only a client holding it can delete them.
The session keeps that cookie and an upload log in a JSON file in the ExApp's persistent storage.
"""

import asyncio
import json
import os
import re
import secrets
import string
import time

import niquests
from limits import AsyncLRU

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
SITE = "https://imgflip.com"
IMG = "https://i.imgflip.com"
SLUG_RE = re.compile(r"^[0-9a-z]{1,16}$")

_http = niquests.AsyncSession()
_http.headers["User-Agent"] = UA


def b36(n: int) -> str:
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = digits[r] + out
    return out or "0"


def boxes_for(t: dict) -> list[dict]:
    """Text boxes in template pixels. Templates without a saved layout get the classic top/bottom pair."""
    w, h = t["w"], t["h"]
    saved = [b for b in json.loads(t.get("default_settings") or "[]") if b.get("type") == "text"]
    if saved:
        return saved
    bh = h / 4
    base = {
        "type": "text",
        "x": 5,
        "w": w - 10,
        "h": bh,
        "rotation": 0,
        "font": "impact",
        "font_color": "#ffffff",
        "outline_color": "#000000",
        "force_caps": True,
        "text_align": "center",
    }
    return [{**base, "y": 5, "vertical_align": "top"}, {**base, "y": h - bh - 5, "vertical_align": "bottom"}]


def describe(t: dict) -> dict:
    """A raw imgflip template (search result or template page) in the shape the editor uses."""
    return {
        "id": int(t["id"]),
        "name": t["name"],
        "width": t["w"],
        "height": t["h"],
        "file_type": t["file_type"],
        "box_count": len(boxes_for(t)),
        "image_url": f"{IMG}/{b36(int(t['id']))}.{t['file_type']}",
        "boxes": boxes_for(t),
    }


async def search(q: str, limit: int = 40) -> list[dict]:
    limit = max(1, min(limit, 100))
    if not q.strip():
        return (await popular())[:limit]
    r = await _http.get(
        f"{SITE}/ajax_meme_search_new",
        timeout=20,
        headers={"X-Requested-With": "XMLHttpRequest"},
        params={"q": q, "limit": limit, "include_nsfw": 0, "allow_gifs": 0, "transparent_only": 0, "gifs_only": 0},
    )
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(body["error"])
    return [describe(t) for t in body["results"]]


_popular: tuple[float, list[dict]] = (0.0, [])


async def popular() -> list[dict]:
    """The top 100 imgflip templates, refreshed hourly. They carry no box layout: fetch it with template()."""
    global _popular
    if time.time() - _popular[0] > 3600:
        r = await _http.get("https://api.imgflip.com/get_memes", timeout=20)
        r.raise_for_status()
        _popular = (
            time.time(),
            [
                {
                    "id": int(t["id"]),
                    "name": t["name"],
                    "width": t["width"],
                    "height": t["height"],
                    "file_type": t["url"].rsplit(".", 1)[-1],
                    "box_count": t["box_count"],
                    "image_url": t["url"],
                    "boxes": None,
                }
                for t in r.json()["data"]["memes"]
            ],
        )
    return _popular[1]


# Bounded: the template ID comes from the request, so an unbounded cache would grow with every new ID.
_templates: AsyncLRU[int, dict] = AsyncLRU(100)
_images: AsyncLRU[str, tuple[bytes, str]] = AsyncLRU(100)


async def template(template_id: int) -> dict:
    """A template's metadata. Search by ID is not supported, so it is read from the template's page."""
    return await _templates.get(template_id, lambda: _fetch_template(template_id))


async def _fetch_template(template_id: int) -> dict:
    r = await _http.get(f"{SITE}/memegenerator/{template_id}", timeout=20)
    r.raise_for_status()
    marker = "memes=["
    start = r.text.find(marker)
    if start < 0:
        raise LookupError(f"template {template_id} not found")
    memes, _ = json.JSONDecoder().raw_decode(r.text, start + len(marker) - 1)
    for t in memes:
        if int(t["id"]) == template_id:
            return describe(t)
    raise LookupError(f"template {template_id} not found")


async def image(path: str) -> tuple[bytes, str]:
    """An image from i.imgflip.com, as (body, content type). `path` is `<slug>.<jpg|png>`."""
    slug, _, ext = path.partition(".")
    if not SLUG_RE.match(slug) or ext not in ("jpg", "png"):
        raise LookupError(f"not an imgflip image: {path}")
    return await _images.get(f"{slug}.{ext}", lambda: _fetch_image(slug, ext))


async def _fetch_image(slug: str, ext: str) -> tuple[bytes, str]:
    r = await _http.get(f"{IMG}/{slug}.{ext}", timeout=30)
    if r.status_code == 404:
        raise LookupError(f"no image {slug}.{ext}")
    r.raise_for_status()
    return r.content, "image/jpeg" if ext == "jpg" else "image/png"


class Session:
    """The anonymous imgflip identity that owns this ExApp's uploads, persisted as JSON."""

    def __init__(self, path: str):
        self.path = path
        self.lock = asyncio.Lock()
        self.http = niquests.AsyncSession()
        self.http.headers["User-Agent"] = UA
        self.uploads: list[dict] = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                saved = json.load(f)
            if saved.get("claim_key"):
                self.http.cookies.set("claim_key", saved["claim_key"], domain="imgflip.com")
            self.uploads = saved.get("uploads", [])

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)  # claim_key grants delete rights
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"claim_key": self.claim_key(), "uploads": self.uploads}, f, indent=2)
        os.replace(tmp, self.path)

    def claim_key(self) -> str | None:
        return next((c.value for c in self.http.cookies if c.name == "claim_key"), None)

    def find(self, slug: str) -> dict | None:
        return next((u for u in self.uploads if u["url"].rsplit("/", 1)[-1].split(".")[0] == slug), None)

    async def upload(self, jpeg_b64: str, template_id: int, texts: list[str], boxes: list[dict], user: str) -> dict:
        """Host a finished JPEG on imgflip as an anonymous, public meme."""
        form = {
            "template": template_id,
            "template_url": "",
            "imgData": jpeg_b64,
            "text": " ".join(t for t in texts if t),
            "type": "jpeg",
            "anon": "",
            "private": "",
            "isReply": "",
            "source": "canvas",
            "watermark_text": "imgflip.com",
            "watermark_position": "bottom-left",
            "watermark_custom": "",
        }
        for i, (box, text) in enumerate(zip(boxes, texts, strict=False)):
            for k in ("type", "x", "y", "w", "h"):
                form[f"boxes[{i}][{k}]"] = box[k]
            form[f"boxes[{i}][text]"] = text
        async with self.lock:
            tok = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
            self.http.cookies.set("doge", tok, domain="imgflip.com")
            r = await self.http.post(
                f"{SITE}/ajax_meme_done_canvas",
                data={**form, "__tok": tok, "__cookie_enabled": 1},
                timeout=60,
                headers={"X-Requested-With": "XMLHttpRequest", "Origin": SITE, "Referer": f"{SITE}/memegenerator"},
            )
            r.raise_for_status()
            body = r.json()
            if "iid" not in body:
                raise RuntimeError(body.get("error", f"unexpected response: {body}"))
            slug = b36(int(body["iid"]))
            entry = {
                "iid": int(body["iid"]),
                "url": f"{IMG}/{slug}.jpg",
                "page_url": f"{SITE}/i/{slug}",
                "template_id": template_id,
                "text": form["text"],
                "user": user,
                "created": int(time.time()),
            }
            self.uploads.append(entry)
            self._save()
        return entry
