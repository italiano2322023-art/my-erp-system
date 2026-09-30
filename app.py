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

# --------------------------------------------------
# 1. إعدادات وتكريت الخزائن وأذون استلام وصرف النقدية
# --------------------------------------------------
@app.route('/treasuries', methods=['GET', 'POST'])
def treasuries():
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name']
        balance = float(request.form.get('balance', 0))
        conn.execute('INSERT INTO treasuries (name, balance) VALUES (?, ?)', (name, balance))
        conn.commit()
    treasuries_list = conn.execute('SELECT * FROM treasuries').fetchall()
    conn.close()
    return render_template('treasuries.html', treasuries=treasuries_list)

@app.route('/vouchers/<v_type>', methods=['GET', 'POST'])
def vouchers(v_type):
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        treasury_id = request.form['treasury_id']
        entity_id = request.form['entity_id']
        amount = float(request.form['amount'])
        notes = request.form['notes']

        # حفظ الإذن
        conn.execute('INSERT INTO cash_vouchers (voucher_type, treasury_id, entity_id, amount, notes) VALUES (?, ?, ?, ?, ?)',
                     (v_type, treasury_id, entity_id, amount, notes))
        
        # تحديث رصيد الخزينة
        t_change = amount if v_type == 'receipt' else -amount
        conn.execute('UPDATE treasuries SET balance = balance + ? WHERE id = ?', (t_change, treasury_id))

        # التحديث المالي للعميل/المورد
        debit = amount if v_type == 'payment' else 0
        credit = amount if v_type == 'receipt' else 0
        v_title = "إذن استلام نقدية" if v_type == 'receipt' else "إذن صرف نقدية"
        conn.execute('INSERT INTO ledger (entity_id, doc_type, description, debit, credit) VALUES (?, ?, ?, ?, ?)',
                     (entity_id, v_type, f"{v_title}: {notes}", debit, credit))

        # إضافة قيد محاسبي
        acc_entity = "عملاء" if v_type == 'receipt' else "موردين"
        conn.execute('INSERT INTO journal_entries (description, account_name, debit, credit) VALUES (?, ?, ?, ?)',
                     (f"{v_title} - {notes}", "الخزينة", amount if v_type == 'receipt' else 0, amount if v_type == 'payment' else 0))
        conn.execute('INSERT INTO journal_entries (description, account_name, debit, credit) VALUES (?, ?, ?, ?)',
                     (f"{v_title} - {notes}", acc_entity, amount if v_type == 'payment' else 0, amount if v_type == 'receipt' else 0))

        conn.commit()

    vouchers_list = conn.execute('''SELECT v.*, t.name as treasury_name, e.name as entity_name 
                                    FROM cash_vouchers v 
                                    JOIN treasuries t ON v.treasury_id = t.id 
                                    JOIN entities e ON v.entity_id = e.id 
                                    WHERE v.voucher_type = ? ORDER BY v.id DESC''', (v_type,)).fetchall()
    treasuries_list = conn.execute('SELECT * FROM treasuries').fetchall()
    entities_list = conn.execute('SELECT * FROM entities').fetchall()
    conn.close()
    return render_template('vouchers.html', v_type=v_type, vouchers=vouchers_list, treasuries=treasuries_list, entities=entities_list)

# --------------------------------------------------
# 2. إعدادات العملاء والموردين وتكريتهم
# --------------------------------------------------
@app.route('/entities/<entity_type>', methods=['GET', 'POST'])
def entities(entity_type):
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute('INSERT INTO entities (name, type, phone, address, tax_number) VALUES (?, ?, ?, ?, ?)',
                     (request.form['name'], entity_type, request.form['phone'], request.form['address'], request.form['tax_number']))
        conn.commit()
    entities_list = conn.execute('SELECT * FROM entities WHERE type = ?', (entity_type,)).fetchall()
    conn.close()
    return render_template('entities.html', entities=entities_list, entity_type=entity_type)

# --------------------------------------------------
# 3. إعدادات المخازن والأصناف والتكاليف
# --------------------------------------------------
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

