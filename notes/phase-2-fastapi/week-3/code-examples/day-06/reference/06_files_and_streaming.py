import os
import time
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse

app = FastAPI()

# 1. File Response
@app.get("/download-file")
async def download_file():
    """
    Generates a temporary file and serves it.
    """
    file_path = "example.txt"
    with open(file_path, "w") as f:
        f.write("This is a downloadable text file created by FastAPI.")
    
    # media_type tells the browser how to handle it
    # filename forces the browser to download it as "readme.txt"
    return FileResponse(
        path=file_path, 
        filename="readme.txt", 
        media_type="text/plain"
    )

# 2. Streaming Response
@app.get("/stream-data")
async def stream_data():
    """
    Streams data line-by-line.
    Try curling this endpoint: curl http://localhost:8000/stream-data
    """
    def iter_file():
        for i in range(5):
            yield f"Data chunk {i}\n"
            time.sleep(1) # Simulate slow processing

    return StreamingResponse(iter_file(), media_type="text/plain")

# 3. Stream a Video (Fake) or Large Binary
@app.get("/stream-binary")
async def stream_binary():
    def iter_binary():
        # Yield 1024 bytes of '0's repeatedly
        for _ in range(10):
            yield b"0" * 1024
    
    return StreamingResponse(iter_binary(), media_type="application/octet-stream")