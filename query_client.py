import sqlite3
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_FILE = "linkedin_jobs.db"

def list_tables():
    """Lists all tables in the database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if tables:
            logger.info("Tables in the database:")
            for table in tables:
                print(f"- {table[0]}")
        else:
            logger.info("No tables found in the database.")
    except sqlite3.Error as e:
        logger.error(f"Error listing tables: {e}")
    finally:
        if conn:
            conn.close()

def query_table(table_name: str, limit: int = 5):
    """Queries a specific table and prints a few rows."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if table exists to prevent SQL injection in table name
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?;", (table_name,))
        if cursor.fetchone() is None:
            logger.warning(f"Table '{table_name}' does not exist.")
            return

        query = f'SELECT job_id, url, job_title, company_name FROM "{table_name}" LIMIT ?;'
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        if rows:
            column_names = [description[0] for description in cursor.description]
            logger.info(f"Data from table '{table_name}' (first {limit} rows):")
            print(column_names)
            for row in rows:
                print(row)
        else:
            logger.info(f"No data found in table '{table_name}'.")
    except sqlite3.Error as e:
        logger.error(f"Error querying table '{table_name}': {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        logger.warning(f"Database file '{DB_FILE}' not found. Run the scraper first.")
    else:
        list_tables()
        # # Example usage: Replace with the actual table name after a scrape run
        # # query_table("jobs_product_manager_United_States_20240101_120000") 
        # logger.info("\nTo query a specific table, call query_table('YOUR_TABLE_NAME') and replace 'YOUR_TABLE_NAME'.")
        # logger.info("The table name will be logged by the scraper when it creates it.")
        query_table("jobs_product_manager_United_States")
