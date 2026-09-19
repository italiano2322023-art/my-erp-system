import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import Database

app = Flask(__name__)
app.secret_key = "super_secret_erp_key"

def get_db():
    return Database()

def is_logged_in():
    return 'user_id' in session

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        db = get_db()
        db.cursor.execute("""
            SELECT u.user_id, u.username, u.password_hash, u.full_name, r.role_name 
            FROM users u 
            JOIN roles r ON u.role_id = r.role_id 
            WHERE u.username = ? AND u.is_active = 1
        """, (username,))
        user = db.cursor.fetchone()
        db.close()

        from werkzeug.security import check_password_hash
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['full_name'] = user[3]
            session['role_name'] = user[4]
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة!', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج بنجاح.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))

    db = get_db()
    db.cursor.execute("SELECT COUNT(*) FROM products")
    total_products = db.cursor.fetchone()[0]

    db.cursor.execute("SELECT COUNT(*) FROM customers")
    total_customers = db.cursor.fetchone()[0]

    db.cursor.execute("SELECT COUNT(*) FROM suppliers")
    total_suppliers = db.cursor.fetchone()[0]

    db.cursor.execute("SELECT COALESCE(SUM(balance), 0) FROM treasuries")
    total_cash = db.cursor.fetchone()[0]
    db.close()

    stats = {
        'total_products': total_products,
        'total_customers': total_customers,
        'total_suppliers': total_suppliers,
        'total_cash': total_cash
    }

    return render_template('dashboard.html', stats=stats)

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        credit_limit = float(request.form.get('credit_limit') or 0.0)

        db.cursor.execute(
            "INSERT INTO customers (name, phone, address, credit_limit) VALUES (?, ?, ?, ?)",
            (name, phone, address, credit_limit)
        )
        db.conn.commit()
        flash('تمت إضافة العميل بنجاح', 'success')

    db.cursor.execute("SELECT * FROM customers ORDER BY customer_id DESC")
    cust_list = db.cursor.fetchall()
    db.close()
    return render_template('customers.html', customers=cust_list)

@app.route('/suppliers', methods=['GET', 'POST'])
def suppliers():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')

        db.cursor.execute(
            "INSERT INTO suppliers (name, phone, address) VALUES (?, ?, ?)",
            (name, phone, address)
        )
        db.conn.commit()
        flash('تمت إضافة المورد بنجاح', 'success')

    db.cursor.execute("SELECT * FROM suppliers ORDER BY supplier_id DESC")
    supp_list = db.cursor.fetchall()
    db.close()
    return render_template('suppliers.html', suppliers=supp_list)

@app.route('/products', methods=['GET', 'POST'])
def products():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    db = get_db()
    if request.method == 'POST':
        barcode = request.form.get('barcode')
        name = request.form.get('name')
        unit = request.form.get('unit', 'قطعة')
        cost_price = float(request.form.get('cost_price') or 0.0)
        selling_price = float(request.form.get('selling_price') or 0.0)
        initial_qty = float(request.form.get('quantity_on_hand') or 0.0)
        min_stock = float(request.form.get('min_stock_level') or 0.0)

        try:
            db.cursor.execute('''
                INSERT INTO products (barcode, name, unit, cost_price, selling_price, quantity_on_hand, min_stock_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (barcode, name, unit, cost_price, selling_price, initial_qty, min_stock))
            db.conn.commit()
            flash('تم إضافة الصنف بنجاح', 'success')
        except Exception as e:
            flash(f'خطأ: كود الباركود مستخدم أو البيانات غير صحيحة', 'danger')

    db.cursor.execute("SELECT * FROM products ORDER BY product_id DESC")
    prod_list = db.cursor.fetchall()
    db.close()
    return render_template('products.html', products=prod_list)

if __name__ == '__main__':
    app.run(debug=True, port=5000)