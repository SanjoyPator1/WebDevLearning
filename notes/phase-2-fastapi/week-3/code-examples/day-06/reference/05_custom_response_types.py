from fastapi import FastAPI, Response
from fastapi.responses import (
    HTMLResponse, 
    PlainTextResponse, 
    RedirectResponse, 
    JSONResponse
)

app = FastAPI()

@app.get("/html", response_class=HTMLResponse)
async def read_html():
    return """
    <html>
        <head><title>FastAPI Day 6</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is direct HTML!</p>
        </body>
    </html>
    """

@app.get("/text", response_class=PlainTextResponse)
async def read_text():
    return "Just some raw text. No JSON quotes here."

@app.get("/legacy")
async def read_legacy():
    # Redirect to the new text endpoint
    return RedirectResponse(url="/text")

@app.get("/headers")
async def read_headers(response: Response):
    """
    Adding custom headers to the response.
    Useful for Caching, Security, or Custom metadata.
    """
    response.headers["X-Custom-Header"] = "MySecretValue"
    response.headers["Cache-Control"] = "max-age=3600"
    return {"message": "Check the headers in your inspector"}