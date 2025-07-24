from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Data file paths
USERS_FILE = "static/data/users.txt"
RECIPES_FILE = "static/data/recipes.txt"
ORDERS_FILE = "static/data/orders.txt"

def load_recipes():
    recipes = {}
    try:
        with open(RECIPES_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "#" in line:
                    name, ingredients = line.split("#", 1)
                    recipes[name.strip()] = [i.strip() for i in ingredients.split(",")]
    except FileNotFoundError:
        pass
    return recipes

def save_recipes(recipes):
    with open(RECIPES_FILE, "w") as f:
        for name, ingredients in recipes.items():
            f.write(f"{name}#{','.join(ingredients)}\n")

def load_users():
    users = {}
    try:
        with open(USERS_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                username, password = line.split(":", 1)
                users[username.strip()] = password.strip()
    except FileNotFoundError:
        pass
    return users

def save_users(users):
    with open(USERS_FILE, "w") as f:
        for username, password in users.items():
            f.write(f"{username}:{password}\n")

def load_orders():
    orders = []
    try:
        with open(ORDERS_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                parts = line.split(":", 2)
                if len(parts) == 3:
                    timestamp, username, order_details = parts
                    orders.append({
                        'timestamp': timestamp,
                        'username': username.strip(),
                        'details': order_details.strip()
                    })
    except FileNotFoundError:
        pass
    return orders

def save_orders(orders):
    with open(ORDERS_FILE, "w") as f:
        for order in orders:
            f.write(f"{order['timestamp']}:{order['username']}:{order['details']}\n")

def calculate_ingredients(orders, recipes):
    ingredient_counts = {}
    for order in orders:
        items = order['details'].split(",")
        for item in items:
            if ":" in item:
                quantity, pizza_info = item.split(":", 1)
                pizza_name = pizza_info.split("_")[0].strip()
                if pizza_name in recipes:
                    for ingredient in recipes[pizza_name]:
                        ingredient_counts[ingredient] = ingredient_counts.get(ingredient, 0) + int(quantity)
    return ingredient_counts

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/menu')
def menu():
    recipes = load_recipes()
    return render_template("menu.html", recipes=recipes)

@app.route('/pizza/<pizza_name>')
def pizza_details(pizza_name):
    recipes = load_recipes()
    if pizza_name not in recipes:
        flash("Pizza not found!", "error")
        return redirect(url_for('menu'))
    return render_template("pizza.html", pizza=pizza_name, ingredients=recipes[pizza_name])

@app.route('/order', methods=['GET', 'POST'])
def order():
    if 'username' not in session:
        flash("Please login to place an order", "warning")
        return redirect(url_for('login'))
    
    recipes = load_recipes()
    
    if request.method == 'POST':
        cart = {}
        for pizza in recipes:
            quantity = request.form.get(f'quantity_{pizza}', 0)
            size = request.form.get(f'size_{pizza}', 'medium')
            try:
                quantity = int(quantity)
                if quantity > 0:
                    cart[f"{pizza}_{size}"] = quantity
            except ValueError:
                continue
        
        if cart:
            # Save order
            orders = load_orders()
            order_details = ", ".join([f"{qty}:{item}" for item, qty in cart.items()])
            orders.append({
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'username': session['username'],
                'details': order_details
            })
            save_orders(orders)
            flash("Order placed successfully!", "success")
            return redirect(url_for('order_history'))
        else:
            flash("Please select at least one pizza to order", "warning")
    
    return render_template("order.html", pizzas=recipes)

@app.route('/order/history')
def order_history():
    if 'username' not in session:
        flash("Please login to view your order history", "warning")
        return redirect(url_for('login'))
    
    orders = load_orders()
    user_orders = [o for o in orders if o['username'] == session['username']]
    return render_template("order_history.html", orders=user_orders)

@app.route('/cart')
def cart():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template("cart.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        
        if username not in users:
            flash("Invalid username or password", "error")
        elif not check_password_hash(users[username], password):
            flash("Invalid username or password", "error")
        else:
            session['username'] = username
            flash("Logged in successfully!", "success")
            return redirect(url_for('index'))
    
    return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form.get('email', '')
        
        users = load_users()
        
        if username in users:
            flash("Username already exists", "error")
        elif password != confirm_password:
            flash("Passwords do not match", "error")
        else:
            users[username] = generate_password_hash(password)
            save_users(users)
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
    
    return render_template("register.html")

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash("Logged out successfully", "success")
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if 'username' not in session or session['username'] != 'admin':
        flash("Unauthorized access", "error")
        return redirect(url_for('index'))
    
    orders = load_orders()
    recipes = load_recipes()
    ingredient_counts = calculate_ingredients(orders, recipes)
    
    return render_template("admin.html", 
                         orders=orders, 
                         recipes=recipes,
                         ingredient_counts=ingredient_counts)

@app.route('/admin/pizza/add', methods=['GET', 'POST'])
def add_pizza():
    if 'username' not in session or session['username'] != 'admin':
        flash("Unauthorized access", "error")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        ingredients = [i.strip() for i in request.form['ingredients'].split(",") if i.strip()]
        
        if not name or not ingredients:
            flash("Please provide both name and ingredients", "error")
        else:
            recipes = load_recipes()
            recipes[name] = ingredients
            save_recipes(recipes)
            
            # Handle image upload
            if 'image' in request.files:
                image = request.files['image']
                if image.filename != '':
                    filename = f"pizza_{name.lower().replace(' ', '_')}.{image.filename.split('.')[-1]}"
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            flash("Pizza added successfully!", "success")
            return redirect(url_for('admin'))
    
    return render_template("add_pizza.html")

@app.route('/admin/pizza/edit/<pizza_name>', methods=['GET', 'POST'])
def edit_pizza(pizza_name):
    if 'username' not in session or session['username'] != 'admin':
        flash("Unauthorized access", "error")
        return redirect(url_for('index'))
    
    recipes = load_recipes()
    if pizza_name not in recipes:
        flash("Pizza not found", "error")
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        new_name = request.form['name'].strip()
        ingredients = [i.strip() for i in request.form['ingredients'].split(",") if i.strip()]
        
        if not new_name or not ingredients:
            flash("Please provide both name and ingredients", "error")
        else:
            if new_name != pizza_name:
                del recipes[pizza_name]
            recipes[new_name] = ingredients
            save_recipes(recipes)
            
            # Handle image upload
            if 'image' in request.files:
                image = request.files['image']
                if image.filename != '':
                    filename = f"pizza_{new_name.lower().replace(' ', '_')}.{image.filename.split('.')[-1]}"
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            flash("Pizza updated successfully!", "success")
            return redirect(url_for('admin'))
    
    return render_template("edit_pizza.html", 
                         pizza_name=pizza_name,
                         ingredients=", ".join(recipes[pizza_name]))

@app.route('/admin/pizza/delete/<pizza_name>', methods=['POST'])
def delete_pizza(pizza_name):
    if 'username' not in session or session['username'] != 'admin':
        flash("Unauthorized access", "error")
        return redirect(url_for('index'))
    
    recipes = load_recipes()
    if pizza_name in recipes:
        del recipes[pizza_name]
        save_recipes(recipes)
        flash("Pizza deleted successfully", "success")
    
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)