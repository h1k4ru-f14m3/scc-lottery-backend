from flask import Blueprint, Flask, redirect, render_template, request, session
from flask_caching import Cache
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

import functions.cart as cart
import functions.global_vars as glvars
import functions.orders as orders
import functions.tickets as tickets
import functions.users as usr
from flask_session import Session
from functions.db_man import DBManager

app = Flask(__name__)
app.config["TEMPLATE_AUTO_RELOAD"] = True
app.secret_key = glvars.secret_key
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Uncomment the following if you want to use sessions
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_HTTPONLY"] = True

app.config["SESSION_FILE_DIR"] = "/tmp/flask_sessions"

app.config["CACHE_TYPE"] = "simple"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300
Session(app)
CORS(
    app,
    supports_credentials=True,
    origins=[
        "http://localhost:5173",
        "https://scc-lottery.netlify.app",
        "https://scc-lottery-frontend-rho.vercel.app",
        "https://scc-lottery.h1k4ru.dev",
    ],
)
Cache().init_app(app)

# Blueprints
cart_bp = Blueprint(
    "cart", __name__, url_prefix="/cart", template_folder="./templates/pages/cart/"
)
users_bp = Blueprint("users", __name__, url_prefix="/user")
orders_bp = Blueprint("order", __name__, url_prefix="/order")
tickets_bp = Blueprint("tickets", __name__, url_prefix="/tickets")

# Classes (Managers)
db_man = DBManager()
auth_man = usr.Authentication(db_man)
order_man = orders.OrderManager(db_man)
tickets_man = tickets.TicketsManager(db_man)
users_man = usr.UserManager(db_man)

order_man.set_tickets_man(tickets_man)


# The ROOT
@app.route("/")
def index():
    # query = f"SELECT t.code, t.buyer_id, u.name, u.address, u.phone_number FROM {glvars.tickets_table} t JOIN {glvars.users_table} u ON t.buyer_id = u.id;"
    q = request.args.get("q")
    offset = request.args.get("offset") or 0

    query = f"SELECT * FROM {glvars.tickets_table} WHERE status = 'available' LIMIT 28 OFFSET {offset}"

    if q:
        refined_q = f"%{q}%"
        query = f"SELECT * FROM {glvars.tickets_table} WHERE status = 'available' AND code LIKE ? LIMIT 28 OFFSET {offset}"
        data = db_man.execute_query(query, (refined_q,))
        print("With q: ", data)
    else:
        data = db_man.execute_query(query)
        print("Without q: ", data)

    session_data = session.get("user_info")
    if not session_data:
        session_data = {}

    return glvars.ReturnData(True, "Ok!", data=data, user_session=session_data).send(
        "json"
    )


@app.route("/update")
def update():
    return glvars.ReturnMessage(True, "Backend is updated! v.0.1.1").send("json")


@app.route("/search")
def search():
    q = request.args.get("q")
    offset = request.args.get("offset")

    query = f"SELECT * FROM {glvars.tickets_table} WHERE status = 'available' AND code LIKE ? LIMIT 28 OFFSET ?"

    res = db_man.execute_query(query, (q, offset))
    return glvars.ReturnData(True, "OK!", data=res).send("json")


@app.route("/bought_data")
def get_bought_data():
    user = session.get("user_info")

    query = f"SELECT t.code, t.status, t.note_for FROM {glvars.tickets_table} t JOIN {glvars.users_table} u ON t.buyer_id = u.id WHERE t.buyer_id = ? AND t.status != ? AND t.status != ?"

    params = [user["id"], "ordered", "available"]

    res = db_man.execute_query(query, params)
    if len(res) == 0:
        return glvars.ReturnMessage(False, "Not found!").send("json")

    return glvars.ReturnData(True, "Found!", data=res).send("json")


@app.route("/register", methods=["POST"])
def register():
    form_data = request.get_json()
    return auth_man.register(form_data)


@app.route("/login", methods=["GET", "POST"])
def login():
    form_data = request.get_json()
    return auth_man.login(form_data)


@app.route("/logout")
def logout():
    session.clear()
    return glvars.ReturnMessage(True, "Logged out!").send("json")


@app.route("/load_user")
def load_user():
    if not session.get("user_info"):
        return glvars.ReturnMessage(False, "User not logged in!").send("json")
    return glvars.ReturnData(True, "Ok!", user=session.get("user_info")).send("json")


