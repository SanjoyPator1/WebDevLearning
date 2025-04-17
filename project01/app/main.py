from fastapi import FastAPI

app = FastAPI(
    title="My FastAPI Application",
    description="A sample FastAPI application",
    version="0.1.0",
)

@app.get("/")
async def root():
    return {"message": "Hello, FastAPI!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
