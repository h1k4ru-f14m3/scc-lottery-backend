import sqlite3
import os
import functions.users as usr
import functions.db_man as db
from dotenv import load_dotenv, set_key
import secrets

# ... (your existing imports)

# Path to your .env file
db_path = 'data.db'
ENV_PATH = '.env'

def setup_env():
    """Generates a SECRET_KEY if it doesn't exist in .env"""
    # Create the file if it doesn't exist
    if not os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'w') as f:
            f.write('')

    load_dotenv(ENV_PATH)
    
    if not os.getenv('SECRET_KEY'):
        # Generate a high-entropy 32-byte string
        new_key = secrets.token_hex(32)
        set_key(ENV_PATH, 'SECRET_KEY', new_key)
        print(f"Generated new SECRET_KEY in {ENV_PATH}")
    else:
        print("SECRET_KEY already exists in .env")

def create_db():
    db_file_name = db_path
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


def create_admin():
    db_man = db.DBManager(db_path)
    user_man = usr.UserManager(db_man)

    db_conn = db_man.get_conn()
    res = user_man.add_user('admin', 'admin', 'admin@12345', 'admin', db_conn)
    if not res['success']:
        print(f"Could not create admin: {res['message']}")
        return
    
    edit_res = user_man.edit_user('1', ('role',), ('admin',), db_conn)
    if not edit_res['success']:
        print(f"ERROR CREATING ADMIN! {edit_res['message']}")
    
    commit_res = db_man.commit(db_conn)
    if not commit_res['success']:
        print(f"Could not commit changes: {commit_res['message']}")
        return

setup_env()
create_db()
create_admin()
print('OK!')