@app.route("/is_admin")
def is_admin():
    if not session.get("user_info") or session.get("user_info")["role"] != "admin":
        return glvars.ReturnMessage(False, "You are not an admin!").send("json")

    return glvars.ReturnMessage(True, "You are an admin!").send("json")


###############
# Cart Routes #
###############
@cart_bp.route("/")
def cart():
    if not session.get("cart"):
        results = order_man.create_cart(session.get("user_info"))
        session["cart"] = results["cart"]

    if not session.get("user_info"):
        return glvars.ReturnMessage(False, "Log in first").send("json")

    return glvars.ReturnData(
        True,
        "Cart Data is here",
        data=session.get("cart"),
        user=session.get("user_info"),
    ).send("json")


@cart_bp.route("/add", methods=["POST"])
def add_to_cart():
    if not session.get("user_info"):
        return glvars.ReturnMessage(False, "Login first").send("json")

    if not session.get("cart"):
        results = order_man.create_cart(session.get("user_info"))
        session["cart"] = results["cart"]

    data = request.get_json()
    ticket_code = data.get("code")
    response = order_man.add_tickets_to_cart(
        ticket_code, session.get("user_info"), session.get("cart")
    )

    print(response)

    if not response["success"]:
        return glvars.ReturnData(False, response["message"]).send("json")

    session["user_info"] = response["user"]
    session["cart"] = response["cart"]

    return glvars.ReturnData(True, "Added to cart").send("json")


@cart_bp.route("/remove", methods=["POST"])
def remove_from_cart():
    if not session.get("user_info"):
        return glvars.ReturnMessage(False, "Login first").send("json")

    if not session.get("cart"):
        return glvars.ReturnMessage(False, "No Cart!").send("json")

    data = request.get_json()
    ticket_code = data.get("code")
    response = order_man.remove_tickets_from_cart(
        ticket_code, session.get("user_info"), session.get("cart")
    )

    if not response["success"]:
        return glvars.ReturnData(False, response["message"]).send("json")

    session["user_info"] = response["user"]
    session["cart"] = response["cart"]

    return glvars.ReturnData(True, "Added to cart").send("json")


@cart_bp.route("/confirm", methods=["POST"])
def confirm_cart():
    data = request.get_json()
    img_data = data.get("img_link")

    if not glvars.is_base64_image(img_data):
        return glvars.ReturnMessage(False, "An error occured with the image!").send(
            "json"
        )

    res = order_man.confirm_bought(
        img_data, session.get("user_info"), session.get("cart")
    )

    if not res["success"]:
        return glvars.ReturnMessage(False, res["message"]).send("json")

    session["cart"] = res["cart"]
    session["user_info"] = res["user"]

    if session['user_info']['role'] == 'admin' or session['user_info']['role'] == 'agent':
        if not order_man.confirm_cart(res['order_id'])['success']:
            return glvars.ReturnMessage(False, 'Something went wrong confirming the tickets').send('json')

    print(f'SESSION ROLE: {session['user_info']['role']}')

    return glvars.ReturnMessage(True, res["message"]).send("json")


#######################
# Orders Route        #
#######################


@orders_bp.route("/")
def load_orders():
    offset = request.args.get("offset") or 0

    query = f"SELECT o.id, u.id, u.name, o.tickets_bought, CASE WHEN o.confirmed = 0 THEN 'processing' WHEN o.confirmed = 1 THEN 'confirmed' END AS status, o.id FROM {glvars.orders_table} o JOIN {glvars.users_table} u ON o.buyer_id = u.id WHERE o.confirmed = 0 AND o.is_in_cart = 0 LIMIT 28 OFFSET {offset}"
    res = db_man.execute_query(query)

    orders = []
    img_data = []
    for row in res:
        orders.append([row[0], row[1], row[2], row[3], row[4]])
        img_data.append(row[5])

    return glvars.ReturnData(
        True, "Orders Data", orders=orders, img_data=img_data
    ).send("json")


@orders_bp.route("/load_all")
def load_all():
    offset = request.args.get("offset") or 0

    query = f"SELECT o.id, u.id, u.name, o.tickets_bought, CASE WHEN o.confirmed = 0 THEN 'processing' WHEN o.confirmed = 1 THEN 'confirmed' END AS status, o.id FROM {glvars.orders_table} o JOIN {glvars.users_table} u ON o.buyer_id = u.id LIMIT 28 OFFSET {offset}"
    res = db_man.execute_query(query)

    orders = []
    img_data = []
    for row in res:
        orders.append([row[0], row[1], row[2], row[3], row[4]])
        img_data.append(row[5])

    return glvars.ReturnData(
        True, "Orders Data", orders=orders, img_data=img_data
    ).send("json")


