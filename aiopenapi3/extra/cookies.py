from typing import Literal
import email.message
import http.cookiejar
import urllib.request

import aiopenapi3.plugin


class Cookies(aiopenapi3.plugin.Message, aiopenapi3.plugin.Init):
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
            if key.lower() == "cookie":
                name, _, value = value.partition("=")
                self.ctx.cookies[name] = value
            else:
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

    def __init__(
        self, cookiejar: http.cookiejar.CookieJar = None, policy: Literal["jar", "securitySchemes"] = "jar"
    ) -> None:
        self.cookiejar = cookiejar or http.cookiejar.CookieJar()
        self.policy = policy
        self.schemes: dict[str, str] = None
        super().__init__()

    def initialized(self, ctx: "aiopenapi3.plugin.Init.Context") -> "aiopenapi3.plugin.Init.Context":
        if self.policy in ["securitySchemes", "jar"]:
            self.schemes = {
                v.root.name: k
                for k, v in filter(
                    lambda x: (x[1].root.type.lower(), x[1].root.in_) == ("apikey", "cookie"),
                    self.api.components.securitySchemes.items(),
                )
            }
        else:
            raise ValueError(f"policy {self.policy} is not a valid policy")
        return ctx

    def received(self, ctx: "aiopenapi3.plugin.Message.Context") -> "aiopenapi3.plugin.Message.Context":
        response = Cookies._Response(ctx)
        request = Cookies._Request(ctx)

        cookies = self.cookiejar.make_cookies(response, request)

        for cookie in cookies:
            if not self.cookiejar._policy.set_ok(cookie, request):
                continue  # pragma: no cover

            if (ss := self.schemes.get(cookie.name)) is not None:
                self.api.authenticate(**{ss: cookie.value})
            elif self.policy == "jar":
                self.cookiejar.set_cookie(cookie)

        return ctx

    def sending(self, ctx: "aiopenapi3.plugin.Message.Context") -> "aiopenapi3.plugin.Message.Context":
        if self.policy == "jar":
            self.cookiejar.add_cookie_header(Cookies._Request(ctx))
        elif self.policy == "securitySchemes":
            # authentication will take care
            pass
        return ctx
