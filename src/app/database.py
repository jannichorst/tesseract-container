import sqlite3
import uuid
from datetime import datetime

from fastapi import HTTPException


def init_db(database_url, logger):
    conn = sqlite3.connect(database_url)
    cursor = conn.cursor()

    # Create jobs table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS jobs (
        uuid TEXT PRIMARY KEY,
        file_name TEXT,
        start_datetime TEXT,
        end_datetime TEXT,
        status TEXT,
        width INTEGER,
        height INTEGER
    )
    """
    )

    # Create ocr_results table with foreign key to jobs table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS ocr_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT,
        level INTEGER,
        page_num INTEGER,
        block_num INTEGER,
        par_num INTEGER,
        line_num INTEGER,
        word_num INTEGER,
        left INTEGER,
        top INTEGER,
        width INTEGER,
        height INTEGER,
        conf INTEGER,
        text TEXT,
        FOREIGN KEY (uuid) REFERENCES jobs(uuid)
    )
    """
    )

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at {database_url}")
    print(f"Database initialized at {database_url}")


def check_db_operations(DB_PATH):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Insert a test entry
        test_uuid = str(uuid.uuid4())
        cursor.execute(
            """INSERT INTO jobs (uuid, file_name, start_datetime,
                       status) VALUES (?, ?, ?, ?)""",
            (test_uuid, "test_file", datetime.now().isoformat(), "test_status"),
        )

        # Verify insertion
        cursor.execute("SELECT * FROM jobs WHERE uuid = ?", (test_uuid,))
        if cursor.fetchone() is None:
            raise Exception("Test insertion failed")

        # Delete the test entry
        cursor.execute("DELETE FROM jobs WHERE uuid = ?", (test_uuid,))

        # Verify deletion
        cursor.execute("SELECT * FROM jobs WHERE uuid = ?", (test_uuid,))
        if cursor.fetchone() is not None:
            raise Exception("Test deletion failed")

        conn.commit()
        conn.close()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database operation check failed: {e}"
        )
