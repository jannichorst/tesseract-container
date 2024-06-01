import logging
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import pytesseract
import sqlite3
import asyncio
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
import subprocess
import shutil
import os
from PIL import Image
from io import BytesIO
from app.database import init_db, check_db_operations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")
logger.propagate = False

# Variables
DB_PATH = 'app/ocr_results.db'
PORT = 8000
HOST = '0.0.0.0'

def list_directory_structure(start_path="."):
    directory_structure = {}
    for root, dirs, files in os.walk(start_path):
        folder = os.path.relpath(root, start_path)
        subdir = directory_structure
        if folder != ".":
            for part in folder.split(os.sep):
                subdir = subdir.setdefault(part, {})
        subdir["files"] = files
    return directory_structure

async def process_image(contents, task_id):
    await asyncio.sleep(0)  # Yield control to the event loop
    pil_image = Image.open(BytesIO(contents))
        
    width, height = pil_image.size
    
    # Ensure the image is in RGB mode
    pil_image = pil_image.convert("RGB")
    
    data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for i in range(len(data['level'])):
        cursor.execute('''
        INSERT INTO ocr_results (
            uuid, level, page_num, block_num, par_num,
            line_num, word_num, left, top, width, height,
            conf, text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_id, data['level'][i], data['page_num'][i], data['block_num'][i],
            data['par_num'][i], data['line_num'][i], data['word_num'][i],
            data['left'][i], data['top'][i], data['width'][i], data['height'][i],
            data['conf'][i], data['text'][i]
        ))
    
    cursor.execute('''
    UPDATE jobs
    SET end_datetime = ?, status = ?, width = ?, height = ?
    WHERE uuid = ?
    ''', (datetime.now().isoformat(), 'completed', width, height, task_id))
    
    conn.commit()
    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db(DB_PATH, logger)
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/analyzeDocument/")
async def upload_image(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # TODO: Validate file type and size

    contents = await file.read()
    task_id = str(uuid.uuid4())  # Generate a new UUID for each task
    start_datetime = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO jobs (uuid, file_name, start_datetime, status) VALUES (?, ?, ?, ?)',
                   (task_id, file.filename, start_datetime, 'in_progress'))
    conn.commit()
    conn.close()
    
    background_tasks.add_task(process_image, contents, task_id)
    return JSONResponse(content={"task_id": task_id})

@app.get("/analyzeResults/{task_id}")
async def get_result(task_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get job info
    cursor.execute('SELECT file_name, start_datetime, end_datetime, status, width, height FROM jobs WHERE uuid = ?', (task_id,))
    job_row = cursor.fetchone()
    
    if not job_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    
    file_name, start_datetime, end_datetime, status, width, height = job_row
    
    # Get OCR results
    cursor.execute('SELECT level, page_num, block_num, par_num, line_num, word_num, left, top, width, height, conf, text FROM ocr_results WHERE uuid = ?', (task_id,))
    ocr_rows = cursor.fetchall()
    conn.close()
    
    if status == 'completed':
        results = []
        for row in ocr_rows:
            results.append({
                'level': row[0],
                'page_num': row[1],
                'block_num': row[2],
                'par_num': row[3],
                'line_num': row[4],
                'word_num': row[5],
                'left': row[6],
                'top': row[7],
                'width': row[8],
                'height': row[9],
                'conf': row[10],
                'text': row[11],
            })
        
        response = {
            "state": "SUCCESS",
            "file_name": file_name,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "status": status,
            "width": width,
            "height": height,
            "results": results
        }
    else:
        response = {
            "state": "PENDING",
            "status": status,
            "file_name": file_name,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "width": width,
            "height": height
        }
    
    return JSONResponse(content=response)

@app.get("/health")
async def health_check():
    try:
        # Check Tesseract availability
        result = subprocess.run(['tesseract', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="Tesseract is not available")

        # Check disk space
        total, used, free = shutil.disk_usage("/")
        if free < 1 * 1024 * 1024 * 1024:  # Less than 1GB free space
            raise HTTPException(status_code=500, detail="Not enough disk space")
        
        # Check if db file exists
        if not os.path.exists(DB_PATH):
            for root, dirs, files in os.walk("."):
                if "ocr_results.db" in files:
                    found_path = os.path.join(root, "ocr_results.db")
                    raise HTTPException(status_code=500, detail=f"Health check failed: Database file found at {found_path}, but not at the expected location.")
            else:
                raise FileNotFoundError("Database file not found")

                # Check database connection
        
        # Easy DB connection check
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            conn.commit()
            conn.close()
        except Exception as e:
            raise HTTPException(status_code=500, detail="Could not connect to database.")

        # Check database connection and operations
        check_db_operations(DB_PATH)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")
    
    return JSONResponse(content={"status": "healthy"})

@app.get("/fs")
async def file_system_structure():
    try:
        structure = list_directory_structure()
        return JSONResponse(content=structure)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list file system structure: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)