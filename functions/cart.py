from functions.tickets import Ticket
import flask
from functions.db_man import DBManager
from functions.users import User
from collections.abc import Iterable
import functions.global_vars as glvars
import sqlite3

# db_man = DBManager()
# logger = glvars.logger

# input param refers to the data that is from a DB query
class Cart():
    def __init__(self, cart_id=0, user_id=0, input=None, dict_data=None):
        # ID should be +1 of the amount of orders
        self.id = cart_id
        self.user_id = user_id

        self.items = set()
        self.items_len = len(self.items)
        self.img_link = ''
        self.is_in_cart = True

        self.import_from_dict(dict_data)
        self.import_from_db(input)

        self.price_each = glvars.price_each


    # After adding and removing item(s), user_info session must be set again!
    def add_item(self, *item_id, user_dict):
        ids = [*item_id]
        user_obj = User(self.user_id)
        user_obj.import_from_dict(user_dict)

        for row in ids:
            self.items.add(row)
            self.items_len = len(self.items)

            user_obj.add_set_item('tickets_ordered', row)
            
        return self


    def remove_item(self, *item_id):
        ids = [*item_id]
        user_obj = User(self.user_id)

        for row in ids:
            self.items.discard(row)
            self.items_len = len(self.items)

            user_rm_return_var = user_obj.remove_set_item('tickets_ordered', row)
            if user_rm_return_var['success'] == False:
                return glvars.ReturnMessage(False, user_rm_return_var['message'])
            
        return self
    

    def clear_cart(self): 
        for item in self.items:
            self.remove_item(item)


    def to_dict(self):
        cart_dict = {
            'id': self.id,
            'buyer_id': self.user_id,
            'amount_bought': len(self.items) if self.items else 0,
            'tickets_bought': ";".join(self.items) if self.items else None,
            'img_link': self.img_link,
            'is_in_cart': self.is_in_cart,
            'price_each': self.price_each
        }
        # print(cart_dict)
        return cart_dict
    

    def turn_to_order(self):
        if self.items_len == 0:
            return glvars.ReturnMessage(False, 'Cart is empty!').send()
        if not self.is_in_cart:
            return glvars.ReturnMessage(False, 'Cart already in orders').send()
        
        setattr(self, 'is_in_cart', False)
        return self.to_dict()



    def import_from_db(self, input_data):
        if input_data == None or not isinstance(input_data, Iterable):
            return 0
        
        self.id = input_data[0]
        self.user_id = input_data[1]
        self.img_link = input_data[4]
        self.is_in_cart = input_data[5]
        
        # try:
        #     tickets_string = str(input_data[3])
        # except TypeError:
        #     return glvars.ReturnMessage(False, 'Something went wrong with the cart data input!').send()
        # tickets_list = tickets_string.split(';')

        if input_data[3] == None:
            self.items = set()
            self.items_len = 0
            return glvars.ReturnMessage(True, 'Successfully imported!').send()
        
        self.items = set(input_data[3].split(';')) if input_data[3] else set()
        self.items_len = len(self.items)
        return glvars.ReturnMessage(True, 'Successfully imported!').send()
    

    # You can say this is a from_dict() function
    def import_from_dict(self, dict_data):
        if dict_data == None or not isinstance(dict_data, dict):
            return glvars.ReturnMessage(False, 'Wrong dictionary data').send()
        
        try:
            self.id = dict_data['id']
            self.user_id = dict_data['buyer_id']
            self.items = set(dict_data.get('tickets_bought', '').split(';')) if dict_data.get('tickets_bought') else set()
            self.items_len = len(self.items)
            self.is_in_cart = bool(dict_data['is_in_cart'])
            self.img_link = dict_data['img_link']
        except ValueError:
            return glvars.ReturnMessage(False, 'Something went wrong with dictionary data for cart.').send()
        
        return glvars.ReturnMessage(True, 'Ok from setting dictionary data').send()
        

        
        

    # def add_cart(self, cart_class):
    #     self.carts[cart_class.id] = cart_class


    # def remove_cart(self, cart_id):
    #     self.carts.pop(cart_id)


    # def get_session_cart(self, session):
    #     cart = Cart()
    #     cart.set_dict_data(session.get('cart'))
    #     return cart


