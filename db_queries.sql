CREATE TABLE IF NOT EXISTS tickets (
    code TEXT UNIQUE PRIMARY KEY,
    status TEXT DEFAULT 'available',
    expire_at TEXT DEFAULT NULL,
    buyer_id INTEGER DEFAULT NULL,
    note_for TEXT DEFAULT NULL,
    CONSTRAINT status CHECK (status IN ('available', 'ordered', 'processing', 'confirmed')),
    FOREIGN KEY(buyer_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER UNIQUE PRIMARY KEY AUTOINCREMENT,
    name TEXT DEFAULT NULL,
    email TEXT DEFAULT NULL,
    phone_number TEXT DEFAULT NULL,
    address TEXT DEFAULT NULL,
    password TEXT DEFAULT NULL,
    role TEXT DEFAULT 'user',
    pfp BLOB DEFAULT NULL,
    tickets_bought TEXT DEFAULT NULL,
    tickets_ordered TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER UNIQUE PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER NOT NULL,
    amount_bought INTEGER DEFAULT 0,
    tickets_bought TEXT DEFAULT NULL,
    img_link TEXT DEFAULT NULL,
    is_in_cart INTEGER DEFAULT 1,
    confirmed INTEGER DEFAULT 0,
    CONSTRAINT confirmed CHECK (confirmed < 2 AND confirmed > -1)
    CONSTRAINT is_in_cart CHECK (is_in_cart < 2 AND is_in_cart > -1)
    FOREIGN KEY(buyer_id) REFERENCES users(id)
);


