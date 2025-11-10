from fastapi import FastAPI

app = FastAPI(title="Todo App")

# Simple health check route
@app.get("/health")
async def health_check():
    return {"status": "ok"}
