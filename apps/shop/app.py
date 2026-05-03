from flask import Flask, request, render_template_string, session, redirect, url_for, jsonify
import os

app = Flask(__name__)
app.secret_key = 'super_secret_test_key'

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Login - ScriptSim Shop</title></head>
<body style="font-family: sans-serif; padding: 2rem;">
    <h2>Login to ScriptSim Shop</h2>
    {% if error %} <p style="color:red">{{ error }}</p> {% endif %}
    <form method="POST">
        <div style="margin-bottom: 1rem;">
            <label for="email">Email</label><br>
            <input type="email" name="email" id="email" placeholder="Email" required style="padding: 0.5rem;">
        </div>
        <div style="margin-bottom: 1rem;">
            <label for="password">Password</label><br>
            <input type="password" name="password" id="password" placeholder="Password" required style="padding: 0.5rem;">
        </div>
        <button type="submit" style="padding: 0.5rem 1rem;">Login</button>
    </form>
</body>
</html>
"""

HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>ScriptSim Shop</title></head>
<body style="font-family: sans-serif; padding: 2rem;">
    <div style="display: flex; justify-content: space-between;">
        <h1>ScriptSim Shop</h1>
        <div>
            <p>Welcome, {{ session.get('email') }}</p>
            <a href="/cart" style="font-weight: bold;">View Cart ({{ cart_size }})</a>
        </div>
    </div>
    <hr>
    
    <div style="margin: 2rem 0;">
        <form action="/search" method="GET">
            <input type="text" name="q" placeholder="Search products..." aria-label="Search" style="padding: 0.5rem; width: 300px;">
            <button type="submit" style="padding: 0.5rem 1rem;">Search</button>
        </form>
    </div>
    
    <h3>Products</h3>
    <div style="display: flex; gap: 2rem;">
        <div style="border: 1px solid #ccc; padding: 1rem; border-radius: 8px;">
            <h4>Awesome Widget</h4>
            <p>$19.99</p>
            <button onclick="addToCart('Awesome Widget')" aria-label="Add to cart" style="padding: 0.5rem;">Add to Cart</button>
        </div>
        <div style="border: 1px solid #ccc; padding: 1rem; border-radius: 8px;">
            <h4>Super Gadget</h4>
            <p>$49.99</p>
            <button onclick="addToCart('Super Gadget')" aria-label="Add to cart" style="padding: 0.5rem;">Add to Cart</button>
        </div>
    </div>

    <script>
    async function addToCart(item) {
        const fd = new FormData();
        fd.append('item', item);
        let res = await fetch('/api/cart/add', {method: 'POST', body: fd});
        if (res.ok) {
            alert(item + ' added to cart!');
            window.location.reload();
        } else {
            // Wait, if it fails with 500, we just go to the 500 page? Let's just reload to see the error.
            window.location.reload();
        }
    }
    </script>
</body>
</html>
"""

SEARCH_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Search Results</title></head>
<body style="font-family: sans-serif; padding: 2rem;">
    <h1>Search Results</h1>
    <!-- BUG 1: XSS Vulnerability - query rendered with safe filter -->
    <div style="background: #f0f0f0; padding: 1rem; margin-bottom: 2rem;">
        You searched for: <strong>{{ query|safe }}</strong>
    </div>
    <p>No products found matching your search.</p>
    <a href="/">Back to Home</a>
</body>
</html>
"""

CART_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Your Cart</title></head>
<body style="font-family: sans-serif; padding: 2rem;">
    <h1>Your Cart</h1>
    {% if session.get('cart') %}
        <ul style="line-height: 1.5;">
        {% for item in session['cart'] %}
            <li>{{ item }}</li>
        {% endfor %}
        </ul>
        <p><strong>Total items:</strong> {{ session['cart']|length }}</p>
        
        <div style="margin-top: 2rem;">
            <!-- BUG 5: Frozen checkout button -->
            <button disabled aria-label="Checkout" style="padding: 1rem 2rem; background: #ccc; cursor: not-allowed; border: none; border-radius: 4px;">Checkout</button>
            <p style="font-size: 0.8rem; color: #666;">(Checkout is currently unavailable)</p>
        </div>
    {% else %}
        <p>Your cart is empty.</p>
    {% endif %}
    
    <div style="margin-top: 2rem;">
        <a href="/">Back to Home</a>
    </div>
</body>
</html>
"""

ERROR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>Server Error</title></head>
<body style="font-family: sans-serif; padding: 2rem; text-align: center; background: #fee;">
    <!-- BUG 4: Confusing error message -->
    <h1 style="color: #c00;">Oops! The chickens have come home to roost.</h1>
    <p>It seems we've dropped the ball in the soup. Please try again when the moon is full.</p>
    <a href="/">Go Home</a>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    if 'email' not in session:
        return redirect(url_for('login'))
    cart = session.get('cart', [])
    return render_template_string(HOME_TEMPLATE, cart_size=len(cart))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email == 'test@scriptsim.com' and password == 'TestPass123!':
            session['email'] = email
            session['cart'] = []
            return redirect(url_for('index'))
        else:
            error = "Invalid credentials."
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/search', methods=['GET'])
def search():
    if 'email' not in session:
        return redirect(url_for('login'))
    query = request.args.get('q', '')
    return render_template_string(SEARCH_TEMPLATE, query=query)

@app.route('/cart', methods=['GET'])
def cart():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template_string(CART_TEMPLATE)

@app.route('/api/cart/add', methods=['POST'])
def api_cart_add():
    if 'email' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    item = request.form.get('item')
    cart = session.get('cart', [])
    
    # BUG 2: Silent cart failure
    # When adding "Super Gadget", we return success but don't actually add it.
    if item == 'Awesome Widget':
        cart.append(item)
        session['cart'] = cart
        
        # BUG 3: Crash at 10+ items
        if len(cart) >= 10:
            # This will trigger a 500 which is handled by our confusing error handler
            raise ValueError("Too many items, the cart overflowed!")
            
    return jsonify({"status": "success"})

@app.errorhandler(500)
def handle_500(e):
    return render_template_string(ERROR_TEMPLATE), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
