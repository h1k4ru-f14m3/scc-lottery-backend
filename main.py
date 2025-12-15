# import prune_tickets
# from threading import Thread

# from functions.global_vars import setup_logger
from routes import app

# setup_logger()

application = app

if __name__ == "__main__":
    # Thread(target=prune_tickets.loop).start()
    application.run(host="0.0.0.0", port=5000, debug=True)