# قسم التكاليف الديناميكي
@app.route('/costs', methods=['GET', 'POST'])
def costs():
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    if request.method == 'POST':
        product_id = request.form['product_id']
        raw_cost = float(request.form.get('raw_material_cost', 0))
        labor_cost = float(request.form.get('labor_cost', 0))
        overhead = float(request.form.get('overhead_cost', 0))
        total = raw_cost + labor_cost + overhead

        conn.execute('DELETE FROM product_costs WHERE product_id = ?', (product_id,))
        conn.execute('INSERT INTO product_costs (product_id, raw_material_cost, labor_cost, overhead_cost, total_cost) VALUES (?, ?, ?, ?, ?)',
                     (product_id, raw_cost, labor_cost, overhead, total))
        # تحديث سعر الشراء/التكلفة للمنتج النهائى
        conn.execute('UPDATE products SET buy_price = ? WHERE id = ?', (total, product_id))
        conn.commit()

    costs_list = conn.execute('''SELECT pc.*, p.name as product_name, p.sell_price 
                                 FROM product_costs pc JOIN products p ON pc.product_id = p.id''').fetchall()
    products_list = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('costs.html', costs=costs_list, products=products_list)

# --------------------------------------------------
# 4. الفواتير والخصومات والضرائب والطباعة
# --------------------------------------------------
DOC_CONFIG = {
    'sales': {'type': 'sale', 'title': 'فواتير المبيعات', 'entity': 'customer'},
    'sales_returns': {'type': 'sale_return', 'title': 'مرتجعات المبيعات', 'entity': 'customer'},
    'purchases': {'type': 'purchase', 'title': 'فواتير المشتريات', 'entity': 'supplier'},
    'purchases_returns': {'type': 'purchase_return', 'title': 'مرتجعات المشتريات', 'entity': 'supplier'}
}

