from flask import Blueprint, Flask, request, session
from flask_caching import Cache
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

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

app.config["SESSION_FILE_DIR"] = "/home/admin/scc-lottery-backend/tmp/flask_sessions"

app.config["CACHE_TYPE"] = "simple"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300
Session(app)
CORS(
    app,
    supports_credentials=True,
    origins=[
        "http://localhost:5173",
        "https://lucky27.kawdai.org",
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
    limit = request.args.get("limit") or 28

    query = f"SELECT * FROM {glvars.tickets_table} WHERE status = 'available' LIMIT {limit} OFFSET {offset}"

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

    return glvars.ReturnData(
        True, "Ok!", data=data, user_session=session_data
    ).response()


@app.route("/version")
def version():
    return glvars.ReturnMessage(True, "Backend: v.0.2.1").response()


@app.route("/search")
def search():
    q = request.args.get("q")
    offset = request.args.get("offset")

    query = f"SELECT * FROM {glvars.tickets_table} WHERE status = 'available' AND code LIKE ? LIMIT 28 OFFSET ?"

    res = db_man.execute_query(query, (q, offset))
    return glvars.ReturnData(True, "OK!", data=res).response()


@app.route("/bought_data")
def get_bought_data():
    user = session.get("user_info")
    if not user:
        return glvars.ReturnMessage(False, "You're not logged in!").response()

    query = f"SELECT t.code, t.status, t.note_for FROM {glvars.tickets_table} t JOIN {glvars.users_table} u ON t.buyer_id = u.id WHERE t.buyer_id = ? AND t.status != ? AND t.status != ?"

    params = [user["id"], "ordered", "available"]

    res = db_man.execute_query(query, params)
    if not isinstance(res, list) or not res:
        return glvars.ReturnMessage(False, "Not found!").response()

    return glvars.ReturnData(True, "Found!", data=res).response()


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
    return glvars.ReturnMessage(True, "Logged out!").response()


@app.route("/load_user")
def load_user():
    if not session.get("user_info"):
        return glvars.ReturnMessage(False, "User not logged in!").response()
    return glvars.ReturnData(True, "Ok!", user=session.get("user_info")).response()


@app.route("/is_admin")
def is_admin():
    user = session.get("user_info")
    if not user:
        return glvars.ReturnMessage(False, "You are not an admin!").response()

    if user["role"] != "admin":
        return glvars.ReturnMessage(False, "You are not an admin!").response()

    return glvars.ReturnMessage(True, "You are an admin!").response()


###############
# Cart Routes #
###############
@cart_bp.route("/")
def cart_root():
    if not session.get("cart"):
        results = order_man.create_cart(session.get("user_info"))
        if not results["success"]:
            return glvars.ReturnMessage(
                False, f"Something went wrong in making a cart: {results['message']}"
            ).response()
        session["cart"] = results["cart"]

    if not session.get("user_info"):
        return glvars.ReturnMessage(False, "Log in first").response()

    return glvars.ReturnData(
        True,
        "Cart Data is here",
        data=session.get("cart"),
        user=session.get("user_info"),
    ).response()


@cart_bp.route("/add", methods=["POST"])
def add_to_cart():
    if not session.get("user_info"):
        return glvars.ReturnMessage(False, "Login first").response()

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
        return glvars.ReturnData(False, response["message"]).response()

    session["user_info"] = response["user"]
    session["cart"] = response["cart"]

    return glvars.ReturnData(True, "Added to cart").response()


@cart_bp.route("/remove", methods=["POST"])
def remove_from_cart():
    if not session.get("user_info"):
        return glvars.ReturnMessage(False, "Login first").response()

    if not session.get("cart"):
        return glvars.ReturnMessage(False, "No Cart!").response()

    data = request.get_json()
    ticket_code = data.get("code")
    response = order_man.remove_tickets_from_cart(
        ticket_code, session.get("user_info"), session.get("cart")
    )

    if not response["success"]:
        return glvars.ReturnData(False, response["message"]).response()

    session["user_info"] = response["user"]
    session["cart"] = response["cart"]

    return glvars.ReturnData(True, "Added to cart").response()


@cart_bp.route("/confirm", methods=["POST"])
def confirm_cart():
    data = request.get_json()
    img_data = data.get("img_link")

    if not glvars.is_base64_image(img_data) or not img_data:
        return glvars.ReturnMessage(
            False, "An error occured with the image!"
        ).response()

    res = order_man.confirm_bought(
        img_data, session.get("user_info"), session.get("cart")
    )

    if not res["success"]:
        return glvars.ReturnMessage(False, res["message"]).response()

    session["cart"] = res["cart"]
    session["user_info"] = res["user"]

    if (
        session["user_info"]["role"] == "admin"
        or session["user_info"]["role"] == "agent"
    ):
        if not order_man.confirm_cart(res["order_id"])["success"]:
            return glvars.ReturnMessage(
                False, "Something went wrong confirming the tickets"
            ).response()

    print(f"SESSION ROLE: {session['user_info']['role']}")

    return glvars.ReturnMessage(True, res["message"]).response()


#######################
# Orders Route        #
#######################


@orders_bp.route("/")
def load_orders():
    offset = request.args.get("offset") or "0"
    search_q = request.args.get("q") or None
    search_for = request.args.get("type") or None

    if search_q and search_for:
        params = f'%{search_q}%'
        query = f"SELECT o.id, u.id, u.name, o.tickets_bought, CASE WHEN o.confirmed = 0 THEN 'processing' WHEN o.confirmed = 1 THEN 'confirmed' END AS status, o.id FROM {glvars.orders_table} o JOIN {glvars.users_table} u ON o.buyer_id = u.id WHERE o.confirmed = 0 AND o.is_in_cart = 0 AND {search_for} LIKE ? LIMIT 28 OFFSET {offset}"
        res = db_man.execute_query(query, (params,))
    else:
        query = f"SELECT o.id, u.id, u.name, o.tickets_bought, CASE WHEN o.confirmed = 0 THEN 'processing' WHEN o.confirmed = 1 THEN 'confirmed' END AS status, o.id FROM {glvars.orders_table} o JOIN {glvars.users_table} u ON o.buyer_id = u.id WHERE o.confirmed = 0 AND o.is_in_cart = 0 LIMIT 28 OFFSET {offset}"
        res = db_man.execute_query(query)
    
    if not isinstance(res, list):
        print('SOMETHING WENT WRONG IN LOADING ORDERS!')
        return glvars.ReturnMessage(
            False, "Something went wrong in loading orders!"
        ).response()

    orders = []
    img_data = []
    for row in res:
        orders.append([row[0], row[1], row[2], row[3], row[4]])
        img_data.append(row[5])

    return glvars.ReturnData(
        True, "Orders Data", orders=orders, img_data=img_data
    ).response()


@orders_bp.route("/load_all")
def load_all():
    offset = request.args.get("offset") or 0
    search_q = request.args.get("q") or None
    search_for = request.args.get('type') or None

    if search_q and search_for:
        params = f'%{search_q}%'
        query = f"SELECT o.id, u.id, u.name, o.tickets_bought, CASE WHEN o.confirmed = 0 THEN 'processing' WHEN o.confirmed = 1 THEN 'confirmed' END AS status, o.id FROM {glvars.orders_table} o JOIN {glvars.users_table} u ON o.buyer_id = u.id WHERE {search_for} LIKE ? LIMIT 15 OFFSET {offset}"
        res = db_man.execute_query(query, (params,))
    else:
        query = f"SELECT o.id, u.id, u.name, o.tickets_bought, CASE WHEN o.confirmed = 0 THEN 'processing' WHEN o.confirmed = 1 THEN 'confirmed' END AS status, o.id FROM {glvars.orders_table} o JOIN {glvars.users_table} u ON o.buyer_id = u.id LIMIT 15 OFFSET {offset}"
        res = db_man.execute_query(query)

    if not isinstance(res, list):
        return glvars.ReturnMessage(
            False, "Something went wrong in loading orders!"
        ).response()

    orders = []
    img_data = []
    for row in res:
        orders.append([row[0], row[1], row[2], row[3], row[4]])
        img_data.append(row[5])

    return glvars.ReturnData(
        True, "Orders Data", orders=orders, img_data=img_data
    ).response()


@orders_bp.route("/load_img", methods=["POST"])
def load_img():
    data = request.get_json()
    img_id = data["id"]
    query = f"SELECT img_link FROM {glvars.orders_table} WHERE id = ?"

    res = db_man.execute_query(query, (img_id,))
    if not isinstance(res, list) or not res:
        return glvars.ReturnMessage(
            False, "Something went wrong in loading orders!"
        ).response()
    try:
        img_data = res[0]
    except IndexError:
        return glvars.ReturnMessage(False, "Index Error in Load Image").response()
    print(img_data)

    return glvars.ReturnData(
        True, f"Image Data of {img_id}", img_data=img_data
    ).response()


@orders_bp.route("/confirm", methods=["POST"])
def confirm_order():
    res = request.get_json()
    order_id = res["code"][0]

    print(res)

    confirm_res = order_man.confirm_cart(order_id)
    if not confirm_res["success"]:
        return glvars.ReturnMessage(False, "Order not confirmed!").response()

    return glvars.ReturnMessage(True, "Confirmed order").response()


@orders_bp.route("/edit_note", methods=["POST"])
def edit_note():
    res = request.get_json()
    ticket_code = res["code"]
    note = res["note_for"]

    edit_ticket_note = order_man.edit_note(note, ticket_code)
    if not edit_ticket_note["success"]:
        return glvars.ReturnMessage(False, edit_ticket_note["message"]).response()

    return glvars.ReturnMessage(True, edit_ticket_note["message"]).response()


@orders_bp.route("/cancel", methods=["POST"])
def cancel_order():
    res = request.get_json()
    order_id = res["code"][0]

    cancel_res = order_man.cancel_cart(order_id)
    if not cancel_res["success"]:
        return glvars.ReturnMessage(False, cancel_res["message"]).response()

    return glvars.ReturnMessage(True, "Cancelled Order").response()


############
# USERS BP #
############
@users_bp.route("/")
def get_users():
    offset = int(request.args.get("offset") or "0")
    q = request.args.get("q") or None
    search_for = request.args.get("type") or "id"
    limit = request.args.get("limit") or '15'

    try:
        res = users_man.get_users(limit=int(limit), offset=offset, q=q, search_for=search_for)
    except Exception:
        return glvars.ReturnMessage(False, "Limit must be a number!").response()

    if not res["success"]:
        return glvars.ReturnMessage(
            False, "Something went wrong with the database! **users**"
        ).response()

    main_data = []
    personal_info = []

    for row in res["data"]:
        main_data.append([row[0], row[1], row[2], row[5], row[7]])
        personal_info.append([row[3], row[4], row[5], row[6], row[7]])

    return glvars.ReturnData(
        True, "Fetched user data", data=main_data, personal_info=personal_info
    ).response()


@users_bp.route("/set_role", methods=["POST"])
def set_role():
    data = request.get_json()
    print(data)
    if not data["role"]:
        return glvars.ReturnMessage(False, "Select a role!").response()

    user_data = users_man.get_user(data["id"])
    user = user_data["data"]

    user.set_vars(["role"], [data["role"]])
    print("User OBJ Role: ", user.role)

    db_conn = db_man.get_conn()

    usr_edit = db_man.edit_row(
        glvars.users_table, ("id",), (user.id,), ("role",), (user.role,), db_conn
    )

    if not usr_edit["success"]:
        return glvars.ReturnMessage(False, usr_edit["message"]).response()

    commit_res = db_man.commit(db_conn)
    if not commit_res["success"]:
        return glvars.ReturnMessage(
            False, f"Could not commit: {commit_res['message']}"
        ).response()

    return glvars.ReturnMessage(True, f"Role set to {data['role']}").response()


@users_bp.route("/get_user", methods=["POST"])
def get_user():
    data = request.get_json()
    
    q = data["id"]
    if not q:
        return glvars.ReturnMessage(False, "No User ID provided!").response()

    user_import = users_man.get_user(q)
    if not user_import["success"]:
        return glvars.ReturnMessage(False, "User not found!").response()

    user = user_import["data"]

    return glvars.ReturnData(True, f"Here's user {q}", data=user.to_dict()).response()


@users_bp.route("/add_user", methods=["POST"])
def add_user():
    data = request.get_json()
    u_name = data["name"]
    u_phone_number = data["phone_number"]
    u_password = data["password"]
    u_address = data["address"]

    if None in [u_name, u_phone_number, u_password, u_address]:
        return glvars.ReturnMessage(False, "Insufficient data!").response()

    db_conn = db_man.get_conn()
    u_add = users_man.add_user(u_name, u_phone_number, u_password, u_address, db_conn)

    if not u_add["success"]:
        return glvars.ReturnMessage(False, u_add["message"]).response()

    commit_res = db_man.commit(db_conn)
    if not commit_res["success"]:
        return glvars.ReturnMessage(
            False, f"Could not commit: {commit_res['message']}"
        ).response()

    return glvars.ReturnMessage(True, "Added User!").response()


@users_bp.route("/del_user", methods=['POST'])
def del_user():
    data = request.get_json()
    u_id = data['id']
    if not u_id:
        return glvars.ReturnMessage(False, "Insufficient data!").response()

    db_conn = db_man.get_conn()
    u_del = users_man.delete_user(u_id, db_conn)
    if not u_del["success"]:
        return glvars.ReturnMessage(False, u_del["message"]).response()
    
    commit_res = db_man.commit(db_conn)
    if not commit_res:
        return glvars.ReturnMessage(False, commit_res['message']).response()

    return glvars.ReturnMessage(True, "Deleted user!").response()


@users_bp.route("/edit_user", methods=["POST"])
def edit_user():
    data = request.get_json()
    user_import = users_man.get_user(data["id"])
    if not user_import["success"]:
        return glvars.ReturnMessage(False, user_import["message"]).response()

    user = user_import["data"]

    filtered_data = {k: v for k, v in data.items() if k != "id"}
    if not filtered_data:
        return glvars.ReturnMessage(False, "No params provided").response()

    db_conn = db_man.get_conn()
    user_edit = users_man.edit_user(
        user.id, list(filtered_data.keys()), list(filtered_data.values()), db_conn
    )
    if not user_edit["success"]:
        return glvars.ReturnMessage(False, user_edit["message"]).response()

    commit_res = db_man.commit(db_conn)
    if not commit_res["success"]:
        return glvars.ReturnMessage(
            False, f"Could not commit data: {commit_res['message']}"
        ).response()

    return glvars.ReturnData(True, "Edited user!", data=user.to_dict()).response()


@users_bp.route("/load_pfp")
def load_img():
    q = request.args.get('q') or None
    search_for = request.args.get('type') or None
    if not q or not search_for:
        return glvars.ReturnMessage(False, 'Insufficient data!').response()

    query = f"SELECT pfp FROM {glvars.users_table} WHERE {search_for} = ?"

    res = db_man.execute_query(query, (q,))
    if not isinstance(res, list) or not res:
        return glvars.ReturnMessage(
            False, "Something went wrong in loading orders!"
        ).response()

    img_data = res
    print(img_data)

    return glvars.ReturnData(
        True, f"Image Data", img_data=img_data
    ).response()


##############
# Tickets BP #
##############
@tickets_bp.route("/")
def get_tickets():
    offset = int(request.args.get("offset") or "0")
    q = request.args.get("q") or None
    search_for = request.args.get("type") or None

    res = tickets_man.get_records(limit=15, offset=offset, q=q, search_for=search_for)

    if not res["success"]:
        return glvars.ReturnMessage(
            False, "Something went wrong with the database! **tickets**"
        ).response()

    print(f"RES: {res}")

    return glvars.ReturnData(True, res["message"], data=res["data"]).response()


@tickets_bp.route("/get_ticket")
def get_ticket():
    data = request.get_json()
    q = data["code"] or None
    ticket_import = tickets_man.get_ticket(code=q)
    if not ticket_import["success"]:
        return glvars.ReturnMessage(False, ticket_import["message"]).response()

    ticket = ticket_import["data"]

    return glvars.ReturnData(True, "Some ticket...", data=ticket.to_dict()).response()


@tickets_bp.route("/add_ticket", methods=["POST"])
def add_ticket():
    db_conn = db_man.get_conn()

    data = request.get_json()
    code = data["code"] or None
    if not code:
        return glvars.ReturnMessage(False, "No code provided").response()

    codes = str(code).strip().split(";")
    print(f"LENGTH CODES: {len(codes)}")
    print(f"CODE: {code}")
    print(f"CODES: {codes}")
    # if len(codes) == 0 and code:
    #     codes = [code]

    new_codes = list()

    for c in codes:
        c_mod = str(c).split("-")

        if len(c_mod) == 2:
            if int(c_mod[0]) > int(c_mod[1]):
                c_mod = [c_mod[1], c_mod[0]]

            for j in range(int(c_mod[0]), int(c_mod[1]) + 1):
                new_codes.append(str(j))
                res = tickets_man.add_ticket(str(j), db_conn)
                if not res["success"]:
                    print(f"FAILURE! {res['message']}")
                    continue

        elif len(c_mod) == 1:
            new_codes.append(str(c_mod[0]))
            res = tickets_man.add_ticket(str(c_mod[0]), db_conn)
            if not res["success"]:
                print(f"FAILURE! {res['message']}")
                continue

    print(f"NEW CODES: {new_codes}")

    commit_res = db_man.commit(db_conn)
    if not commit_res["success"]:
        return glvars.ReturnMessage(
            False, f"Could not commit: {commit_res['message']}"
        ).send()

    return glvars.ReturnData(
        True, "Added ticket(s)!", added_tickets=new_codes
    ).response()


@tickets_bp.route("/del_ticket", methods=["POST"])
def del_ticket():
    data = request.get_json()
    print(f"DATA: {data}")
    code = data["code"] or None
    if not code:
        return glvars.ReturnMessage(False, "No code provided").response()

    res = tickets_man.delete_ticket(code)
    if not res["success"]:
        return glvars.ReturnMessage(
            False, f"Something in the tickets went wrong: {res['message']}"
        ).response()
    return glvars.ReturnMessage(True, "Deleted ticket!").response()


@tickets_bp.route("/edit_ticket", methods=["POST"])
def edit_ticket():
    db_conn = db_man.get_conn()

    data = request.get_json()
    ticket_import = tickets_man.get_ticket(data["code"])
    if not ticket_import["success"]:
        return glvars.ReturnMessage(False, ticket_import["message"]).response()

    ticket = ticket_import["data"]

    filtered_data = {k: v for k, v in data.items() if k != "code"}
    if not filtered_data:
        return glvars.ReturnMessage(False, "No params provided").response()

    if not ticket or not ticket.is_available():
        return glvars.ReturnMessage(False, "Not Allowed!").response()

    tickets_man.edit_ticket(
        ticket.code, list(filtered_data.keys()), list(filtered_data.values()), db_conn
    )

    commit_res = db_man.commit(db_conn)
    if not commit_res["success"]:
        return glvars.ReturnMessage(
            False, f"Could not commit: {commit_res['message']}"
        ).send()

    return glvars.ReturnData(True, "Edited ticket!", data=ticket.to_dict()).response()


app.register_blueprint(cart_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(users_bp)
app.register_blueprint(tickets_bp)
