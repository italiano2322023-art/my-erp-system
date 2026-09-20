from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'erp_super_secret_key'

def get_db_connection():
    conn = sqlite3.connect('erp_system.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username, password = request.form['username'], request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        if user:
            session['username'], session['role'] = user['username'], user['role']
            return redirect(url_for('index'))
        flash('بيانات الدخول غير صحيحة')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 1. إعدادات المستخدمين
@app.route('/users_settings', methods=['GET', 'POST'])
def users_settings():
    if session.get('role') != 'admin': return "غير مسموح إلا للأدمن"
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                     (request.form['username'], request.form['password'], request.form['role']))
        conn.commit()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('users_settings.html', users=users)

# 2. إدارة العملاء والموردين
@app.route('/entities/<entity_type>', methods=['GET', 'POST'])
def entities(entity_type):
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute('INSERT INTO entities (name, type, phone, address) VALUES (?, ?, ?, ?)',
                     (request.form['name'], entity_type, request.form['phone'], request.form['address']))
        conn.commit()
    entities_list = conn.execute('SELECT * FROM entities WHERE type = ?', (entity_type,)).fetchall()
    conn.close()
    return render_template('entities.html', entities=entities_list, entity_type=entity_type)

# 3. إدارة المخازن والتصنيفات والمنتجات
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_category':
            conn.execute('INSERT INTO categories (name) VALUES (?)', (request.form['name'],))
        elif action == 'add_warehouse':
            conn.execute('INSERT INTO warehouses (name) VALUES (?)', (request.form['name'],))
        elif action == 'add_product':
            conn.execute('''INSERT INTO products (name, sku, category_id, warehouse_id, quantity, buy_price, sell_price)
                            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (request.form['name'], request.form['sku'], request.form['category_id'],
                          request.form['warehouse_id'], request.form['quantity'], request.form['buy_price'], request.form['sell_price']))
        conn.commit()

    products = conn.execute('''SELECT p.*, c.name as category_name, w.name as warehouse_name 
                               FROM products p 
                               LEFT JOIN categories c ON p.category_id = c.id
                               LEFT JOIN warehouses w ON p.warehouse_id = w.id''').fetchall()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    warehouses = conn.execute('SELECT * FROM warehouses').fetchall()
    conn.close()
    return render_template('inventory.html', products=products, categories=categories, warehouses=warehouses)

# 4. الفواتير والعمليات (مبيعات / مشتريات / مرتجعات)
@app.route('/invoices/<inv_type>', methods=['GET', 'POST'])
def invoices(inv_type):
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    entity_target = 'customer' if 'sale' in inv_type else 'supplier'

    if request.method == 'POST':
        entity_id = request.form['entity_id']
        product_id = request.form['product_id']
        qty = int(request.form['quantity'])
        price = float(request.form['unit_price'])
        total = qty * price
        paid = float(request.form.get('paid_amount', 0))

        # 1. إنشاء الفاتورة
        cur = conn.cursor()
        cur.execute('INSERT INTO invoices (invoice_type, entity_id, total_amount, paid_amount) VALUES (?, ?, ?, ?)',
                    (inv_type, entity_id, total, paid))
        inv_id = cur.lastrowid
        cur.execute('INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)',
                    (inv_id, product_id, qty, price, total))

        # 2. تحديث حركة المخزن تلقائياً
        qty_change = -qty if inv_type in ['sale', 'purchase_return'] else qty
        cur.execute('UPDATE products SET quantity = quantity + ? WHERE id = ?', (qty_change, product_id))

        # 3. التأثير على كشف الحساب (Ledger)
        debit = total if inv_type in ['sale', 'purchase_return'] else 0
        credit = total if inv_type in ['purchase', 'sale_return'] else 0
        cur.execute('INSERT INTO ledger (entity_id, description, debit, credit) VALUES (?, ?, ?, ?)',
                    (entity_id, f"فاتورة {inv_type} رقم {inv_id}", debit, credit))
        if paid > 0:
            cur.execute('INSERT INTO ledger (entity_id, description, debit, credit) VALUES (?, ?, ?, ?)',
                        (entity_id, f"سداد عن فاتورة رقم {inv_id}", credit if debit > 0 else 0, paid if debit > 0 else paid))

        conn.commit()

    invoices_list = conn.execute('''SELECT i.*, e.name as entity_name 
                                    FROM invoices i JOIN entities e ON i.entity_id = e.id 
                                    WHERE i.invoice_type = ? ORDER BY i.id DESC''', (inv_type,)).fetchall()
    entities_list = conn.execute('SELECT * FROM entities WHERE type = ?', (entity_target,)).fetchall()
    products_list = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('invoices.html', invoices=invoices_list, entities=entities_list, products=products_list, inv_type=inv_type)

# 5. كشف الحسابات المالية (Ledger)
@app.route('/accounts')
def accounts():
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    entity_id = request.args.get('entity_id')
    ledger_entries = []
    selected_entity = None
    balance = 0

    if entity_id:
        selected_entity = conn.execute('SELECT * FROM entities WHERE id = ?', (entity_id,)).fetchone()
        entries = conn.execute('SELECT * FROM ledger WHERE entity_id = ? ORDER BY date ASC', (entity_id,)).fetchall()
        for e in entries:
            balance += (e['debit'] - e['credit'])
            entry_dict = dict(e)
            entry_dict['running_balance'] = balance
            ledger_entries.append(entry_dict)

    entities_list = conn.execute('SELECT * FROM entities').fetchall()
    conn.close()
    return render_template('accounts.html', entities=entities_list, entries=ledger_entries, selected_entity=selected_entity)

# 6. الموارد البشرية (HR)
@app.route('/hr', methods=['GET', 'POST'])
def hr():
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute('INSERT INTO employees (name, position, salary, hire_date) VALUES (?, ?, ?, ?)',
                     (request.form['name'], request.form['position'], request.form['salary'], request.form['hire_date']))
        conn.commit()
    employees = conn.execute('SELECT * FROM employees').fetchall()
    conn.close()
    return render_template('hr.html', employees=employees)

# الموديولات الأخرى العامة
@app.route('/sales')
def sales(): return redirect(url_for('invoices', inv_type='sale'))

@app.route('/purchases')
def purchases(): return redirect(url_for('invoices', inv_type='purchase'))

@app.route('/production')
def production(): return render_template('placeholder.html', title="التصنيع والإنتاج")

@app.route('/maintenance')
def maintenance(): return render_template('placeholder.html', title="إدارة الصيانة")

@app.route('/reports')
def reports(): return render_template('placeholder.html', title="التقارير والذكاء التجاري")

@app.route('/crm')
def crm(): return render_template('entities', entity_type='customer')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)