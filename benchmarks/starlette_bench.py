from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route


def hello(request):
    return JSONResponse({"message": "Hello, World!"})

def plaintext(request):
    return PlainTextResponse("Hello, World!")

app = Starlette(routes=[
    Route("/", hello),
    Route("/plaintext", plaintext),
])
