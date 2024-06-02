import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException


class DatabaseConnection:
    _instance: Optional[sqlite3.Connection] = None

    @classmethod
    def get_instance(cls, db_path: str) -> sqlite3.Connection:
        if cls._instance is None:
            cls._instance = sqlite3.connect(
                db_path, timeout=30, check_same_thread=False
            )
            cls._instance.row_factory = sqlite3.Row
            cls.enable_wal_mode(cls._instance)
        return cls._instance

    @staticmethod
    def enable_wal_mode(conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        conn.commit()


def init_db(db_path: str, logger: logging.Logger) -> None:
    conn = DatabaseConnection.get_instance(db_path)
    cursor = conn.cursor()

    # Create jobs table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS jobs (
        uuid TEXT PRIMARY KEY,
        file_name TEXT,
        file_type TEXT,
        num_pages INTEGER,
        start_datetime TEXT,
        end_datetime TEXT,
        status TEXT,
        dpi INTEGER,
        page_info TEXT,
        psm_type INTEGER,
        error_message TEXT
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

    logger.info(f"Database initialized at {db_path}")
    print(f"Database initialized at {db_path}")


def check_db_operations(db_path: str) -> None:
    try:
        conn = DatabaseConnection.get_instance(db_path)
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
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database operation check failed: {e}"
        )


def create_job(db_path: str, task_id: str, file_name: str, start_datetime: str) -> None:
    sql = """
    INSERT INTO jobs (uuid, file_name, start_datetime, status)
    VALUES (?, ?, ?, ?)
    """
    values = (task_id, file_name, start_datetime, "pending")

    conn = DatabaseConnection.get_instance(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(sql, values)
        conn.commit()
    except sqlite3.Error as e:
        raise Exception(f"Failed to create job with id: {task_id}: {e}")


def update_job(db_path: str, task_id: str, fields: Dict[str, Any]) -> None:
    if not fields:
        raise ValueError("No fields to update provided.")

    set_clause = ", ".join([f"{key} = ?" for key in fields.keys()])
    values = list(fields.values()) + [task_id]

    sql = f"""
    UPDATE jobs
    SET {set_clause}
    WHERE uuid = ?
    """

    conn = DatabaseConnection.get_instance(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(sql, values)
        conn.commit()
    except sqlite3.Error as e:
        raise Exception(f"Failed to update job with id: {task_id}: {e}")


def save_ocr_results(
    db_path: str, all_data: List[Dict[str, Any]], task_id: str
) -> None:
    conn = DatabaseConnection.get_instance(db_path)
    cursor = conn.cursor()

    for page in all_data:
        data = page["data"]
        page_num = page["page_num"]

        for i in range(len(data["level"])):
            cursor.execute(
                """
            INSERT INTO ocr_results (
                uuid, level, page_num, block_num, par_num,
                line_num, word_num, left, top, width, height,
                conf, text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    task_id,
                    data["level"][i],
                    page_num,
                    data["block_num"][i],
                    data["par_num"][i],
                    data["line_num"][i],
                    data["word_num"][i],
                    data["left"][i],
                    data["top"][i],
                    data["width"][i],
                    data["height"][i],
                    data["conf"][i],
                    data["text"][i],
                ),
            )

    conn.commit()
