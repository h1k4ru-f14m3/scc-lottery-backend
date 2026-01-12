import functions.global_vars as glvars
import sqlite3
from collections.abc import Iterable

class DBManager():
    def __init__(self, db_file_path=glvars.db_path):
        self.db_path = db_file_path


    def get_conn(self):
        return sqlite3.connect(self.db_path)


    # Params must be a tuple
    def execute_query(self, query, params=None):
        db_conn = sqlite3.connect(self.db_path)
        db_cur = db_conn.cursor()
        # print('params= ', params)
        # query = str()

        parameters = params
        if not isinstance(params, tuple) and not isinstance(params, type(None)):
            parameters = tuple(params)

        try:
            db_cur.execute(query, parameters or ())
        except sqlite3.DatabaseError as e:
            return e

        if query.strip().upper().startswith('SELECT'):
            return db_cur.fetchall()
        else:
            db_conn.commit()
            return db_cur.lastrowid
        

    def exec_no_commit(self, query, params=None, conn=None):
        if not isinstance(conn, sqlite3.Connection):
            db_conn = sqlite3.connect(self.db_path)
        else:
            db_conn = conn
        db_cur = db_conn.cursor()

        parameters = params
        if not isinstance(params, tuple) and not isinstance(params, None):
            parameters = tuple(params)

        try:
            db_cur.execute(query, parameters or ())
        except sqlite3.DatabaseError:
            return glvars.ReturnMessage(False, 'No such column').send()

        return glvars.ReturnData(True, 'OK! DONT FORGET TO COMMIT!', db_conn=db_conn, id_affected=db_cur.lastrowid).send()
    

    def commit(self, db_conn):
        if not isinstance(db_conn, sqlite3.Connection):
            return glvars.ReturnMessage(False, 'NOT A DB CONN!').send()
        
        db_conn.commit()
        return glvars.ReturnMessage(True, 'COMMITTED!').send()
        

    def add_row(self, table, cols, values, db_conn):
        if not isinstance(cols, Iterable) or not isinstance(values, Iterable) or not isinstance(table, str) or len(cols) != len(values) or not isinstance(db_conn, sqlite3.Connection):
            return glvars.ReturnMessage(False, 'Invalid Data').send()
            
        placeholders = ', '.join(['?'] * len(values))

        col_string = ', '.join(cols)


        query = f"INSERT INTO {table} ({col_string}) VALUES ({placeholders})"
        # print(query)
        response = self.exec_no_commit(query, tuple(values), db_conn)
        if not response['success']:
            return glvars.ReturnMessage(False, f'Something in the backend went wrong: {response}').send()
        
        return glvars.ReturnData(True, 'Successfully added row', id_affected=response['id_affected']).send()
    
    
    def delete_row(self, table, col, value, db_conn):
        if not isinstance(col, str) or not isinstance(value, str) or not isinstance(table, str):
            return glvars.ReturnMessage(False, 'Invalid Data').send()

        query = f"DELETE FROM {table} WHERE {col} = ?"
        response = self.exec_no_commit(query, (value,), db_conn)
        
        return glvars.ReturnData(True, 'Successfully removed row', id_affected=response).send()
    

    def edit_row(self, table, condition_cols, condition_values, edit_cols, edit_values, conn=None):
        if not isinstance(conn, sqlite3.Connection):
            db_conn = sqlite3.connect(self.db_path)
        else:
            db_conn = conn

        if (not isinstance(table, str) 
            or not isinstance(condition_cols, Iterable) 
            or not isinstance(condition_values, Iterable) 
            or not isinstance(edit_cols, Iterable) 
            or not isinstance(edit_values, Iterable)):
            return glvars.ReturnMessage(False, 'Incorrect value types').send()
        
        condition_string, condition_params = glvars.pair_iters_to_string(condition_cols, condition_values)
        edit_string, edit_params = glvars.pair_iters_to_string(edit_cols, edit_values)
        query = f'UPDATE {table} SET {edit_string} WHERE {condition_string}'

        all_params = edit_params + condition_params
        self.exec_no_commit(query, all_params, db_conn)
        
        return glvars.ReturnMessage(True, 'Edited row(s)').send()
    

    def rollback(self, db_conn):
        if not isinstance(db_conn, sqlite3.Connection):
            return glvars.ReturnMessage(False, 'Provide a db connection!').send()
        
        db_conn.rollback()
        return glvars.ReturnMessage(True, 'Rolled back changes!').send()