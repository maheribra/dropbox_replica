import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from routes import auth, files, directories, sharing

app = FastAPI(
    title="Dropbox Replica",
    description="Backend for cloud storage assignment",
    version="1.0.0"
)

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(exist_ok=True)

# API Routes
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(directories.router)
app.include_router(sharing.router)

# Static files and Frontend
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        return {"error": "index.html missing from static folder"}
    return FileResponse(index_path)

@app.get("/api/health")
async def health_check():
    return {"status": "online", "message": "Server is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)