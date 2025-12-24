from functions.db_man import DBManager
from functions.tickets import Ticket
import functions.global_vars as glvars
import datetime
import time
import logging

db_man = DBManager('/home/admin/scc-lottery-backend/data.db')
log_file = '/home/admin/scc-lottery-backend/prune_job.log'
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def prune():
    now = datetime.datetime.now().strftime(glvars.format_code)
    query = f'SELECT * FROM {glvars.tickets_table} WHERE expire_at <= ?'
    db_conn = db_man.get_conn()
    res = db_man.execute_query(query, (now,))
    if not res:
        logger.info('No tickets...\n')
        return 

    for row in res:
        ticket = Ticket(row[0])
        query2 = f'SELECT code, status, expire_at, buyer_id, note_for FROM {glvars.tickets_table} WHERE code = ?'
        ticket.import_from_db(db_man.execute_query(query2, (row[0],))[0])

        ticket.reset()
        response = db_man.edit_row(glvars.tickets_table, 
                                   ('code',), 
                                   (ticket.code,), 
                                   ('status', 'expire_at', 'buyer_id', 'note_for'),
                                   (ticket.status, ticket.expire_at, ticket.buyer_id, ticket.note_for),
                                   db_conn)
        if not response['success']:
            logger.error(response['message'])

        logger.info(f"TICKET EDIT - {response['success']}: {response['message']}")

    commit_res = db_man.commit(db_conn)
    logger.info(f"COMMIT - {commit_res['success']}: {commit_res['message']}")

    logger.info('\n Everything went well! \n')


def loop():
    while True:
        logger.info('Start prune! \n')
        prune()
        logger.info('Finished Prune! \n')
        time.sleep(3600)

if __name__ == '__main__':
    # loop()
    prune()
    
