from dotenv import load_dotenv
from flask import session, jsonify
from collections.abc import Iterable
from datetime import datetime, timedelta
import re
import base64
import sqlite3
import json
import logging
import os

load_dotenv()

app_root_dir = os.getenv('APP_ROOT_PATH', './')
db_path = os.getenv('DB_PATH', './data.db')
tickets_table = os.getenv('TICKETS_TABLE', 'tickets') 
users_table = os.getenv('USERS_TABLE', 'users')
orders_table = os.getenv('ORDERS_TABLE', 'orders')
secret_key = os.getenv('SECRET_KEY', '')
price_each = os.getenv('PRICE_EACH', 30000)

status_codes = [
    os.getenv('STATUS_AVAILABLE', 'available'),
    os.getenv('STATUS_ORDERED', 'ordered'),
    os.getenv('STATUS_PROCESSING', 'processing'),
    os.getenv('STATUS_CONFIRMED', 'confirmed')
]

format_code = os.getenv('FORMAT_CODE', '%Y-%m-%d %H:%M:%S')

expire_hours = [
    int(os.getenv('ORDERED_EXPIRE_TIME', 1)),
    int(os.getenv('PROCESSED_EXPIRE_TIME', 24))
]

# Logger Variable here
logger = logging.getLogger(__name__)
roles = ['user', 'mod', 'agent', 'admin']


class ReturnMessage():
    def __init__(self, success, message="???"):
        if not isinstance(success, bool) or not isinstance(message, str):
            raise ValueError('Incorrect value sets!')
        self.success = success
        self.message = message
        

    def send(self):
        dict_format = {'success': self.success, 'message': self.message}

        return dict_format
    

    def response(self):
        dict_format = {'success': self.success, 'message': self.message}

        return jsonify(dict_format)


        

class ReturnData:
    def __init__(self, success, message='???', **params):
        if not isinstance(success, bool) or not isinstance(message, str):
            raise ValueError('Incorrect value sets!')
        
        self.success = success
        self.message = message
        for key, value in params.items():
            setattr(self, key, value)


    def send(self):
        dict_format = {
            'success': self.success,
            'message': self.message
        }

        for key, value in self.__dict__.items():
            if key not in ('success', 'message'): 
                dict_format[key] = value

        return dict_format
    

    def response(self):
        dict_format = {
            'success': self.success,
            'message': self.message
        }

        for key, value in self.__dict__.items():
            if key not in ('success', 'message'): 
                dict_format[key] = value

        return jsonify(dict_format)



def pair_iters_to_string(obj1, obj2): 
    if not isinstance(obj1, Iterable) or not isinstance(obj2, Iterable):
        raise IndexError('Objects must be iterable')       
    if len(obj1) != len(obj2):
        raise ValueError('Objects must have the same length!')

    result_parts = []

    for i in range(len(obj1)):
        # element1 = str(obj1[i])
        # element2 = "NULL" if obj2[i] == None else str(obj2[i])
        # pair = f"{element1} = {element2}"
        # result_parts.append(pair)
        result_parts.append(f"{obj1[i]} = ?")
        
    pair_string = ", ".join(result_parts)
    return pair_string, tuple(obj2) 


def check_multi_conditions(condition_func, *params):
    results = []
    params_list = [*params]

    for param in params_list:
        if isinstance(param, Iterable) and not isinstance(param, str):
            result = bool(condition_func(*params))
            results.append(result)
        else:
            result = bool(condition_func(param))
            results.append(result)

    return results






def setup_logger():
    log_file_path = os.path.join(app_root_dir, 'run.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path)
        ]
    )


def set_exp_time(current_time_string, time_unit='hours', time_units=60):
    dt_obj = datetime.strptime(current_time_string, format_code)

    if time_unit == 'minutes':
        td_obj = timedelta(minutes=time_units)
    else:
        td_obj = timedelta(hours=time_units)

    new_dt_obj = dt_obj + td_obj

    return new_dt_obj.strftime(format_code)


# Shameful but i got the following from GPT
def is_base64_image(s):
    # Check if it matches the "data:image/<type>;base64," pattern
    pattern = r'^data:image/(png|jpeg|jpg|gif|bmp);base64,'
    match = re.match(pattern, s)
    if not match:
        return False
    
    # Remove the prefix
    base64_data = s.split(',', 1)[1]
    
    try:
        # Try decoding
        base64.b64decode(base64_data, validate=True)
        return True
    except Exception:
        return False