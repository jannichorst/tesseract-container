import asyncio
import json
import logging
import os
import platform
import shutil
import sqlite3
import subprocess
# import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime  # timedelta
from io import BytesIO
from typing import Any, Dict

# import psutil
import pytesseract
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pdf2image import convert_from_bytes
from PIL import Image

from app.database import (
    check_db_operations,
    create_job,
    init_db,
    save_ocr_results,
    update_job,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")
logger.propagate = False

# Variables
DB_PATH = "app/ocr_results.db"
PORT = 8000
HOST = "0.0.0.0"
tmp_dir = "/tmp"

available_languages = pytesseract.get_languages(config="")


async def process_file(
    contents, task_id: str, lang: str, dpi: int | None, psm: int, config: str | None
):
    await asyncio.sleep(0)  # Yield control to the event loop
    result_info: Dict[str, Any] = {
        "pages": [],
        "file_type": "PDF" if contents[:4] == b"%PDF" else "Image",
        "used_dpi": dpi,
    }
    update_job(
        DB_PATH,
        task_id,
        {
            "status": "processing",
            "psm_type": psm,
            "dpi": dpi,
            "file_type": result_info["file_type"],
        },
    )

    try:
        if contents[:4] == b"%PDF":  # Check if the file is a PDF
            if dpi:
                images = convert_from_bytes(contents, dpi=dpi)
            else:
                images = convert_from_bytes(contents)
        else:
            pil_image = Image.open(BytesIO(contents))
            images = [pil_image]

        ocr_data = []

        for page_num, image in enumerate(images, start=1):
            image = image.convert("RGB")

            custom_config = f"-l {lang} --psm {psm}"
            if dpi:
                custom_config += f" --dpi {dpi}"
            if config and config.startswith("--"):
                custom_config += f" {config}"

            # Perform OCR on the image
            data = pytesseract.image_to_data(
                image, config=custom_config, output_type=pytesseract.Output.DICT
            )

            page_data = {"data": data, "page_num": page_num}
            ocr_data.append(page_data)

            # Add page info to result_info
            width, height = image.size
            result_info["pages"].append(
                {"page_num": page_num, "width": width, "height": height}
            )

        save_ocr_results(DB_PATH, ocr_data, task_id)
        update_job(
            DB_PATH,
            task_id,
            {
                "end_datetime": datetime.now().isoformat(),
                "status": "completed",
                "num_pages": len(images),
                "page_info": json.dumps(result_info["pages"]),
            },
        )

    except Exception as e:
        update_job(
            DB_PATH,
            task_id,
            {
                "end_datetime": datetime.now().isoformat(),
                "status": "failed",
                "error_message": f"Failed to process image: {e}",
            },
        )
        raise e

    return result_info


async def generate_pdf(contents, task_id, lang, dpi, psm, config):
    await asyncio.sleep(0)  # Yield control to the event loop
    pil_image = Image.open(BytesIO(contents))

    custom_config = f"-l {lang} --psm {psm}"
    if dpi:
        custom_config += f" --dpi {dpi}"
    if config and config.startswith("--"):
        custom_config += f" {config}"

    pdf = pytesseract.image_to_pdf_or_hocr(
        pil_image, config=custom_config, extension="pdf"
    )
    pdf_path = f"{tmp_dir}/{task_id}.pdf"
    with open(pdf_path, "wb") as f:
        f.write(pdf)
    return pdf_path


def delete_file(path: str):
    os.remove(path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db(DB_PATH, logger)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.post(
    "/ocr/",
    summary="Perform OCR [SYNC]",
    description="This endpoint performs OCR processing synchronously and returns the result immediately.",
)
async def perform_ocr(
    file: UploadFile = File(...),
    lang: str = "eng",
    dpi: int | None = None,
    config: str | None = None,
    psm: int = 3,
):
    # Common validation logic
    if lang not in available_languages:
        return JSONResponse(
            content={
                "error": "Specified language is not available",
                "available_languages": available_languages,
            },
            status_code=400,
        )

    if dpi is not None and dpi <= 0:
        return JSONResponse(
            content={"error": "DPI must be more than 0"}, status_code=400
        )

    valid_psm_values = [3, 4, 5, 6, 8, 9, 10, 11, 12, 13]
    if psm not in valid_psm_values:
        return JSONResponse(
            content={"error": f"Invalid PSM value. Must be one of: {valid_psm_values}"},
            status_code=400,
        )

    if config and not config.startswith("--"):
        return JSONResponse(
            content={"error": "Config must start with '--'"}, status_code=400
        )

    # Create a new job in the database
    contents = await file.read()
    task_id = str(uuid.uuid4())
    start_datetime = datetime.now().isoformat()
    create_job(DB_PATH, task_id, str(file.filename), start_datetime=start_datetime)

    try:
        result_info: Dict[str, Any] = {
            "pages": [],
            "file_type": "PDF" if contents[:4] == b"%PDF" else "Image",
            "used_dpi": dpi,
        }
        update_job(
            DB_PATH,
            task_id,
            {
                "status": "processing",
                "psm_type": psm,
                "dpi": dpi,
                "file_type": result_info["file_type"],
            },
        )

        if contents[:4] == b"%PDF":  # Check if the file is a PDF
            if dpi:
                images = convert_from_bytes(contents, dpi=dpi)
            else:
                images = convert_from_bytes(contents)
        else:
            pil_image = Image.open(BytesIO(contents))
            images = [pil_image]

        ocr_data = []
        for page_num, image in enumerate(images, start=1):
            image = image.convert("RGB")

            custom_config = f"-l {lang} --psm {psm}"
            if dpi:
                custom_config += f" --dpi {dpi}"
            if config and config.startswith("--"):
                custom_config += f" {config}"

            # Perform OCR on the image
            data = pytesseract.image_to_data(
                image, config=custom_config, output_type=pytesseract.Output.DICT
            )

            page_data = {"data": data, "page_num": page_num}
            ocr_data.append(page_data)

            # Add page info to result_info
            width, height = image.size
            result_info["pages"].append(
                {"page_num": page_num, "width": width, "height": height}
            )

        save_ocr_results(DB_PATH, ocr_data, task_id)
        end_datetime = datetime.now().isoformat()
        update_job(
            DB_PATH,
            task_id,
            {
                "end_datetime": end_datetime,
                "status": "completed",
                "num_pages": len(images),
                "page_info": json.dumps(result_info["pages"]),
            },
        )

        results = []
        for data in ocr_data:
            for i in range(len(data["data"]["level"])):
                results.append(
                    {
                        "level": data["data"]["level"][i],
                        "page_num": data["data"]["page_num"][i],
                        "block_num": data["data"]["block_num"][i],
                        "par_num": data["data"]["par_num"][i],
                        "line_num": data["data"]["line_num"][i],
                        "word_num": data["data"]["word_num"][i],
                        "left": data["data"]["left"][i],
                        "top": data["data"]["top"][i],
                        "width": data["data"]["width"][i],
                        "height": data["data"]["height"][i],
                        "conf": data["data"]["conf"][i],
                        "text": data["data"]["text"][i],
                    }
                )

        response = {
            "task_id": task_id,
            "file_name": str(file.filename),
            "file_type": result_info["file_type"],
            "num_pages": len(images),
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "status": "completed",
            "dpi": dpi,
            "page_info": result_info["pages"],
            "psm_type": psm,
            "results": results,
        }

        return JSONResponse(content=response)

    except Exception as e:
        end_datetime = datetime.now().isoformat()
        update_job(
            DB_PATH,
            task_id,
            {
                "end_datetime": end_datetime,
                "status": "failed",
                "error_message": f"Failed to process file: {e}",
            },
        )
        raise HTTPException(status_code=500, detail=f"Failed to process file: {e}")


@app.post(
    "/start_ocr/",
    summary="Starts OCR processing [ASYNC]",
    description="This endpoint starts OCR processing and returns a task_id.",
)
async def start_ocr_processing(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    lang: str = "eng",
    dpi: int | None = None,
    config: str | None = None,
    psm: int = 3,
):
    # Common validation logic
    if lang not in available_languages:
        return JSONResponse(
            content={
                "error": "Specified language is not available",
                "available_languages": available_languages,
            },
            status_code=400,
        )

    if dpi is not None and dpi <= 0:
        return JSONResponse(
            content={"error": "DPI must be more than 0"}, status_code=400
        )

    valid_psm_values = [0, 1, 2, 3, 4, 6, 8, 9, 11, 12, 13]
    if psm not in valid_psm_values:
        return JSONResponse(
            content={"error": f"Invalid PSM value. Must be one of: {valid_psm_values}"},
            status_code=400,
        )

    if config and not config.startswith("--"):
        return JSONResponse(
            content={"error": "Config must start with '--'"}, status_code=400
        )

    # Create a new job in the database
    contents = await file.read()
    task_id = str(uuid.uuid4())
    create_job(
        DB_PATH, task_id, str(file.filename), start_datetime=datetime.now().isoformat()
    )

    # Process the image in the background
    background_tasks.add_task(process_file, contents, task_id, lang, dpi, psm, config)
    return JSONResponse(content={"task_id": task_id})


@app.get(
    "/results/{task_id}",
    summary="Get Results",
    description="Retrieve results with a task_id.",
)
async def get_result(task_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get job info
    cursor.execute(
        """ SELECT file_name, file_type, num_pages, start_datetime, end_datetime,
                    status, dpi, page_info, psm_type, error_message
             FROM jobs WHERE uuid = ? """,
        (task_id,),
    )
    job_row = cursor.fetchone()

    if not job_row:
        conn.close()
        raise HTTPException(status_code=404, detail="task_id not found")

    (
        file_name,
        file_type,
        num_pages,
        start_datetime,
        end_datetime,
        status,
        dpi,
        page_info,
        psm_type,
        error_message,
    ) = job_row

    # Get OCR results
    cursor.execute(
        """ SELECT level, page_num, block_num, par_num, line_num,
                    word_num, left, top, width, height, conf,
                    text FROM ocr_results WHERE uuid = ? """,
        (task_id,),
    )
    ocr_rows = cursor.fetchall()
    conn.close()

    if status == "completed":
        results = []
        for row in ocr_rows:
            results.append(
                {
                    "level": row[0],
                    "page_num": row[1],
                    "block_num": row[2],
                    "par_num": row[3],
                    "line_num": row[4],
                    "word_num": row[5],
                    "left": row[6],
                    "top": row[7],
                    "conf": row[8],
                    "text": row[9],
                }
            )

        response = {
            "state": "SUCCESS",
            "file_name": file_name,
            "file_type": file_type,
            "num_pages": num_pages,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "status": status,
            "dpi": dpi,
            "page_info": json.loads(page_info) if page_info else None,
            "psm_type": psm_type,
            "results": results,
        }
    elif status == "failed":
        response = {
            "state": "FAILED",
            "status": status,
            "file_name": file_name,
            "file_type": file_type,
            "num_pages": num_pages,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "dpi": dpi,
            "page_info": json.loads(page_info) if page_info else None,
            "psm_type": psm_type,
            "error_message": error_message,
        }
    elif status == "running":
        response = {
            "state": "RUNNING",
            "status": status,
            "file_name": file_name,
            "file_type": file_type,
            "num_pages": num_pages,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "dpi": dpi,
            "page_info": json.loads(page_info) if page_info else None,
            "psm_type": psm_type,
            "error_message": error_message,
        }
    else:
        response = {
            "state": "PENDING",
            "status": status,
            "file_name": file_name,
            "file_type": file_type,
            "num_pages": num_pages,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "dpi": dpi,
            "page_info": json.loads(page_info) if page_info else None,
            "psm_type": psm_type,
        }

    return JSONResponse(content=response)


@app.post(
    "/create_searchable/",
    summary="Create Searchable PDF [SYNC]",
    description="Creates a searchable PDF from an image or PDF file. The result is returned as a downloadable PDF file.",
)
async def generate_searchable_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    lang: str = "eng",
    dpi: int | None = None,
    psm: int = 3,
    config: str | None = None,
):
    if lang not in available_languages:
        return JSONResponse(
            content={"error": "Specified language is not available"}, status_code=400
        )

    if dpi is not None and dpi <= 0:
        return JSONResponse(
            content={"error": "DPI must be more than 0"}, status_code=400
        )

    if psm not in [0, 1, 2, 3, 4, 6, 8, 9, 11, 12, 13]:
        return JSONResponse(content={"error": "Invalid PSM value"}, status_code=400)

    if config and not config.startswith("--"):
        return JSONResponse(
            content={"error": "Config must start with '--'"}, status_code=400
        )

    contents = await file.read()
    task_id = str(uuid.uuid4())  # Generate a new UUID for each task
    pdf_path = await generate_pdf(contents, task_id, lang, dpi, psm, config)

    # Schedule the deletion of the PDF file after response
    background_tasks.add_task(delete_file, pdf_path)

    return FileResponse(
        path=pdf_path, filename=f"{file.filename}_ocr.pdf", media_type="application/pdf"
    )


@app.get(
    "/jobs", summary="Get Jobs", description="Retrieve all jobs or filter by status."
)
async def get_jobs(status: str = "pending"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get job counts
    cursor.execute(
        "SELECT COUNT(*) FROM jobs WHERE status IN ('pending', 'processing')"
    )
    waiting_jobs_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'completed'")
    completed_jobs_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'failed'")
    failed_jobs_count = cursor.fetchone()[0]

    if status == "all":
        cursor.execute(
            """SELECT uuid, file_name, start_datetime, status, psm_type, end_datetime, error_message
                FROM jobs"""
        )
    elif status == "failed":
        cursor.execute(
            """SELECT uuid, file_name, start_datetime, status, psm_type, end_datetime, error_message
                FROM jobs WHERE status = 'failed'"""
        )
    elif status == "completed":
        cursor.execute(
            """SELECT uuid, file_name, start_datetime, status, psm_type, end_datetime, error_message
                FROM jobs WHERE status = 'completed'"""
        )
    else:
        cursor.execute(
            """SELECT uuid, file_name, start_datetime, status, psm_type, end_datetime, error_message
                FROM jobs WHERE status IN ('pending', 'processing')"""
        )

    jobs = cursor.fetchall()
    conn.close()

    response = []
    for job in jobs:
        job_info = {
            "id": job[0],
            "file_name": job[1],
            "start_datetime": job[2],
            "end_datetime": job[5],
            "status": job[3],
            "psm_type": job[4],
            "message": job[6],
        }
        response.append(job_info)

    return JSONResponse(
        content={
            "queue": waiting_jobs_count,
            "completed": completed_jobs_count,
            "failed": failed_jobs_count,
            "jobs": response,
        }
    )


@app.get(
    "/info",
    summary="Get System Information",
    description="Retrieve system information.",
)
async def get_info():
    # Get available Tesseract languages
    available_languages = pytesseract.get_languages(config="")

    # Get Python version
    python_version = platform.python_version()

    # Get Tesseract version
    try:
        tesseract_version_output = subprocess.run(
            ["tesseract", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        tesseract_version = tesseract_version_output.stdout.splitlines()[0]
    except Exception as e:
        tesseract_version = f"Error retrieving Tesseract version: {e}"

    # Get operating system information
    os_info = platform.platform()

    # Get system architecture
    architecture = platform.architecture()[0]

    """ # Get CPU information
    cpu_info = {
        "Model": platform.processor(),
        "Physical Cores": psutil.cpu_count(logical=False),
        "Total Cores": psutil.cpu_count(logical=True),
    }

    # Get memory information
    svmem = psutil.virtual_memory()
    memory_info = {
        "Total": f"{svmem.total / (1024 ** 3):.2f} GB",
        "Available": f"{svmem.available / (1024 ** 3):.2f} GB",
        "Used": f"{svmem.used / (1024 ** 3):.2f} GB",
        "Percentage": f"{svmem.percent} %",
    }

    # Get disk usage
    partition = psutil.disk_partitions()[0]
    disk_usage = psutil.disk_usage(partition.mountpoint)
    disk_info = {
        "Total": f"{disk_usage.total / (1024 ** 3):.2f} GB",
        "Free": f"{disk_usage.free / (1024 ** 3):.2f} GB",
        "Used": f"{disk_usage.used / (1024 ** 3):.2f} GB",
        "Percentage": f"{disk_usage.percent} %",
    }

    # Get system uptime
    uptime_seconds = time.time() - psutil.boot_time()
    uptime_string = str(timedelta(seconds=int(uptime_seconds))) """

    # Get current time
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return JSONResponse(
        content={
            "Installed Tesseract Languages": available_languages,
            "Python Version": python_version,
            "Tesseract Version": tesseract_version,
            "OS Information": os_info,
            "System Architecture": architecture,
            #"CPU Information": cpu_info,
            #"Memory Information": memory_info,
            #"Disk Information": disk_info,
            #"System Uptime": uptime_string,
            "Current Time": current_time,
        }
    )


@app.get(
    "/health", summary="Health Check", description="Perform a system health check."
)
async def health_check():
    try:
        # Check Tesseract availability
        result = subprocess.run(
            ["tesseract", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
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
                    raise HTTPException(
                        status_code=500,
                        detail=f"""Health check failed:
                                         Database file found at {found_path},
                                         but not at the expected location. """,
                    )
            else:
                raise FileNotFoundError("Database file not found")

        # Easy DB connection check
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.commit()
            conn.close()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Could not connect to database: {e}"
            )

        # Check database connection and operations
        check_db_operations(DB_PATH)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")

    return JSONResponse(content={"status": "healthy"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
