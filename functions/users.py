import bcrypt
from flask import session, jsonify
from collections.abc import Iterable
import functions.global_vars as glvars

class User():
    def __init__(self, user_id=None, db_input=None, dict_input=None):
        self.id = user_id
        self.name = ''
        self.email = None
        self.phone_number = None
        self.role = None
        self.tickets_ordered = set() 
        self.tickets_bought = set()
        self.pfp = ''

        if db_input:
            self.import_from_db(db_input)
        else:
            self.import_from_dict(dict_input)


    def to_dict(self):
        return_dict = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone_number': self.phone_number,
            'role': self.role,
            'tickets_bought': ';'.join(self.tickets_bought),
            'tickets_ordered': ';'.join(self.tickets_ordered),
            'pfp': self.pfp
        }
        return return_dict


    def import_from_dict(self, dict_data):
        if not isinstance(dict_data, dict):
            return glvars.ReturnMessage(False, 'Data not dict!').send()
        
        dict_keys = list(dict_data.keys())
        class_vars = list(self.to_dict().keys())

        if dict_keys != class_vars:
            return glvars.ReturnMessage(False, 'Dictionary not in correct format').send()
        
        for key in dict_keys:
            data_to_set = dict_data[key]
            if key == 'tickets_ordered' or key == 'tickets_bought':
                data_to_set = set(dict_data.get(key, '').split(';')) if dict_data.get(key) else set()
            setattr(self, key, data_to_set)

        return glvars.ReturnMessage(True, 'Successfully imported.').send()
    

    def import_from_db(self, db_input):
        if db_input == None or not isinstance(db_input, (list, tuple)):
            return glvars.ReturnMessage(False, 'Invalid data to import').send()
        
        class_vars = list(self.to_dict().keys())
        if len(class_vars) != len(db_input):
            return glvars.ReturnMessage(False, 'Dictionary keys must match amount of class variables.').send()

        for i in range(len(db_input)):
            try:
                var_to_set = db_input[i]
                # print(db_input[i])

                if class_vars[i] in ['tickets_bought', 'tickets_ordered']:
                    if db_input[i] == 'None':
                        var_to_set = None
                    var_to_set = set(str(db_input[i]).split(';')) if db_input[i] else set()
                setattr(self, class_vars[i], var_to_set)
            except IndexError:
                return glvars.ReturnMessage(False, 'Index error occured.').send()
            
        return glvars.ReturnMessage(True, 'Successfully imported from database.').send()
        



    # def update_db_vars(self):
    #     query = ''
    #     if self.username:
    #         query = f"SELECT id, name, phone_number, role, tickets_ordered, tickets_bought, pfp WHERE username = {self.username}"
    #     elif self.id:
    #         query = f"SELECT id, name, phone_number, role, tickets_ordered, tickets_bought, pfp WHERE id = {self.id}"
    #     else:
    #         return glvars.ReturnMessage(False, 'No data to find with.').send()

    #     data = self.db_man.execute_query(query)[0]
    #     if not data:
    #         return glvars.ReturnMessage(False, 'Empty data')

    #     self.id = data[0]
    #     self.name = data[1]
    #     self.phone_number = data[2]
    #     self.role = data[3]
    #     self.pfp = data[6]

    #     self.tickets_ordered = set(data[4])
    #     self.tickets_bought = set(data[5])


    def set_vars(self, vars_to_set, values):
        if not isinstance(vars_to_set, list) or not isinstance(values, list) or len(vars_to_set) != len(values):
            return glvars.ReturnMessage(False, 'Invalid datatypes to set!').send()
        
        for var, value in zip(vars_to_set, values):
            if not hasattr(self, var):
                return glvars.ReturnMessage(False, 'Error occured with the variables and values.').send()
            setattr(self, var, value)

        return self.to_dict()


    def add_set_item(self, set_var, value):
        if isinstance(set_var, str):
            set_var.split(';')
        
        if not hasattr(self, set_var):
            return glvars.ReturnMessage(False, 'No such variable!').send()
        
        var_to_change = getattr(self, set_var)

        if not isinstance(var_to_change, set):
            return glvars.ReturnMessage(False, 'Invalid data type!').send()
        
        var_to_change.add(value)

        return self.to_dict()
    

    def remove_set_item(self, set_var, value):
        if not hasattr(self, set_var):
            return glvars.ReturnMessage(False, 'No such variable').send()
        
        var_to_change = getattr(self, set_var)
        if not isinstance(var_to_change, set):
            return glvars.ReturnMessage(False, 'Invalid data type!').send()
        elif value not in var_to_change:
            return glvars.ReturnMessage(False, 'Nothing changed. Already removed.').send()

        var_to_change.remove(value)
        return self.to_dict()

        


