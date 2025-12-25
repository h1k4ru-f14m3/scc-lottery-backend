import datetime

from flask.typing import ResponseClass

import functions.global_vars as glvars
from functions.cart import Cart
from functions.tickets import Ticket
from functions.users import User


class OrderManager:
    def __init__(self, db_man):
        self.db_man = db_man
        self.tickets_man = None

    def set_tickets_man(self, tickets_man):
        self.tickets_man = tickets_man

    def add_tickets_to_cart(self, ticket_id, user_session, cart_session):
        """Edit Ticket in DB"""
        # Initialize ticket class
        ticket_get = self.tickets_man.get_ticket(ticket_id)
        if not ticket_get["success"]:
            return glvars.ReturnMessage(False, ticket_get["message"]).send()
        ticket = ticket_get["data"]

        # Initialize user class
        user = User()
        user.import_from_dict(user_session)

        """Update tickets in db"""
        db_conn = self.db_man.get_conn()
        if not ticket.is_available():
            # print('Ticket Data: ', ticket.to_dict())
            return glvars.ReturnMessage(False, "Ticket already ordered!").send()
        ticket.order(user.id)
        response = self.db_man.edit_row(
            glvars.tickets_table,
            ("code",),
            (ticket_id,),
            ("status", "buyer_id", "expire_at"),
            (ticket.status, ticket.buyer_id, ticket.expire_at),
            db_conn,
        )
        if not response["success"]:
            return glvars.ReturnMessage(False, response["message"]).send()

        """Edit Cart Session"""
        cart = Cart()
        cart.import_from_dict(cart_session)
        cart = cart.add_item(ticket_id, user_dict=user_session)
        cart_dict = cart.to_dict()

        """ Edit User Session """
        user.add_set_item("tickets_ordered", ticket_id)
        user_dict = user.to_dict()

        self.save_to_db(user_dict, cart_dict, db_conn)

        commit_res = self.db_man.commit(db_conn)
        if not commit_res["success"]:
            return glvars.ReturnMessage(False, commit_res["message"]).send()

        """Return the Data"""
        return glvars.ReturnData(
            True, "Added ticket!", cart=cart_dict, user=user_dict
        ).send()

    def remove_tickets_from_cart(self, ticket_id, user_session, cart_session):
        """Edit Ticket in DB"""
        # Initialize ticket class
        ticket_get = self.tickets_man.get_ticket(ticket_id)
        if not ticket_get["success"]:
            return glvars.ReturnMessage(False, ticket_get["message"]).send()
        ticket = ticket_get["data"]

        # Initialize user class
        user = User()
        user.import_from_dict(user_session)

        """Update tickets in db"""
        db_conn = self.db_man.get_conn()
        if ticket.is_available():
            return glvars.ReturnMessage(False, "Ticket is available").send()
        ticket.remove_order()
        response = self.db_man.edit_row(
            glvars.tickets_table,
            ("code",),
            (ticket_id,),
            ("status", "buyer_id", "expire_at"),
            (ticket.status, ticket.buyer_id, ticket.expire_at),
            db_conn,
        )
        if not response["success"]:
            return glvars.ReturnMessage(False, response["message"]).send()

        commit_res = self.db_man.commit(db_conn)
        if not commit_res["success"]:
            return glvars.ReturnMessage(False, commit_res["message"]).send()

        """Edit Cart Session"""
        cart = Cart()
        cart.import_from_dict(cart_session)
        cart.remove_item(ticket_id)

        # Edit User Session
        user.remove_set_item("tickets_ordered", ticket_id)

        """Return the Data"""
        return glvars.ReturnData(
            True, "Removed ticket!", cart=cart.to_dict(), user=user.to_dict()
        ).send()

    def clear_cart(self, user_session, cart_session):
        user = User()
        user.import_from_dict(user_session)
        cart = Cart()
        cart.import_from_dict(cart_session)

        db_conn = self.db_man.get_conn()
        for item in cart.items:
            ticket_get = self.tickets_man.get_ticket(item)
            if not ticket_get["success"]:
                return glvars.ReturnMessage(False, ticket_get["message"]).send()
            ticket = ticket_get["data"]
            ticket.remove_order()
            response = self.db_man.edit_row(
                glvars.tickets_table,
                ("code",),
                (ticket.code,),
                ("status", "buyer_id", "expire_at"),
                (ticket.status, ticket.buyer_id, ticket.expire_at),
                db_conn,
            )
            if response["success"] == False:
                return glvars.ReturnMessage(False, response["message"]).send()

            user.remove_set_item("tickets_ordered", ticket.code)
            cart.remove_item(ticket.code)

        commit_res = self.db_man.commit(db_conn)
        if not commit_res["success"]:
            return glvars.ReturnMessage(
                False, f"Could not commit: {commit_res['message']}"
            ).send()

        return glvars.ReturnData(
            True, "Removed Successfully", cart=cart.to_dict(), user=user.to_dict()
        ).send()

    def confirm_bought(self, img_data, user_session, cart_session):
        user = User()
        user.import_from_dict(user_session)
        cart = Cart()
        cart.import_from_dict(cart_session)

        if not cart.items:
            return glvars.ReturnMessage(False, "No tickets in cart!").send()

        cart.img_link = img_data

        db_conn = self.db_man.get_conn()

        for item in cart.items:
            ticket_get = self.tickets_man.get_ticket(item)
            if not ticket_get["success"]:
                return glvars.ReturnMessage(False, ticket_get["message"]).send()
            ticket = ticket_get["data"]

            ticket.purchase()
            ticket.add_note(user.name)

            response = self.tickets_man.edit_ticket(
                ticket.code,
                ["status", "buyer_id", "expire_at", "note_for"],
                [ticket.status, ticket.buyer_id, ticket.expire_at, ticket.note_for],
                db_conn,
            )

            if response["success"] == False:
                return glvars.ReturnMessage(False, response["message"]).send()

            user.remove_set_item("tickets_ordered", ticket.code)
            user.add_set_item("tickets_bought", ticket.code)
        self.db_man.commit(db_conn)

        cart.turn_to_order()
        order_id = cart.id
        # SAVE TO DB
        if not self.save_to_db(user_session, cart.to_dict())["success"]:
            return glvars.ReturnMessage(False, "Could not save to DB.").send()

        return glvars.ReturnData(
            True,
            "Tickets in cart bought.",
            cart=None,
            user=user.to_dict(),
            order_id=order_id,
        ).send()

    def confirm_cart(self, order_id):
        order = Cart()
        order_res_query = f"SELECT * FROM {glvars.orders_table} WHERE id = ?"
        order_res = self.db_man.execute_query(order_res_query, (order_id,))
        order.import_from_db(order_res[0])

        db_conn = self.db_man.get_conn()
        for item in order.items:
            # print('Ticket Code: ', item)
            ticket_get = self.tickets_man.get_ticket(item)
            if not ticket_get["success"]:
                return glvars.ReturnMessage(False, ticket_get["message"]).send()
            ticket = ticket_get["data"]

            ticket.confirm()
            # print('This is a ticket: ', ticket.to_dict())
            response = self.db_man.edit_row(
                glvars.tickets_table,
                ("code",),
                (ticket.code,),
                ("status", "expire_at"),
                (ticket.status, ticket.expire_at),
                db_conn,
            )

            if response["success"] == False:
                return glvars.ReturnMessage(False, response["message"]).send()

        cart_edit = self.db_man.edit_row(
            glvars.orders_table, ("id",), (order_id,), ("confirmed",), (1,), db_conn
        )
        if cart_edit["success"] == False:
            return glvars.ReturnMessage(False, cart_edit["message"]).send()

        commit_res = self.db_man.commit(db_conn)
        if not commit_res["success"]:
            return glvars.ReturnMessage(False, commit_res["message"]).send()

        return glvars.ReturnMessage(True, "Order confirmed to be bought!").send()

    def cancel_cart(self, order_id):
        order = Cart()
        order_res_query = f"SELECT * FROM {glvars.orders_table} WHERE id = ?"
        order_res = self.db_man.execute_query(order_res_query, (order_id,))
        order.import_from_db(order_res[0])

        db_conn = self.db_man.get_conn()

        for item in order.items:
            ticket_get = self.tickets_man.get_ticket(item)
            if not ticket_get["success"]:
                return glvars.ReturnMessage(False, ticket_get["message"]).send()
            ticket = ticket_get["data"]

            ticket.reset()
            response = self.db_man.edit_row(
                glvars.tickets_table,
                ("code",),
                (ticket.code,),
                ("status", "expire_at", "buyer_id", "note_for"),
                (ticket.status, ticket.expire_at, ticket.buyer_id, ticket.note_for),
                db_conn
            )
            if not response["success"]:
                return glvars.ReturnMessage(
                    False, "Something went wrong editing to reset in the database."
                ).send()

        order_del = self.db_man.delete_row(
            glvars.orders_table, "id", str(order.id), db_conn
        )

        if not order_del["success"]:
            return glvars.ReturnMessage(
                False, f"Could not cancel the order: {order_del['message']}"
            ).send()

        commit_res = self.db_man.commit(db_conn)
        if not commit_res["success"]:
            return glvars.ReturnMessage(
                False, f"Could not cancel the order: {commit_res['message']}"
            ).send()

        return glvars.ReturnMessage(True, "Order cancelled!").send()

    def save_to_db(self, user_session, cart_session, given_db_conn=None):
        # Save User
        user = User()
        user.import_from_dict(user_session)
        user_dict = user.to_dict()
        db_conn = given_db_conn
        if not given_db_conn:
            db_conn = self.db_man.get_conn()

        response = self.db_man.edit_row(
            glvars.users_table,
            ("id",),
            (user.id,),
            ("tickets_bought", "tickets_ordered"),
            (user_dict["tickets_bought"], user_dict["tickets_ordered"]),
            db_conn,
        )
        if response["success"] == False:
            return glvars.ReturnMessage(False, response["message"]).send()

        # Save Cart
        cart = Cart()
        cart.import_from_dict(cart_session)
        cart_dict = cart.to_dict()

        response = self.db_man.edit_row(
            glvars.orders_table,
            ("id",),
            (cart.id,),
            ("buyer_id", "amount_bought", "tickets_bought", "img_link", "is_in_cart"),
            (
                cart_dict["buyer_id"],
                cart_dict["amount_bought"],
                cart_dict["tickets_bought"],
                cart_dict["img_link"],
                cart_dict["is_in_cart"],
            ),
            db_conn,
        )
        if response["success"] == False:
            return glvars.ReturnMessage(False, response["message"]).send()

        if not given_db_conn:
            commit_res = self.db_man.commit(db_conn)
            if not commit_res["success"]:
                return glvars.ReturnMessage(False, commit_res["message"]).send()

        return glvars.ReturnMessage(True, "Successfully saved to the database").send()

    def create_cart(self, user_session):
        user = User()
        user.import_from_dict(user_session)

        db_conn = self.db_man.get_conn()
        response = self.db_man.add_row(
            glvars.orders_table, ("buyer_id",), (user.id,), db_conn
        )
        print(response)

        commit_res = self.db_man.commit(db_conn)
        if not commit_res["success"]:
            return glvars.ReturnMessage(
                False, f"Could not commit data: {commit_res['message']}"
            ).send()
        if not response["success"]:
            return glvars.ReturnMessage(
                False, f"Something went wrong: {response['message']}"
            )

        cart = Cart(response["id_affected"], user.id)

        query = f"SELECT id, buyer_id, amount_bought, tickets_bought, img_link, is_in_cart FROM {glvars.orders_table} WHERE id = ?"
        response = self.db_man.execute_query(query, (cart.id,))
        print("SUPPOSED PARAM", (cart.id,))
        print(
            "TYPE_PARAM",
            type(
                cart.id,
            ),
        )
        print("RESPONSE:", response)
        cart.import_from_db(response[0])

        # print(response[0])

        return glvars.ReturnData(True, "Created new cart", cart=cart.to_dict()).send()

    def edit_note(self, note, ticket_code):
        ticket_get = self.tickets_man.get_ticket(ticket_code)
        if not ticket_get["success"]:
            return glvars.ReturnMessage(False, ticket_get["message"]).send()
        ticket = ticket_get["data"]

        ticket.add_note(note)
        db_conn = self.db_man.get_conn()
        response = self.db_man.edit_row(
            glvars.tickets_table, ("code",), (ticket_code,), ("note_for",), (note,), db_conn
        )

        if not response["success"]:
            return glvars.ReturnMessage(False, response["message"]).send()

        commit_res = self.db_man.commit(db_conn)
        if not commit_res["success"]:
            return glvars.ReturnMessage(
                False, f"Could not commit: {commit_res['message']}"
            ).send()

        return glvars.ReturnMessage(True, "Edited Note!").send()
