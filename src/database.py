import sqlite3

def init_db(database_url):
    conn = sqlite3.connect(database_url)
    cursor = conn.cursor()
    
    # Create jobs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        uuid TEXT PRIMARY KEY,
        file_name TEXT,
        start_datetime TEXT,
        end_datetime TEXT,
        status TEXT,
        width INTEGER,
        height INTEGER
    )
    ''')
    
    # Create ocr_results table with foreign key to jobs table
    cursor.execute('''
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
    ''')
    
    conn.commit()
    conn.close()

