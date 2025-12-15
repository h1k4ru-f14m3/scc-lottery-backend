import functions.global_vars as glvars
import sqlite3
from collections.abc import Iterable

class DBManager():
    def __init__(self, db_file_path=glvars.db_path):
        self.db_path = db_file_path

    # Params must be a tuple
    def execute_query(self, query, params=None):
        db_conn = sqlite3.connect(self.db_path)
        db_cur = db_conn.cursor()
        # print('params= ', params)
        # query = str()

        db_cur.execute(query, params or ())

        if query.strip().upper().startswith('SELECT'):
            return db_cur.fetchall()
        else:
            db_conn.commit()
            return db_cur.lastrowid
        

    def add_row(self, table, cols, values):
        if not isinstance(cols, Iterable) or not isinstance(values, Iterable) or not isinstance(table, str) or len(cols) != len(values):
            return glvars.ReturnMessage(False, 'Invalid Data').send()
            
        placeholders = ', '.join(['?'] * len(values))

        col_string = ', '.join(cols)


        query = f"INSERT INTO {table} ({col_string}) VALUES ({placeholders})"
        # print(query)
        response = self.execute_query(query, tuple(values))
        if response < 1:
            return glvars.ReturnMessage(False, 'Something in the backend went wrong').send()
        
        return glvars.ReturnData(True, 'Successfully added row', id_affected=response).send()
    
    
    def delete_row(self, table, cols, values):
        if not isinstance(cols, Iterable) or not isinstance(values, Iterable) or not isinstance(table, str) or len(cols) != len(values):
            return glvars.ReturnMessage(False, 'Invalid Data').send()
            
        placeholders = ', '.join(['?'] * len(values))

        col_string = ', '.join(cols)


        query = f"DELETE FROM {table} WHERE ({col_string}) = ({placeholders})"
        response = self.execute_query(query, tuple(values))
        
        return glvars.ReturnData(True, 'Successfully added row', id_affected=response).send()
    

    def edit_row(self, table, condition_cols, condition_values, edit_cols, edit_values):
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
        self.execute_query(query, all_params)
        
        return glvars.ReturnMessage(True, 'Edited row(s)').send()