@orders_bp.route("/load_img", methods=["POST"])
def load_img():
    data = request.get_json()
    img_id = data["id"]
    query = f"SELECT img_link FROM {glvars.orders_table} WHERE id = ?"

    res = db_man.execute_query(query, (img_id,))
    try:
        img_data = res[0]
    except IndexError:
        return glvars.ReturnMessage(False, "Index Error in Load Image").send("json")
    print(img_data)

    return glvars.ReturnData(True, f"Image Data of {img_id}", img_data=img_data).send(
        "json"
    )


@orders_bp.route("/confirm", methods=["POST"])
def confirm_order():
    res = request.get_json()
    order_id = res["code"][0]

    print(res)

    confirm_res = order_man.confirm_cart(order_id)
    if not confirm_res["success"]:
        return glvars.ReturnMessage(False, "Order not confirmed!").send("json")

    return glvars.ReturnMessage(True, "Confirmed order").send("json")


@orders_bp.route("/edit_note", methods=["POST"])
def edit_note():
    res = request.get_json()
    ticket_code = res["code"]
    note = res["note_for"]

    edit_ticket_note = order_man.edit_note(note, ticket_code)
    if not edit_ticket_note["success"]:
        return glvars.ReturnMessage(False, edit_ticket_note["message"]).send("json")

    return glvars.ReturnMessage(True, edit_ticket_note["message"]).send("json")


@orders_bp.route("/cancel", methods=["POST"])
def cancel_order():
    res = request.get_json()
    order_id = res['code'][0]

    cancel_res = order_man.cancel_cart(order_id)
    if not cancel_res['success']:
        return glvars.ReturnMessage(False, cancel_res['message']).send('json')
    
    return glvars.ReturnMessage(True, 'Cancelled Order').send('json')


############
# USERS BP #
############
@users_bp.route("/")
def get_users():
    query = f"SELECT id, name, role, tickets_ordered, tickets_bought, phone_number, email, address FROM {glvars.users_table}"
    res = db_man.execute_query(query)

    main_data = []
    personal_info = []

    for row in res:
        main_data.append([row[0], row[1], row[2]])
        personal_info.append([row[3], row[4], row[5], row[6], row[7]])

    return glvars.ReturnData(
        True, "Fetched user data", data=main_data, personal_info=personal_info
    ).send("json")


@users_bp.route("/set_role", methods=["POST"])
def set_role():
    data = request.get_json()
    print(data)
    if not data["role"]:
        return glvars.ReturnMessage(False, "Select a role!").send("json")

    user_data = users_man.get_user(data["id"])
    user = user_data["data"]

    user.set_vars(["role"], [data["role"]])
    print("User OBJ Role: ", user.role)

    db_conn = db_man.get_conn()

    usr_edit = db_man.edit_row(
        glvars.users_table, ("id",), (user.id,), ("role",), (user.role,), db_conn
    )

    if not usr_edit["success"]:
        return glvars.ReturnMessage(False, usr_edit["message"]).send("json")

    commit_res = db_man.commit(db_conn)
    if not commit_res['success']:
        return glvars.ReturnMessage(False, f'Could not commit: {commit_res['message']}').send('json')

    return glvars.ReturnMessage(True, f"Role set to {data['role']}").send("json")


@users_bp.route("/get_user", methods=["POST"])
def get_user():
    data = request.get_json()
    q = data["id"]
    if not q:
        return glvars.ReturnMessage(False, "No User ID provided!").send("json")

    user_import = users_man.get_user(q)
    if not user_import["success"]:
        return glvars.ReturnMessage(False, "User not found!").send("json")

    user = user_import["data"]

    return glvars.ReturnData(True, f"Here's user {q}", data=user.to_dict()).send("json")


@users_bp.route("/add_user", methods=["POST"])
def add_user():
    data = request.get_json()
    u_name = data["name"]
    u_phone_number = data["phone_number"]
    u_password = data["password"]

    if None in [u_name, u_phone_number, u_password]:
        return glvars.ReturnMessage(False, "Insufficient data!").send("json")

    db_conn = db_man.get_conn()
    u_add = users_man.add_user(u_name, u_phone_number, u_password, db_conn)
    if not u_add["success"]:
        return glvars.ReturnMessage(False, u_add["message"]).send("json")
    
    commit_res = db_man.commit(db_conn)
    if not commit_res['success']:
        return glvars.ReturnMessage(False, f'Could not commit: {commit_res['message']}').send('json')

    return glvars.ReturnMessage(True, "Added User!").send("json")


