import os
import shutil
import uuid
import base64
import time
import glob
import asyncio
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Security, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from starlette.requests import Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
import uvicorn

from backend.engines import LocalNudeNetDetector, LocalNSFWClassifier, ImageProcessor

# --- App Setup ---
app = FastAPI(title="NSFW Guard Pro")

# --- Rate Limiting ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Trust proxy headers from Cloudflare/Nginx ---
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# --- CORS (allow_credentials must be False when allow_origins=["*"]) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration ---
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
API_KEY = os.getenv("NSFW_API_KEY", "NSFW_PRO_8rqNo38SzYgZX86-byPnlZvvXzpiJL5rbE_TYIkbce8")
print(f"[NSFW Guard] API Key loaded: {API_KEY[:10]}...{API_KEY[-5:]}")

UPLOAD_DIR = "uploads"
PROCESSED_DIR = "processed"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# --- API Key Auth ---
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=True)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        print(f"[Auth] FAILED: received='{api_key[:8]}...' expected='{API_KEY[:8]}...'")
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

# --- AI Engine Singletons ---
_detector = None
_classifier = None
_processor = ImageProcessor()
MAX_CONCURRENCY = 2
process_semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

def get_engines():
    global _detector, _classifier
    if _detector is None:
        print("[NSFW Guard] Loading NudeNet Detector...")
        _detector = LocalNudeNetDetector()
    if _classifier is None:
        print("[NSFW Guard] Loading NSFW Classifier...")
        _classifier = LocalNSFWClassifier()
    return _detector, _classifier

# --- Cleanup ---
def cleanup_old_files():
    """Delete uploaded/processed files older than 24 hours."""
    now = time.time()
    for folder in [UPLOAD_DIR, PROCESSED_DIR]:
        for f in glob.glob(os.path.join(folder, "*")):
            try:
                if os.stat(f).st_mtime < now - 86400:
                    os.remove(f)
            except Exception:
                pass

# --- Core Processing ---
async def _handle_single_image(file_data, filename: str, mode: str, intensity: int, color: str, background_tasks: BackgroundTasks):
    """Processes a single image with concurrency control."""
    async with process_semaphore:
        file_id = str(uuid.uuid4())
        ext = os.path.splitext(filename)[1].lower()
        if ext not in {'.jpg', '.jpeg', '.png', '.webp'}:
            ext = '.jpg'

        input_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")

        # Write uploaded data to disk safely
        try:
            if hasattr(file_data, 'read'):
                with open(input_path, "wb") as buf:
                    shutil.copyfileobj(file_data, buf)
            else:
                with open(input_path, "wb") as buf:
                    buf.write(file_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

        file_size = os.path.getsize(input_path)
        print(f"[Process] Saved '{filename}' -> {input_path} ({file_size} bytes)")

        if file_size == 0:
            os.remove(input_path)
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Run AI engines
        det_engine, cls_engine = get_engines()
        scores = cls_engine.classify(input_path)
        detections = det_engine.detect(input_path)

        output_filename = f"processed_{file_id}{ext}"
        output_path = os.path.join(PROCESSED_DIR, output_filename)

        _processor.blur_radius = intensity
        _, blur_count = _processor.process(
            input_path, detections, output_path,
            mode=mode, nsfw_scores=scores, color_hex=color
        )

        # Schedule cleanup after returning response
        background_tasks.add_task(cleanup_old_files)

        return {
            "id": file_id,
            "filename": filename,
            "scores": scores,
            "detections": detections,
            "blur_count": blur_count,
            "processed_url": f"/api/files/{output_filename}?v={uuid.uuid4()}"
        }

# --- Endpoints ---
@app.post("/api/process")
async def process_image(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    mode: str = Form("blur"),
    intensity: int = Form(51),
    color: str = Form("#000000"),
    api_key: str = Depends(verify_api_key),
):
    # File size check
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_FILE_SIZE // 1024 // 1024}MB.")
    return await _handle_single_image(file.file, file.filename, mode, intensity, color, background_tasks)


@app.post("/api/process-batch")
async def process_batch(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    mode: str = Form("blur"),
    intensity: int = Form(51),
    color: str = Form("#000000"),
    api_key: str = Depends(verify_api_key),
):
    for f in files:
        f.file.seek(0, 2)
        size = f.file.tell()
        f.file.seek(0)
        if size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File '{f.filename}' too large.")

    tasks = [
        _handle_single_image(f.file, f.filename, mode, intensity, color, background_tasks)
        for f in files
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Convert exceptions to error dicts
    output = []
    for r in results:
        if isinstance(r, Exception):
            output.append({"error": str(r)})
        else:
            output.append(r)
    return {"results": output}


class ProcessRequest(BaseModel):
    image: str  # Base64
    mode: str = "blur"
    intensity: int = 51
    color: str = "#000000"
    return_base64: bool = False


@app.post("/api/process-base64")
async def process_base64(
    request: Request,
    background_tasks: BackgroundTasks,
    req: ProcessRequest,
    api_key: str = Depends(verify_api_key),
):
    if len(req.image) > MAX_FILE_SIZE * 1.4:
        raise HTTPException(status_code=413, detail="Base64 data too large.")

    async with process_semaphore:
        try:
            file_id = str(uuid.uuid4())
            input_path = os.path.join(UPLOAD_DIR, f"{file_id}.jpg")

            data = req.image
            if "," in data:
                data = data.split(",")[1]
            with open(input_path, "wb") as f:
                f.write(base64.b64decode(data))

            det_engine, cls_engine = get_engines()
            scores = cls_engine.classify(input_path)
            detections = det_engine.detect(input_path)

            output_filename = f"processed_{file_id}.jpg"
            output_path = os.path.join(PROCESSED_DIR, output_filename)

            _processor.blur_radius = req.intensity
            _, blur_count = _processor.process(
                input_path, detections, output_path,
                mode=req.mode, nsfw_scores=scores, color_hex=req.color
            )

            result = {"id": file_id, "scores": scores, "detections": detections, "blur_count": blur_count}

            if req.return_base64:
                with open(output_path, "rb") as img_file:
                    encoded = base64.b64encode(img_file.read()).decode()
                    result["processed_image"] = f"data:image/jpeg;base64,{encoded}"
            else:
                result["processed_url"] = f"/api/files/{output_filename}?v={uuid.uuid4()}"

            background_tasks.add_task(cleanup_old_files)
            return result

        except HTTPException:
            raise
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files/{filename}")
async def get_file(filename: str):
    # Security: prevent path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    path = os.path.join(PROCESSED_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path)


# Serve frontend
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
