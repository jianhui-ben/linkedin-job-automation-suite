import logging
import sys
from utils import db_utils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    if len(sys.argv) < 2:
        print("Usage: python query_client.py [list|query|purge] [table_name] [limit]")
        return
    action = sys.argv[1]
    if action == "list":
        tables = db_utils.list_tables()
        print("\nTables in the database:")
        for t in tables:
            print(f"- {t}")
    elif action == "query":
        if len(sys.argv) < 3:
            print("Usage: python query_client.py query [table_name] [limit]")
            return
        table = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        db_utils.query_table(table, limit)
    elif action == "purge":
        if len(sys.argv) < 3:
            print("Usage: python query_client.py purge [table_name]")
            return
        table = sys.argv[2]
        db_utils.purge_table(table)
    else:
        print("Unknown action. Use list, query, or purge.")

if __name__ == "__main__":
    main()
