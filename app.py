from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, redirect, session, render_template_string
import sqlite3, os, hashlib

app = Flask(__name__)
import os
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE-THIS-BEFORE-PUBLIC")

DB = "shop.db"

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def setup():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
        address TEXT
    );
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        stock INTEGER DEFAULT 0,
        image TEXT
    );
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        total REAL,
        address TEXT,
        status TEXT DEFAULT 'Pending'
    );
    CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER
    );
    """)
    if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        c.execute("INSERT INTO products(name,description,price,stock,image) VALUES(?,?,?,?,?)",
                  ("Smartphone X1","Smartphone for everyday use",12999,10,""))
        c.execute("INSERT INTO products(name,description,price,stock,image) VALUES(?,?,?,?,?)",
                  ("Wireless Headphones","Wireless headphones",1499,20,""))
    c.commit()
    c.close()

setup()

STYLE = """
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Arial;background:#f2f4f7;color:#111}
header{background:#111;color:white;padding:16px;position:sticky;top:0;z-index:5}
header h2{margin:0 0 12px}
nav{display:flex;gap:8px;flex-wrap:wrap}
nav a{color:white;text-decoration:none;background:#333;padding:9px 11px;border-radius:8px;font-size:14px}
main{max-width:700px;margin:auto;padding:15px}
.hero{background:#111;color:white;border-radius:15px;padding:22px;margin-bottom:18px}
.search{display:flex;gap:8px}
input,textarea,select{width:100%;padding:13px;margin:6px 0 12px;border:1px solid #ccc;border-radius:9px;font-size:16px}
button,.btn{background:#111;color:white;border:0;padding:12px 15px;border-radius:9px;text-decoration:none;display:inline-block;cursor:pointer}
.card{background:white;padding:16px;border-radius:14px;margin:12px 0;box-shadow:0 2px 10px #0001}
.price{font-size:21px;font-weight:bold}
.row{background:white;padding:14px;border-radius:12px;margin:10px 0}
.flash{padding:12px;background:#d9ffd9;border-radius:9px;margin:10px 0}
.danger{background:#ffdede}
</style>
"""

def page(title, body):
    return f"""<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>{STYLE}</head>
<body>
<header>
<h2>🛍️ Sushant Shopping</h2>
<nav>
<a href="/">Home</a>
<a href="/cart">🛒 Cart</a>\n<a href="/assistant">🤖 Assistant</a>
<a href="/orders">📦 Orders</a>
<a href="/profile">👤 Profile</a>
<a href="/admin">⚙️ Admin</a>
</nav>
</header>
<main>{body}</main>
</body></html>"""

@app.route("/")
def home():
    q=request.args.get("q","")
    c=db()
    if q:
        products=c.execute(
            "SELECT * FROM products WHERE name LIKE ? OR description LIKE ?",
            ("%"+q+"%","%"+q+"%")).fetchall()
    else:
        products=c.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    c.close()

    cards=""
    for p in products:
        cards+=f"""
        <div class="card">
        <h3>{p['name']}</h3>
        <p>{p['description']}</p>
        <p class="price">₹{p['price']:.2f}</p>
        <p>Stock: {p['stock']}</p>
        <a class="btn" href="/product/{p['id']}">देखें</a>
        <form method="post" action="/cart/add/{p['id']}" style="display:inline">
        <button>Cart में डालें</button></form>
        </div>"""

    return page("Sushant Shopping",f"""
    <div class="hero">
    <h1>Sushant Shopping</h1>
    <p>आपकी अपनी ऑनलाइन shopping website</p>
    <form class="search">
    <input name="q" value="{q}" placeholder="सामान खोजें">
    <button>Search</button>
    </form></div>
    <h2>Products</h2>{cards}""")

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"]
        email=request.form["email"].lower()
        password=hashlib.sha256(request.form["password"].encode()).hexdigest()
        phone=request.form["phone"]
        address=request.form["address"]
        c=db()
        try:
            c.execute("INSERT INTO users(name,email,password,phone,address) VALUES(?,?,?,?,?)",
                      (name,email,password,phone,address))
            c.commit()
            user=c.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
            session["user_id"]=user["id"]
            c.close()
            return redirect("/")
        except sqlite3.IntegrityError:
            c.close()
            return page("Register","<h2>Email पहले से registered है.</h2><a class='btn' href='/register'>Back</a>")

    return page("Register","""
    <h1>Create Account</h1>
    <form method="post">
    <label>नाम</label><input name="name" required>
    <label>Email</label><input type="email" name="email" required>
    <label>Password</label><input type="password" name="password" required>
    <label>Phone</label><input name="phone">
    <label>पूरा Address</label><textarea name="address"></textarea>
    <button>Register</button>
    </form>""")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        email=request.form["email"].lower()
        password=hashlib.sha256(request.form["password"].encode()).hexdigest()
        c=db()
        u=c.execute("SELECT * FROM users WHERE email=? AND password=?",
                    (email,password)).fetchone()
        c.close()
        if u:
            session["user_id"]=u["id"]
            return redirect("/")
        return page("Login","<h2>गलत Email या Password</h2><a class='btn' href='/login'>फिर कोशिश करें</a>")

    return page("Login","""
    <h1>Login</h1>
    <form method="post">
    <label>Email</label><input type="email" name="email" required>
    <label>Password</label><input type="password" name="password" required>
    <button>Login</button>
    </form>
    <p>Account नहीं है?</p>
    <a class="btn" href="/register">Register</a>
    """)

@app.route("/product/<int:pid>")
def product(pid):
    c=db()
    p=c.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
    c.close()
    if not p:return "Product नहीं मिला"
    return page(p["name"],f"""
    <div class="card">
    <h1>{p['name']}</h1>
    <p>{p['description']}</p>
    <h2>₹{p['price']:.2f}</h2>
    <p>Stock: {p['stock']}</p>
    <form method="post" action="/cart/add/{p['id']}">
    <button>🛒 Cart में डालें</button>
    </form></div>""")

@app.post("/cart/add/<int:pid>")
def add_cart(pid):
    cart=session.get("cart",{})
    key=str(pid)
    cart[key]=int(cart.get(key,0))+1
    session["cart"]=cart
    return redirect("/cart")

@app.route("/cart")
def cart():
    cart=session.get("cart",{})
    c=db()
    items=[]
    total=0
    for pid,qty in cart.items():
        p=c.execute("SELECT * FROM products WHERE id=?",(int(pid),)).fetchone()
        if p:
            total+=p["price"]*qty
            items.append((p,qty))
    c.close()
    html="<h1>🛒 आपका Cart</h1>"
    for p,q in items:
        html+=f"""<div class="row">
        <b>{p['name']}</b><br>Quantity: {q}<br>
        ₹{p['price']*q:.2f}
        <form method="post" action="/cart/remove/{p['id']}">
        <button class="danger">Remove</button></form></div>"""
    html+=f"<h2>Total: ₹{total:.2f}</h2>"
    if items:
        html+="<a class='btn' href='/checkout'>Checkout</a>"
    else:
        html+="<p>Cart खाली है.</p>"
    return page("Cart",html)

@app.post("/cart/remove/<int:pid>")
def remove_cart(pid):
    cart=session.get("cart",{})
    cart.pop(str(pid),None)
    session["cart"]=cart
    return redirect("/cart")

@app.route("/checkout",methods=["GET","POST"])
def checkout():
    if not session.get("user_id"):
        return redirect("/login")
    cart=session.get("cart",{})
    if not cart:return redirect("/cart")
    c=db()
    total=0
    products=[]
    for pid,q in cart.items():
        p=c.execute("SELECT * FROM products WHERE id=?",(int(pid),)).fetchone()
        if p:
            products.append((p,q))
            total+=p["price"]*q
    if request.method=="POST":
        address=request.form["address"]
        cur=c.execute("INSERT INTO orders(user_id,total,address) VALUES(?,?,?)",
                      (session["user_id"],total,address))
        oid=cur.lastrowid
        for p,q in products:
            c.execute("INSERT INTO order_items(order_id,product_id,quantity) VALUES(?,?,?)",
                      (oid,p["id"],q))
            c.execute("UPDATE products SET stock=stock-? WHERE id=?",(q,p["id"]))
        c.commit()
        c.close()
        session["cart"]={}
        return page("Order","<h1>✅ Order Successfully Placed</h1><p>Order Number: #%s</p><a class='btn' href='/orders'>My Orders</a>"%oid)
    u=c.execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone()
    c.close()
    return page("Checkout",f"""
    <h1>Checkout</h1><h2>Total: ₹{total:.2f}</h2>
    <form method="post">
    <label>Delivery Address</label>
    <textarea name="address" required>{u['address'] or ''}</textarea>
    <button>Order Place करें</button></form>""")

@app.route("/orders")
def orders():
    if not session.get("user_id"):return redirect("/login")
    c=db()
    rows=c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC",
                   (session["user_id"],)).fetchall()
    c.close()
    html="<h1>📦 My Orders</h1>"
    for o in rows:
        html+=f"<div class='row'><b>Order #{o['id']}</b><br>₹{o['total']:.2f}<br>Status: {o['status']}</div>"
    if not rows:html+="<p>अभी कोई order नहीं है.</p>"
    return page("Orders",html)

@app.route("/profile",methods=["GET","POST"])
def profile():
    if not session.get("user_id"):return redirect("/login")
    c=db()
    if request.method=="POST":
        c.execute("UPDATE users SET name=?,phone=?,address=? WHERE id=?",
                  (request.form["name"],request.form["phone"],
                   request.form["address"],session["user_id"]))
        c.commit()
    u=c.execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone()
    c.close()
    return page("Profile",f"""
    <h1>👤 Profile</h1>
    <form method="post">
    <label>नाम</label><input name="name" value="{u['name']}">
    <label>Email</label><input value="{u['email']}" disabled>
    <label>Phone</label><input name="phone" value="{u['phone'] or ''}">
    <label>Address</label><textarea name="address">{u['address'] or ''}</textarea>
    <button>Save Profile</button></form>
    <p><a class="btn" href="/logout">Logout</a></p>""")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/admin")
def admin():
    # ADMIN SECURITY PATCH
    if not admin_required():
        return redirect(url_for('login'))
    c=db()
    products=c.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    orders=c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    c.close()
    html="""<h1>⚙️ Admin Panel</h1>
    <p><b>ध्यान दें:</b> यह शुरुआती mobile admin panel है.</p>
    <h2>➕ Product Add करें</h2>
    <form method="post" action="/admin/add">
    <input name="name" placeholder="Product name" required>
    <input name="description" placeholder="Description">
    <input type="number" step="0.01" name="price" placeholder="Price" required>
    <input type="number" name="stock" placeholder="Stock" required>
    <input name="image" placeholder="Image URL">
    <button>Add Product</button></form><h2>Products</h2>"""
    for p in products:
        html+=f"""<div class="row">
        <b>{p['name']}</b><br>₹{p['price']} | Stock {p['stock']}
        <form method="post" action="/admin/delete/{p['id']}">
        <button>Delete</button></form></div>"""
    html+="<h2>Orders</h2>"
    for o in orders:
        html+=f"<div class='row'>Order #{o['id']} — ₹{o['total']} — {o['status']}</div>"
    return page("Admin",html)

@app.post("/admin/add")
def admin_add():
    if not admin_required():
        return redirect(url_for('login'))
    c=db()
    c.execute("INSERT INTO products(name,description,price,stock,image) VALUES(?,?,?,?,?)",
              (request.form["name"],request.form["description"],
               float(request.form["price"]),int(request.form["stock"]),
               request.form["image"]))
    c.commit()
    c.close()
    return redirect("/admin")

@app.post("/admin/delete/<int:pid>")
def admin_delete(pid):
    if not admin_required():
        return redirect(url_for('login'))
    c=db()
    c.execute("DELETE FROM products WHERE id=?",(pid,))
    c.commit()
    c.close()
    return redirect("/admin")


@app.route("/assistant", methods=["GET","POST"])
def assistant():
    answer = "नमस्ते! मैं Sushant Shopping Assistant हूँ। 😊 आप पूछ सकते हैं: सामान खोजो, कीमत बताओ, cart दिखाओ, order कहाँ है?"
    if request.method == "POST":
        msg = request.form.get("message","").strip().lower()
        c = db()

        if not msg:
            answer = "कुछ लिखकर भेजिए। 😊"

        elif any(x in msg for x in ["hello","hi","नमस्ते","हेलो"]):
            answer = "नमस्ते! Sushant Shopping में आपका स्वागत है। मैं सामान खोजने और खरीदारी में मदद कर सकता हूँ।"

        elif "cart" in msg or "कार्ट" in msg:
            cart = session.get("cart",{})
            if not cart:
                answer = "आपका Cart अभी खाली है। 🛒"
            else:
                names=[]
                total=0
                for pid,q in cart.items():
                    pr=c.execute("SELECT * FROM products WHERE id=?",(int(pid),)).fetchone()
                    if pr:
                        names.append(f"{pr['name']} × {q}")
                        total += pr["price"]*q
                answer = "आपके Cart में: " + ", ".join(names) + f". कुल ₹{total:.2f} हैं।"

        elif any(x in msg for x in ["price","कीमत","दाम","रेट","rate"]):
            rows=c.execute("SELECT name,price,stock FROM products ORDER BY id DESC").fetchall()
            if rows:
                answer="अभी उपलब्ध सामान:\\n" + "\\n".join(
                    f"• {r['name']} — ₹{r['price']:.2f} — Stock {r['stock']}" for r in rows
                )
            else:
                answer="अभी कोई Product उपलब्ध नहीं है।"

        elif any(x in msg for x in ["product","सामान","प्रोडक्ट","क्या है","दिखाओ","खोजो","search"]):
            words=[w for w in msg.replace("?"," ").split() if len(w)>2]
            rows=[]
            if words:
                like="%"+words[-1]+"%"
                rows=c.execute(
                    "SELECT name,price,stock FROM products WHERE name LIKE ? OR description LIKE ?",
                    (like,like)
                ).fetchall()
            if rows:
                answer="मुझे ये सामान मिले:\\n" + "\\n".join(
                    f"• {r['name']} — ₹{r['price']:.2f} — Stock {r['stock']}" for r in rows
                )
            else:
                rows=c.execute("SELECT name,price,stock FROM products ORDER BY id DESC").fetchall()
                answer="उपलब्ध Products:\\n" + "\\n".join(
                    f"• {r['name']} — ₹{r['price']:.2f} — Stock {r['stock']}" for r in rows
                ) if rows else "अभी कोई Product नहीं है।"

        elif any(x in msg for x in ["order","ऑर्डर","आर्डर"]):
            if not session.get("user_id"):
                answer="Order देखने या करने के लिए पहले Login करें।"
            else:
                rows=c.execute(
                    "SELECT id,total,status FROM orders WHERE user_id=? ORDER BY id DESC",
                    (session["user_id"],)
                ).fetchall()
                if rows:
                    answer="आपके Orders:\\n" + "\\n".join(
                        f"• Order #{r['id']} — ₹{r['total']:.2f} — {r['status']}" for r in rows
                    )
                else:
                    answer="अभी आपका कोई Order नहीं है।"

        elif any(x in msg for x in ["buy","खरीद","checkout","चेकआउट"]):
            answer="खरीदारी पूरी करने के लिए पहले सामान Cart में डालें, फिर Checkout करें। 🛒"

        elif any(x in msg for x in ["login","लॉगिन","account","अकाउंट"]):
            answer="Login करने के लिए ऊपर Login खोलें। नया Account बनाने के लिए Register चुनें।"

        elif any(x in msg for x in ["address","पता","एड्रेस"]):
            answer="Delivery Address आप Profile में जाकर सेव कर सकते हैं।"

        else:
            answer="मैं इन कामों में मदद कर सकता हूँ: Product खोजना, कीमत/Stock बताना, Cart देखना, Order status बताना, Login और Checkout तक पहुँचना। 😊"

        c.close()

    return page("Sushant Shopping Assistant", f"""
    <h1>🤖 Sushant Shopping Assistant</h1>
    <div class="card">
    <p style="white-space:pre-line">{answer}</p>
    </div>
    <form method="post">
    <input name="message" placeholder="जैसे: Smartphone की कीमत बताओ" required>
    <button>Assistant से पूछें</button>
    </form>
    <p>
    <a class="btn" href="/">🏠 Shopping</a>
    <a class="btn" href="/cart">🛒 Cart</a>
    <a class="btn" href="/orders">📦 Orders</a>
    </p>
    """)


app.run(host="0.0.0.0",port=5000,debug=False)
