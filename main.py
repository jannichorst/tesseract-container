from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import pytesseract
import sqlite3
import asyncio
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
import subprocess
#import psutil
import shutil
import os


from src.database import init_db

app = FastAPI()

DATABASE_URL = 'ocr_results.db'

async def process_image(contents, task_id):
    await asyncio.sleep(0)  # Yield control to the event loop
    npimg = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    height, width = image.shape[:2]
    
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    
    conn = sqlite3.connect(DATABASE_URL)
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
    init_db(DATABASE_URL)
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/upload/")
async def upload_image(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    contents = await file.read()
    task_id = str(uuid.uuid4())  # Generate a new UUID for each task
    start_datetime = datetime.now().isoformat()
    
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO jobs (uuid, file_name, start_datetime, status) VALUES (?, ?, ?, ?)',
                   (task_id, file.filename, start_datetime, 'in_progress'))
    conn.commit()
    conn.close()
    
    background_tasks.add_task(process_image, contents, task_id)
    return JSONResponse(content={"task_id": task_id})

@app.get("/result/{task_id}")
async def get_result(task_id: str):
    conn = sqlite3.connect(DATABASE_URL)
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
        # Check database connection
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        conn.close()

        # Check Tesseract availability
        result = subprocess.run(['tesseract', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="Tesseract is not available")

        # Check disk space
        total, used, free = shutil.disk_usage("/")
        if free < 1 * 1024 * 1024 * 1024:  # Less than 1GB free space
            raise HTTPException(status_code=500, detail="Not enough disk space")

        """ # Check CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        if cpu_usage > 90:  # CPU usage above 90%
            raise HTTPException(status_code=500, detail="High CPU usage")

        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.available < 100 * 1024 * 1024:  # Less than 100MB available
            raise HTTPException(status_code=500, detail="Low memory available")
 """

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")
    
    return JSONResponse(content={"status": "healthy"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
