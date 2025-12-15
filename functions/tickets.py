import functions.global_vars as glvars
import datetime

class Ticket:
    def __init__(self, code=0):
        self.code = code
        self.status = ''
        self.expire_at = ''
        self.buyer_id = None
        self.note_for = ''


    def to_dict(self):
        return_dict = {
            'code': self.code,
            'status': self.status,
            'expire_at': self.expire_at,
            'buyer_id': self.buyer_id,
            'note_for': self.note_for,
        }
        return return_dict


    def import_from_db(self, db_input):
        if db_input == None or not isinstance(db_input, (list, tuple)):
            return glvars.ReturnMessage(False, 'Invalid data to import').send()

        class_vars = list(self.to_dict().keys())
        if len(class_vars) != len(db_input):
            return glvars.ReturnMessage(False, 'Dictionary keys must match the amount of class variables').send()
        
        for i in range(len(db_input)):
            try:
                setattr(self, class_vars[i], db_input[i])
            except IndexError:
                return glvars.ReturnMessage(False, 'Index error occured').send()
            
        return glvars.ReturnMessage(True, 'Successfully imported from database').send()
        

    def import_from_dict(self, dict_data):
        if not isinstance(dict_data, dict): 
            return glvars.ReturnMessage(False, 'Data not dict!').send()
        
        dict_keys = list(dict_data.keys())
        class_vars = list(self.to_dict().keys())

        if dict_keys != class_vars:
            return glvars.ReturnMessage(False, 'Dictionary not in correct format').send()
        
        for key in dict_keys:
            setattr(self, key, dict_data[key])

        return glvars.ReturnMessage(True, 'Successfully imported').send()
    

    def reset(self):
        self.buyer_id = None
        self.note_for = ''
        self.status = glvars.status_codes[0]
        self.expire_at = None


    def is_available(self):
        # print('Ticket Status: ', self.status)
        # print('Status Code 0: ', glvars.status_codes[0])
        # print('Ticket Code == Status Code 0 ? ', self.status == glvars.status_codes[0])
        return bool(self.status == glvars.status_codes[0])
    

    def order(self, buyer_id):
        if not self.is_available():
            return glvars.ReturnMessage(False, 'Ticket not available').send()
        
        self.status = glvars.status_codes[1]
        current_time = datetime.datetime.now().strftime(glvars.format_code)
        self.expire_at = glvars.set_exp_time(current_time, time_unit='hours', time_units=glvars.expire_hours[0])
        self.buyer_id = buyer_id
        return self.to_dict()
    

    def remove_order(self):
        if self.is_available():
            return glvars.ReturnMessage(False, 'Ticket not ordered').send()
        
        self.status = glvars.status_codes[0]
        self.expire_at = None
        self.buyer_id = None
        return self.to_dict()
    

    def purchase(self):
        if self.status != glvars.status_codes[1]:
            return glvars.ReturnMessage(False, 'Ticket not ordered yet').send()
        
        self.status = glvars.status_codes[2]
        current_time = datetime.datetime.now().strftime(glvars.format_code)
        self.expire_at = glvars.set_exp_time(current_time, time_unit='hours', time_units=glvars.expire_hours[1])
        return self.to_dict()
    

    def confirm(self):
        if self.status != glvars.status_codes[2]:
            return glvars.ReturnMessage(False, 'Ticket not bought yet').send()
        
        self.status = glvars.status_codes[3]
        self.expire_at = 'never'
        return glvars.ReturnData(True, 'Confirmed ticket!', data=self.to_dict()).send()
        
    
    def add_note(self, note):
        if not note:
            return glvars.ReturnMessage(False, 'No note provided').send()
        
        self.note_for = note
        return glvars.ReturnData(True, 'Added note!', data=self.to_dict()).send()
    


class TicketsManager:
    def __init__(self, db_man):
        self.db_man = db_man


    # READ
    def get_records(self, limit=10, offset=0, q=None, search_for=None):
        if str(q).lower() == 'all' and str(search_for).lower() == 'status':
            q = None
            search_for = None

        params = str()
        query = f"SELECT t.code, u.name, t.note_for, t.status, t.expire_at FROM {glvars.tickets_table} t LEFT JOIN {glvars.users_table} u ON t.buyer_id = u.id LIMIT {limit} OFFSET {offset}"

        if q:
            params = f'%{q}%'
            query = f"SELECT t.code, u.name, t.note_for, t.status, t.expire_at FROM {glvars.tickets_table} t LEFT JOIN {glvars.users_table} u ON t.buyer_id = u.id WHERE {search_for} LIKE ? LIMIT {limit} OFFSET {offset}"

        # print('Query: ', query)
        # print('Params: ', params)
        # print('Search For: ', search_for)

        if search_for:
            res = self.db_man.execute_query(query, (params,))
        else:
            res = self.db_man.execute_query(query)
        
        return glvars.ReturnData(True, "Here's the tickets!", data=res).send()
    

    # GET A TICKET
    def get_ticket(self, code=None):
        if not code:
            return glvars.ReturnMessage(False, 'No code given.').send()
        
        ticket = Ticket(code)
        query = f'SELECT code, status, expire_at, buyer_id, note_for FROM {glvars.tickets_table} WHERE code = ?'

        try:
            ticket.import_from_db(self.db_man.execute_query(query, (code,))[0])
        except IndexError:
            return glvars.ReturnMessage(False, 'Ticket not found!').send()

        return glvars.ReturnData(True, 'Ticket Found!', data=ticket).send()
    

    def edit_ticket(self, code=None, edit_vars=None, edit_values=None):
        if not code or not edit_vars or not edit_values or not isinstance(edit_values, list) or not isinstance(edit_values, list) or len(edit_values) != len(edit_vars):
            return glvars.ReturnMessage(False, 'No code provided or invalid datatypes or data lengths do not match!').send()
        
        ticket = self.get_ticket(code)['data']
        
        try:
            for i, var in enumerate(edit_vars):
                setattr(ticket, var, edit_values[i])
        except Exception:
            return glvars.ReturnMessage(False, 'Something went wrong in edit tickets!').send()
        
        edit_res = self.db_man.edit_row(glvars.tickets_table, ('code',), (code,), edit_vars, edit_values)

        if not edit_res['success']:
            return glvars.ReturnMessage(False, edit_res['message']).send()
        
        return glvars.ReturnMessage(True, 'Successfully edited ticket!').send()
    

    def delete_ticket(self, code=None):
        if not code:
            return glvars.ReturnMessage(False, 'No code provided!').send()

        res = self.db_man.delete_row(glvars.tickets_table, ('code',), (code,))
        if not res['success']:
            return glvars.ReturnMessage(False, f"Reason cannot delete ticket: {res['message']}").send()
        
        return glvars.ReturnMessage(True, 'Successfully deleted ticket!').send()

        
    def add_ticket(self, code=None):
        if not code:
            return glvars.ReturnMessage(False, 'No code provided!').send()
        
        ticket = self.get_ticket(code)
        # print('Ticket: ', ticket)
        if ticket['success']:
            return glvars.ReturnMessage(False, 'Ticket already exists!').send()
        
        ticket = Ticket(code)
        res = self.db_man.add_row(glvars.tickets_table, ('code',), (ticket.code,))
        if not res['success']:
            return glvars.ReturnMessage(False, f"Something went wrong in add tickets: {res['message']}").send()

        return glvars.ReturnMessage(True, 'Added Ticket!').send()
        
    




