"""Request size cap and a small async LRU cache."""

from collections import OrderedDict
from collections.abc import Awaitable, Callable, Hashable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodySizeLimitMiddleware:
    """Answers 413 to a request whose body is larger than `max_bytes` on `paths`.

    The body is counted while it streams in, so an oversized request is rejected without being buffered.
    `Content-Length` is checked first; a chunked body is cut off at the limit.
    """

    def __init__(self, app: ASGIApp, max_bytes: int, paths: tuple[str, ...], error: str):
        self.app = app
        self.max_bytes = max_bytes
        self.paths = paths
        self.error = error

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] not in self.paths:
            await self.app(scope, receive, send)
            return

        too_large = JSONResponse({"ok": False, "error": self.error}, status_code=413)
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await too_large(scope, receive, send)
            return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _BodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            response_started = response_started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if not response_started:
                await too_large(scope, receive, send)


class _BodyTooLarge(Exception):
    pass


class AsyncLRU[K: Hashable, V]:
    """At most `maxsize` results of an async loader, least recently used evicted first.

    Only successful results are kept, so a failed lookup is retried next time.
    """

    def __init__(self, maxsize: int):
        self.maxsize = maxsize
        self._items: OrderedDict[K, V] = OrderedDict()

    async def get(self, key: K, load: Callable[[], Awaitable[V]]) -> V:
        if key in self._items:
            self._items.move_to_end(key)
            return self._items[key]
        value = await load()
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self.maxsize:
            self._items.popitem(last=False)
        return value

    def __len__(self) -> int:
        return len(self._items)
