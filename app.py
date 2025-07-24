from flask import *
from markupsafe import escape

app = Flask(__name__)
app.secret_key = b'jd7E7nd0882nao*##\t'

users = {}
recipes = {}

def load_recipes(filename):
    recipes = {}
    try:
        with open(filename) as f:
            for line in f:
                if not line.strip() or "#" not in line:
                    continue
                name, ingredients = line.strip().split("#", 1)
                recipes[name.strip()] = [i.strip() for i in ingredients.split(",")]
    except FileNotFoundError:
        pass
    return recipes

def save_recipes(filename, recipes):
    with open(filename, "w") as f:
        for name, ingredients in recipes.items():
            f.write(f"{name} : {','.join(ingredients)}\n")

def read_user_file(filename):
    users = {}
    with open(filename) as userFile:
        for row in userFile:
            row = row.strip()
            if not row or ":" not in row:
                continue
            parts = row.split(":", 1)
            if len(parts) == 2:
                username, password = parts
                users[username.strip()] = password.strip()
    return users

def save_user_file(filename, users):
    with open(filename, "w") as userFile:
        for username, password in users.items():
            userFile.write(f"{username}:{password}\n")

def load_orders(filename):
    orders = {}
    try:
        with open(filename, "r") as f:
            for line in f:
                if ":" in line:
                    user, order = line.strip().split(":", 1)
                    orders[user.strip()] = order.strip()
    except FileNotFoundError:
        pass
    return orders

def save_orders(filename, orders):
    with open(filename, "w") as f:
        for user, order in orders.items():
            f.write(f"{user} : {order}\n")

users = read_user_file("static/data/users.txt")
recipes = load_recipes("static/data/recipes.txt")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/menu')
def show_menu():
    return render_template("menu.html", pizzas=recipes.keys(), ingredients=recipes)

@app.route('/basket')
def view_cart():
    cart = session.get('cart', {})
    return render_template("basket.html", cart=cart)

@app.route('/menu/<pizza_name>')  
def show_pizza(pizza_name):
    return render_template('pizza.html', pizza=pizza_name, ingredients=recipes.get(pizza_name, []))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] not in users:
            return render_template("login.html", session=session, message="Incorrect username!")
        elif users[request.form['username']] != request.form['password']:
            return render_template("login.html", session=session, message="Incorrect password!")
        else:
            session['username'] = request.form['username']
            return redirect(url_for('index'))
    return render_template("login.html", session=session)

@app.route('/register', methods=['GET', 'POST']) 
def register():
    if request.method == 'POST':
        if request.form['username'] in users:
            return render_template("register.html", session=session, message="Username already exists!")
        users[request.form['username']] = request.form['password']
        save_user_file("static/data/users.txt", users)
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    return render_template("register.html", session=session)

@app.route('/order', methods=['GET', 'POST'])
def add_to_cart():
    if request.method == 'POST':
        if 'username' not in session:
            return redirect(url_for('login'))

        username = session['username']
        cart = session.get('cart', {})

        for key in request.form:
            if key.startswith('quantity_'):
                quantity_str = request.form[key]
                if quantity_str.strip():
                    try:
                        quantity = int(quantity_str)
                        if quantity > 0:
                            item_name = key.replace('quantity_', '')
                            size = request.form.get(f"size_{item_name}", "medium")
                            item_key = f"{item_name}_{size}"
                            cart[item_key] = cart.get(item_key, 0) + quantity
                    except ValueError:
                        print(f"Invalid quantity for {key}: {quantity_str}")

        session['cart'] = cart.copy()

        if cart:
            all_orders = {}
            try:
                with open("static/data/order.txt", "r") as f:
                    for line in f:
                        if ":" not in line:
                            continue
                        user, orders = line.strip().split(":", 1)
                        all_orders[user.strip()] = orders.strip()
            except FileNotFoundError:
                pass

            user_order_items = [f"{qty} : {item}" for item, qty in cart.items()]
            user_order_string = ", ".join(user_order_items)

            previous_orders = all_orders.get(username, "")
            if previous_orders:
                all_orders[username] = previous_orders + " \n(latest_order) " + user_order_string
            else:
                all_orders[username] = user_order_string

            with open("static/data/order.txt", "w") as f:
                for user, order_str in all_orders.items():
                    f.write(f"{user} : {order_str}\n")

        return redirect('/basket')
    return render_template("order.html", pizzas=recipes.keys(), pizza_type=recipes.keys())

@app.route('/admin')
def show_admin_page():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('index'))    

    all_orders = load_orders("static/data/order.txt")
    return render_template("admin.html", recipes=recipes, orders=all_orders)


@app.route('/add', methods=['GET', 'POST'])
def add_pizza():
    if request.method == 'POST':
        name = request.form['name'].strip()
        ingredients = request.form['ingredients'].strip().split(',')
        recipes[name] = [i.strip() for i in ingredients]
        save_recipes("static/data/recipes.txt", recipes)
        return redirect(url_for('show_admin_page'))
    return render_template('add_pizza.html')

@app.route('/edit/<pizza_name>', methods=['GET', 'POST'])
def edit_pizza(pizza_name):
    if pizza_name not in recipes:
        return "Pizza not found", 404
    if request.method == 'POST':
        new_name = request.form['name'].strip()
        ingredients = request.form['ingredients'].strip().split(',')
        if new_name != pizza_name:
            recipes.pop(pizza_name)
        recipes[new_name] = [i.strip() for i in ingredients]
        save_recipes("static/data/recipes.txt", recipes)
        return redirect(url_for('show_admin_page'))
    return render_template('edit_pizza.html', pizza_name=pizza_name, ingredients=', '.join(recipes[pizza_name]))

@app.route('/delete/<pizza_name>', methods=['GET', 'POST'])
def delete_pizza(pizza_name):
    if pizza_name in recipes:
        recipes.pop(pizza_name)
        save_recipes("static/data/recipes.txt", recipes)
    return redirect(url_for('show_admin_page'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('cart', None)
    return redirect(url_for('index'))