@users_bp.route("/del_user")
def del_user():
    u_id = request.args.get("id")
    if not u_id:
        return glvars.ReturnMessage(False, "Insufficient data!").send("json")

    u_del = users_man.delete_user(u_id)
    if not u_del["success"]:
        return glvars.ReturnMessage(False, u_del["message"]).send("json")

    return glvars.ReturnMessage(True, "Deleted user!").send("json")


@users_bp.route("edit_user")
def edit_user():
    data = request.get_json()
    user_import = users_man.get_user(data["id"])
    if not user_import["success"]:
        return glvars.ReturnMessage(False, user_import["message"]).send("json")

    user = user_import["data"]

    filtered_data = {k: v for k, v in data.items() if k != "id"}

    db_conn = db_man.get_conn()
    user_edit = users_man.edit_user(user.id, filtered_data.keys, filtered_data.values, db_conn)
    if not user_edit["success"]:
        return glvars.ReturnMessage(False, user_edit["message"]).send("json")
    
    commit_res = db_man.commit(db_conn)
    if not commit_res['success']:
        return glvars.ReturnMessage(False, f'Could not commit data: {commit_res['message']}').send('json')

    return glvars.ReturnData(True, "Edited ticket!", data=user.to_dict()).send("json")


##############
# Tickets BP #
##############
@tickets_bp.route("/")
def get_tickets():
    offset = request.args.get("offset") or 0
    q = request.args.get("q") or None
    search_for = request.args.get("type") or None

    res = tickets_man.get_records(limit=15, offset=offset, q=q, search_for=search_for)

    if not res["success"]:
        return glvars.ReturnMessage(
            False, "Something went wrong with the database! **tickets**"
        ).send("json")
    
    print(f'RES: {res}')

    return glvars.ReturnData(True, res["message"], data=res["data"]).send("json")


@tickets_bp.route("/get_ticket")
def get_ticket():
    data = request.get_json()
    q = data["code"] or None
    ticket_import = tickets_man.get_ticket(code=q)
    if not ticket_import["success"]:
        return glvars.ReturnMessage(False, ticket_import["message"]).send("json")

    ticket = ticket_import["data"]

    return glvars.ReturnData(True, "Some ticket...", data=ticket.to_dict()).send("json")


@tickets_bp.route("/add_ticket", methods=["POST"])
def add_ticket():
    data = request.get_json()
    code = data["code"] or None
    if not code:
        return glvars.ReturnMessage(False, "No code provided").send("json")

    db_conn = db_man.get_conn()
    res = tickets_man.add_ticket(code, db_conn)
    if not res["success"]:
        return glvars.ReturnMessage(False, f"Something in the tickets went wrong: {res['message']}").send("json")
    
    commit_res = db_man.commit(db_conn)
    if not commit_res['success']:
        return glvars.ReturnMessage(False, f'Could not commit: {commit_res['message']}').send()

    return glvars.ReturnMessage(True, "Added ticket!").send("json")


@tickets_bp.route("/del_ticket", methods=["POST"])
def del_ticket():
    data = request.get_json()
    code = data["code"] or None
    if not code:
        return glvars.ReturnMessage(False, "No code provided").send("json")

    res = tickets_man.delete_ticket(code)
    if not res["success"]:
        return glvars.ReturnMessage(
            False, f"Something in the tickets went wrong: {res['message']}"
        ).send("json")
    return glvars.ReturnMessage(True, "Deleted ticket!").send("json")


@tickets_bp.route("/edit_ticket", methods=["POST"])
def edit_ticket():
    data = request.get_json()
    ticket_import = tickets_man.get_ticket(data["code"])
    if not ticket_import["success"]:
        return glvars.ReturnMessage(False, ticket_import["message"]).send("json")

    ticket = ticket_import["data"]

    filtered_data = {k: v for k, v in data.items() if k != "code" or k != "changecode"}
    if data["changecode"] == "true":
        filtered_data = data

    if not ticket or not ticket.is_available():
        return glvars.ReturnMessage(False, "Not Allowed!").send("json")

    tickets_man.edit_ticket(ticket.code, filtered_data.keys, filtered_data.values)

    return glvars.ReturnData(True, "Edited ticket!", data=ticket.to_dict()).send("json")


app.register_blueprint(cart_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(users_bp)
app.register_blueprint(tickets_bp)
