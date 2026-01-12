from functions.db_man import DBManager
from routes import app
from functions.tickets import Ticket
from functions.cart import Cart
import functions.global_vars as glvars
import datetime
import time
import logging

# db_man = DBManager('/home/admin/scc-lottery-backend/data.db')
# log_file = '/home/admin/scc-lottery-backend/prune_job.log'

db_man = DBManager('./data.db')
log_file = './prune_job.log'
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def prune_ghost_orders():
    db_conn = db_man.get_conn()
    ghost_orders = db_man.execute_query(f'SELECT id, tickets_bought FROM {glvars.orders_table} WHERE tickets_bought IS NULL')
    if not ghost_orders:
        logger.info('No ghost orders...\n')
        return
    
    for row in ghost_orders:
        res = db_man.delete_row(glvars.orders_table, 'id', str(row[0]), db_conn)
        logger.info(f"SUCCESS: {res['success']} - MESSAGE: {res['message']}")
        logger.info(f"DELETE ORDER {row[0]} - TICKETS_BOUGHT: {row[1]}")
        logger.info(f"ORDER {row[0]} - {row}")

    commit_res = db_man.commit(db_conn)
    logger.info(f"COMMIT: SUCCESS - {commit_res['success']} : {commit_res['message']}")

    logger.info(f'\n Successfully pruned ghost orders! \n')


def prune_tickets():
    now = datetime.datetime.now().strftime(glvars.format_code)
    query = f'SELECT * FROM {glvars.tickets_table} WHERE expire_at <= ?'
    db_conn = db_man.get_conn()
    res = db_man.execute_query(query, (now,))
    if not res:
        logger.info('No tickets...\n')
        return 

    for row in res:
        # EDIT TICKETS
        ticket = Ticket(row[0])
        query2 = f'SELECT code, status, expire_at, buyer_id, note_for FROM {glvars.tickets_table} WHERE code = ?'
        ticket_res = db_man.execute_query(query2, (row[0],))
        if not isinstance(ticket_res, list) or not ticket_res:
            logger.error(f'SOMETHING WENT WRONG IN TICKET - {ticket_res}')
            continue
        ticket.import_from_db(ticket_res[0])

        ticket.reset()
        response = db_man.edit_row(glvars.tickets_table, 
                                   ('code',), 
                                   (ticket.code,), 
                                   ('status', 'expire_at', 'buyer_id', 'note_for'),
                                   (ticket.status, ticket.expire_at, ticket.buyer_id, ticket.note_for),
                                   db_conn)
        if not response['success']:
            logger.error(response['message'])
            continue

        # EDIT ORDERS
        order_cart = Cart()
        query3 = f"SELECT * FROM {glvars.orders_table} WHERE ';' || tickets_bought || ';' LIKE '%;{row[0]};%'"
        order_res = db_man.execute_query(query3,)
        if not isinstance(order_res, list) or not order_res:
            logger.error(f'SOMETHING WENT WRONG IN ORDERS - {order_res}')
            continue
        order_cart.import_from_db(order_res[0])

        order_cart.remove_item(ticket.code)

        if order_cart.items:
            response2 = db_man.edit_row(glvars.orders_table,
                                    ('id',),
                                    (order_cart.id,),
                                    ('tickets_bought',),
                                    (order_cart.to_dict()['tickets_bought'],),
                                    db_conn)
        else:
            response2 = db_man.delete_row(str(glvars.orders_table), 'id', str(order_cart.id), db_conn)
        if not response2['success']:
            logger.error(response2['message'])
            continue

        logger.info(f"TICKET EDIT {row[0]} - {response['success']}: {response['message']}")

    commit_res = db_man.commit(db_conn)
    logger.info(f"COMMIT - {commit_res['success']}: {commit_res['message']}")

    logger.info('\n Successfully pruned expired \tickets! \n')


def loop():
    while True:
        logger.info('Start prune! \n')
        prune_tickets()
        logger.info('Finished Prune! \n')
        time.sleep(3600)

if __name__ == '__main__':
    with app.app_context():
        try:
            logger.info("Start Prune!")
    # loop()
            prune_tickets()
            prune_ghost_orders()
        except Exception as e:
            logger.error(f"Prune failed: {e}")