@app.route('/docs/<doc_key>', methods=['GET', 'POST'])
def manage_docs(doc_key):
    if 'username' not in session: return redirect(url_for('login'))
    cfg = DOC_CONFIG[doc_key]
    conn = get_db_connection()

    if request.method == 'POST':
        entity_id = request.form['entity_id']
        product_id = request.form['product_id']
        treasury_id = request.form['treasury_id']
        qty = int(request.form['quantity'])
        price = float(request.form['unit_price'])
        discount = float(request.form.get('discount', 0))
        tax_rate = float(request.form.get('tax_rate', 0))
        paid = float(request.form.get('paid_amount', 0))

        subtotal = qty * price
        after_discount = subtotal - discount
        tax_amount = after_discount * (tax_rate / 100.0)
        total_amount = after_discount + tax_amount

        cur = conn.cursor()
        cur.execute('''INSERT INTO invoices (doc_type, entity_id, subtotal, discount, tax_rate, tax_amount, total_amount, paid_amount, treasury_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (cfg['type'], entity_id, subtotal, discount, tax_rate, tax_amount, total_amount, paid, treasury_id))
        inv_id = cur.lastrowid
        cur.execute('INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)',
                    (inv_id, product_id, qty, price, subtotal))

        # تحديث المخزن
        stock_change = -qty if cfg['type'] in ['sale', 'purchase_return'] else qty
        cur.execute('UPDATE products SET quantity = quantity + ? WHERE id = ?', (stock_change, product_id))

        # تحديث الخزينة بالمبلغ المدفوع
        if paid > 0:
            t_change = paid if cfg['type'] in ['sale', 'purchase_return'] else -paid
            cur.execute('UPDATE treasuries SET balance = balance + ? WHERE id = ?', (t_change, treasury_id))

        # التحديث المالي للعميل/المورد
        debit = total_amount if cfg['type'] in ['sale', 'purchase_return'] else 0
        credit = total_amount if cfg['type'] in ['purchase', 'sale_return'] else 0
        cur.execute('INSERT INTO ledger (entity_id, doc_type, description, debit, credit) VALUES (?, ?, ?, ?, ?)',
                    (entity_id, cfg['type'], f"فاتورة {cfg['title']} رقم #{inv_id}", debit, credit))

        if paid > 0:
            p_debit = paid if cfg['type'] in ['purchase', 'sale_return'] else 0
            p_credit = paid if cfg['type'] in ['sale', 'purchase_return'] else 0
            cur.execute('INSERT INTO ledger (entity_id, doc_type, description, debit, credit) VALUES (?, ?, ?, ?, ?)',
                        (entity_id, 'payment', f"سداد عن فاتورة #{inv_id}", p_debit, p_credit))

        conn.commit()

    docs_list = conn.execute('''SELECT i.*, e.name as entity_name 
                                FROM invoices i JOIN entities e ON i.entity_id = e.id 
                                WHERE i.doc_type = ? ORDER BY i.id DESC''', (cfg['type'],)).fetchall()
    entities_list = conn.execute('SELECT * FROM entities WHERE type = ?', (cfg['entity'],)).fetchall()
    products_list = conn.execute('SELECT * FROM products').fetchall()
    treasuries_list = conn.execute('SELECT * FROM treasuries').fetchall()
    conn.close()
    return render_template('doc_template.html', cfg=cfg, docs=docs_list, entities=entities_list, products=products_list, treasuries=treasuries_list, doc_key=doc_key)

# طباعة الفاتورة
@app.route('/print_invoice/<int:inv_id>')
def print_invoice(inv_id):
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    invoice = conn.execute('''SELECT i.*, e.name as entity_name, e.phone, e.address, e.tax_number 
                              FROM invoices i JOIN entities e ON i.entity_id = e.id WHERE i.id = ?''', (inv_id,)).fetchone()
    items = conn.execute('''SELECT ii.*, p.name as product_name 
                            FROM invoice_items ii JOIN products p ON ii.product_id = p.id WHERE ii.invoice_id = ?''', (inv_id,)).fetchall()
    conn.close()
    return render_template('print_invoice.html', invoice=invoice, items=items)

# --------------------------------------------------
# 5. كشوف الحسابات العامة (عملاء / موردين)
# --------------------------------------------------
@app.route('/statement/<entity_type>')
def statement(entity_type):
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    entity_id = request.args.get('entity_id')
    ledger_entries, selected_entity, balance = [], None, 0

    if entity_id:
        selected_entity = conn.execute('SELECT * FROM entities WHERE id = ?', (entity_id,)).fetchone()
        entries = conn.execute('SELECT * FROM ledger WHERE entity_id = ? ORDER BY id ASC', (entity_id,)).fetchall()
        for e in entries:
            balance += (e['debit'] - e['credit'])
            entry_dict = dict(e)
            entry_dict['running_balance'] = balance
            ledger_entries.append(entry_dict)

    entities_list = conn.execute('SELECT * FROM entities WHERE type = ?', (entity_type,)).fetchall()
    conn.close()
    return render_template('statement.html', entities=entities_list, entries=ledger_entries, selected_entity=selected_entity, entity_type=entity_type)

# --------------------------------------------------
# 6. القيود المحاسبية القوائم المالية والتقارير
# --------------------------------------------------
@app.route('/journal')
def journal():
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    entries = conn.execute('SELECT * FROM journal_entries ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('journal.html', entries=entries)

@app.route('/financial_statements')
def financial_statements():
    if 'username' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    
    # حساب الإيرادات والمصروفات والأصول والخصوم
    sales = conn.execute("SELECT SUM(total_amount) as total FROM invoices WHERE doc_type='sale'").fetchone()['total'] or 0
    purchases = conn.execute("SELECT SUM(total_amount) as total FROM invoices WHERE doc_type='purchase'").fetchone()['total'] or 0
    cash_balance = conn.execute("SELECT SUM(balance) as total FROM treasuries").fetchone()['total'] or 0
    
    net_profit = sales - purchases
    conn.close()
    return render_template('financial_statements.html', sales=sales, purchases=purchases, cash_balance=cash_balance, net_profit=net_profit)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)