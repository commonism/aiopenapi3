import email.message
import http.cookiejar
import urllib.request

import aiopenapi3.plugin


class Cookies(aiopenapi3.plugin.Message):
    class _Request(urllib.request.Request):
        """
        c.f. httpx _CookieCompatRequest
        """

        def __init__(self, ctx: aiopenapi3.plugin.Message.Context) -> None:
            super().__init__(
                url=str(ctx.request.api.url),
                headers=dict(ctx.headers),
                method=ctx.request.method,
            )
            self.ctx = ctx

        def add_unredirected_header(self, key: str, value: str) -> None:
            self.ctx.headers[key] = value

    class _Response:
        """
        c.f. c.f. httpx _CookieCompatResponse
        """

        def __init__(self, ctx: aiopenapi3.plugin.Message.Context) -> None:
            self.ctx = ctx

        def info(self) -> email.message.Message:
            info = email.message.Message()
            key = "set-cookie"
            for value in self.ctx.headers.get_list(key):
                info[key] = value
            return info

    def __init__(self, cookies: http.cookiejar.CookieJar = None):
        self.cookies = cookies or http.cookiejar.CookieJar()
        super().__init__()

    def received(self, ctx: "aiopenapi3.plugin.Message.Context") -> "aiopenapi3.plugin.Message.Context":
        self.cookies.extract_cookies(Cookies._Response(ctx), Cookies._Request(ctx))
        return ctx

    def sending(self, ctx: "aiopenapi3.plugin.Message.Context") -> "aiopenapi3.plugin.Message.Context":
        self.cookies.add_cookie_header(Cookies._Request(ctx))
        return ctx
