import sqlite3
import os

db_file_name = 'data.db'
sql_script_path = 'db_queries.sql' # Your .sql file path

try:
    conn = sqlite3.connect(db_file_name)
    cursor = conn.cursor()
    print(f"Connected to '{db_file_name}'.")

    # 1. Open and read the .sql file
    if os.path.exists(sql_script_path):
        with open(sql_script_path, 'r') as sql_file:
            sql_script = sql_file.read()
        
        # 2. Execute the entire script
        cursor.executescript(sql_script)
        conn.commit()
        print(f"Script '{sql_script_path}' executed successfully.")
    else:
        print(f"Error: The file '{sql_script_path}' was not found.")

except sqlite3.Error as e:
    print(f"SQLite error: {e}")
except Exception as e:
    print(f"General error: {e}")
finally:
    if conn:
        conn.close()
        print("Database connection closed.")