class Authentication():
    def __init__(self, db_man_class):
        self.db_man = db_man_class


    def register(self, json_data):
        if not isinstance(json_data, dict):
            return glvars.ReturnMessage(False, 'Something Went Wrong :(').response()
        
        query = f"SELECT COUNT(*) FROM {glvars.users_table} WHERE phone_number = ?"
        check_count = self.db_man.execute_query(query, (json_data['phone_number'],))[0][0]
        if check_count != 0:
            return glvars.ReturnMessage(False, 'Phone Number already has an account!').response()
        
        # Hash the password
        salt = bcrypt.gensalt(rounds=12)
        byte_pass = json_data['password'].encode('utf-8')
        pass_hash = bcrypt.hashpw(byte_pass, salt)

        # Construct new dictionary for database
        new_dict = json_data.copy()
        new_dict.update({'password': pass_hash})
        new_dict.pop('confirm_password', None)

        db_conn = self.db_man.get_conn()
        # Update/Insert to Database
        # print(tuple(new_dict.values()))
        self.db_man.add_row(glvars.users_table, tuple(new_dict.keys()), tuple(new_dict.values()), db_conn)

        commit_res = self.db_man.commit(db_conn)
        if not commit_res['success']:
            return glvars.ReturnMessage(False, f"Could not commit data: {commit_res['message']}").response()

        new_dict.update({'logininfo': json_data['phone_number']})

        return self.login(json_data)
    

    def login(self, json_data):
        if not isinstance(json_data, dict):
            return {'success': False, 'message': 'Something Went Wrong :('}
        
        dict_check = json_data.copy()
        if 'logininfo' not in dict_check.keys():
            dict_check.update({'logininfo': json_data['phone_number']})

        query = "SELECT password, id, name, email, phone_number, role, tickets_bought, tickets_ordered, pfp FROM users WHERE phone_number = ?"
        
        db_result = self.db_man.execute_query(query, (dict_check['logininfo'],))
        if not db_result:
            return {'success': False, 'message': 'Account not registered!'}
        db_data = db_result[0]

        if not db_data:
            return {'success': False, 'message': 'Account not registered.'}
        
        if not bcrypt.checkpw(json_data['password'].encode('utf-8'), db_data[0]):
            return {'success': False, 'message': 'Invalid password.'}
        
        new_dict = json_data.copy()
        new_dict.pop('password', None)
        new_dict.pop('confirm_password', None)

        user_obj = User()
        new_list = []
        for item in range(1, len(db_data)):
            new_list.append(db_data[item])

        user_obj.import_from_db(new_list)

        session['user_info'] = user_obj.to_dict()
        # print(f'User OBJ: {user_obj.to_dict()}')

        return glvars.ReturnData(True, 'Logged In!', user_info=session['user_info']).response()



class UserManager():
    def __init__(self, db_man):
        self.db_man = db_man


    def get_users(self, limit=10, offset=0, q=None, search_for='id'):
        params = str()
        query = f"SELECT id, name, role, tickets_ordered, tickets_bought, phone_number, email, address FROM {glvars.users_table} LIMIT {limit} OFFSET {offset}"

        if q:
            params = f'%{q}%'    
            query = f"SELECT id, name, role, tickets_ordered, tickets_bought, phone_number, email, address FROM {glvars.users_table} WHERE {search_for} LIKE ? LIMIT {limit} OFFSET {offset}"
            res = self.db_man.execute_query(query, (params,))
        else:
            res = self.db_man.execute_query(query)

        return glvars.ReturnData(True, "Here's the users!", data=res).send()

    def get_user(self, id):
        user = User()
        query = f'SELECT id, name, email, phone_number, role, tickets_ordered, tickets_bought, pfp FROM {glvars.users_table} WHERE id = ?'
        res = self.db_man.execute_query(query, (id,))

        try:
            if not res[0]:
                return glvars.ReturnMessage(False, 'User not found!').send()
            try_import = user.import_from_db(res[0])
            if not try_import['success']:
                return glvars.ReturnMessage(False, try_import['message']).send()
        except IndexError:
            return glvars.ReturnMessage(False, 'User not found!').send()
        
        return glvars.ReturnData(True, 'Got user!', data=user).send()
    
    
    def add_user(self, name, phone_number, password, db_conn=None):
        if isinstance(db_conn, type(None)):
            return glvars.ReturnMessage(False, 'Invalid db conn!').send()

        salt = bcrypt.gensalt(rounds=12)
        byte_pass = password.encode('utf-8')
        pass_hash = bcrypt.hashpw(byte_pass, salt)

        res = self.db_man.add_row(glvars.users_table, ('name', 'phone_number', 'password'), (name, phone_number, pass_hash), db_conn)

        if not res['success']:
            return glvars.ReturnMessage(False, res['message']).send()
        
        return glvars.ReturnData(True, 'Added user!').send()
    

    def edit_user(self, u_id, edit_vars, edit_values, db_conn=None):
        if isinstance(db_conn, type(None)):
            return glvars.ReturnMessage(False, 'Invalid db conn for edit_user').send()

        if not isinstance(edit_vars, Iterable) or not isinstance(edit_values, Iterable):
            return glvars.ReturnMessage(False, 'The two variables must be lists!').send()
        
        if len(edit_vars) != len(edit_values):
            return glvars.ReturnMessage(False, 'The two lists must be the same in size').send()
        
        for i, var in enumerate(edit_vars):
            if var == 'password':
                salt = bcrypt.gensalt(rounds=12)
                byte_pass = edit_values[i].encode('utf-8')
                pass_hash = bcrypt.hashpw(byte_pass, salt)

                try:
                    edit_values[i] = pass_hash
                except Exception as e:
                    return glvars.ReturnMessage(False, f'Something went wrong hashing the password: {e}').send()
                
        print(f'EDIT_VARS: {edit_vars}')
        print(f'EDIT_VALUES: {edit_values}')
        edit_res = self.db_man.edit_row(glvars.users_table, ('id',), (u_id,), edit_vars, edit_values, db_conn)

        if not edit_res['success']:
            return glvars.ReturnMessage(False, edit_res['message']).send()
        
        return glvars.ReturnMessage(True, 'Edited User!').send()
    

    def delete_user(self, id):
        res = self.db_man.delete_row(glvars.users_table, ['id'], [id])
        if not res['success']:
            return glvars.ReturnMessage(False, f"Error: {res['message']}").send()
        
        return glvars.ReturnMessage(True, 'Successfully deleted the user!').send()