"""Gioi han kich thuoc request cua /api/v1 o tang ASGI.

Vi sao khong chi doc Content-Length: header do client tu khai. Mot client
khai 10 byte roi stream 10 MB se di qua neu ta tin header. Nen o day header
chi la duong chan SOM (tu choi truoc khi doc byte nao), con duong chan THAT
la dem so byte thuc su doc duoc.

Middleware doc het body roi phat lai cho app thay vi nem exception tu trong
`receive()`: nem tu do se noi len qua stack middleware cua Starlette va thanh
500, dung luc ta muon tra 413.
"""
import json


MAX_BYTES = 16 * 1024
DUONG_DAN = "/api/v1"


class RequestSizeLimitMiddleware:
    """Gioi han body theo tung nhom duong dan.

    `gioi_han` la tuple (prefix, so_byte). Duong dan khong khop prefix nao thi
    di thang, khong bi buffer - GET tra vai tram KB HTML khong duoc dong vao
    bo nho vi mot middleware chan body request.
    """

    def __init__(self, app, *, max_bytes: int = MAX_BYTES,
                 path_prefix: str = DUONG_DAN, gioi_han=None):
        self.app = app
        self.gioi_han = tuple(gioi_han) if gioi_han else ((path_prefix, max_bytes),)

    def _tran(self, path: str):
        for prefix, so_byte in self.gioi_han:
            if path.startswith(prefix):
                return so_byte
        return None

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)
        # Bien CUC BO, khong gan vao self: middleware la mot instance dung
        # chung cho moi request, gan vao self se lam hai request dong thoi
        # ghi de nguong cua nhau.
        tran = self._tran(scope.get("path", ""))
        if tran is None:
            return await self.app(scope, receive, send)

        headers = dict(scope.get("headers") or ())
        khai_bao = headers.get(b"content-length")
        if khai_bao is not None:
            try:
                if int(khai_bao) > tran:
                    return await self._tra_413(send)
            except ValueError:
                return await self._tra_413(send)

        body = b""
        con_nua = True
        while con_nua:
            message = await receive()
            if message["type"] != "http.request":
                break
            body += message.get("body", b"")
            if len(body) > tran:
                return await self._tra_413(send)
            con_nua = message.get("more_body", False)

        da_phat = False

        async def phat_lai():
            nonlocal da_phat
            if da_phat:
                return {"type": "http.disconnect"}
            da_phat = True
            return {"type": "http.request", "body": body, "more_body": False}

        return await self.app(scope, phat_lai, send)

    async def _tra_413(self, send):
        payload = json.dumps({"detail": "request_too_large"}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode("ascii")),
            ],
        })
        await send({"type": "http.response.body", "body": payload})
