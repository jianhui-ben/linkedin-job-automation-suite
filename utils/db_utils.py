import sqlite3
import logging
from tabulate import tabulate

logger = logging.getLogger(__name__)

DB_FILE = "linkedin_jobs.db"

def list_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

def query_table(table_name: str, limit: int = 5, truncate_desc: int = 80):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM "{table_name}" LIMIT ?;', (limit,))
    rows = cursor.fetchall()
    col_names = [desc[0] for desc in cursor.description]
    # Truncate job_description if present
    if "job_description" in col_names:
        idx = col_names.index("job_description")
        rows = [list(row) for row in rows]
        for row in rows:
            if row[idx] and len(row[idx]) > truncate_desc:
                row[idx] = row[idx][:truncate_desc] + "..."
    print(tabulate(rows, headers=col_names, tablefmt="fancy_grid"))
    conn.close()

def purge_table(table_name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}";')
    conn.commit()
    conn.close()
    logger.info(f"Table '{table_name}' has been purged (dropped).") 