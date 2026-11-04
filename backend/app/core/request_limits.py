from starlette.responses import JSONResponse


class BodyTooLarge(Exception):
    pass


class RequestSizeLimit:
    """Bound the entire multipart request, including chunked requests, before spooling."""
    def __init__(self, app, maximum):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        response = JSONResponse({"detail": "Request too large"}, status_code=413)
        lengths = [v for k, v in scope.get("headers", []) if k == b"content-length"]
        try:
            if lengths and int(lengths[0]) > self.maximum:
                return await response(scope, receive, send)
        except ValueError:
            return await JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)(scope, receive, send)
        total = 0

        async def bounded_receive():
            nonlocal total
            message = await receive()
            total += len(message.get("body", b""))
            if total > self.maximum:
                raise BodyTooLarge()
            return message

        # Frameworks may turn receive errors into 400 responses; consistently return 413.
        async def bounded_send(message):
            if total > self.maximum:
                raise BodyTooLarge()
            await send(message)

        try:
            await self.app(scope, bounded_receive, bounded_send)
        except BodyTooLarge:
            await response(scope, receive, send)
