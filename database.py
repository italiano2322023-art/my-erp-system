import sqlite3

def init_db():
    conn = sqlite3.connect('erp_system.db')
    cursor = conn.cursor()

    # 1. المستخدمين والصلاحيات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            full_name TEXT
        )
    ''')

    # 2. إعدادات الخزائن
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS treasuries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            balance REAL DEFAULT 0
        )
    ''')

    # 3. إعدادات العملاء والموردين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL, -- 'customer' or 'supplier'
            phone TEXT,
            address TEXT,
            tax_number TEXT,
            balance REAL DEFAULT 0
        )
    ''')

    # 4. المخازن والتصنيفات والمنتجات
    cursor.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS warehouses (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE,
            category_id INTEGER,
            warehouse_id INTEGER,
            quantity INTEGER DEFAULT 0,
            buy_price REAL DEFAULT 0,
            sell_price REAL DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (warehouse_id) REFERENCES warehouses (id)
        )
    ''')

    # 5. الفواتير والضرائب والخصومات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT NOT NULL, -- 'sale', 'sale_return', 'purchase', 'purchase_return'
            entity_id INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            discount REAL DEFAULT 0,
            tax_rate REAL DEFAULT 0,
            tax_amount REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            paid_amount REAL DEFAULT 0,
            treasury_id INTEGER,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id),
            FOREIGN KEY (treasury_id) REFERENCES treasuries (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total REAL NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    # 6. أذون استلام وصرف النقدية (السندات)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_vouchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_type TEXT NOT NULL, -- 'receipt' (استلام), 'payment' (صرف)
            treasury_id INTEGER NOT NULL,
            entity_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            notes TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (treasury_id) REFERENCES treasuries (id),
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
    ''')

    # 7. دفتر القيود المحاسبية الشامل (Journal Entries)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT NOT NULL,
            account_name TEXT NOT NULL,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            ref_id INTEGER
        )
    ''')

    # 8. كشوف الحسابات العامة (Ledger)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            doc_type TEXT NOT NULL,
            description TEXT,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
    ''')

    # 9. تكاليف المنتجات والديناميكية (BOM - قائمة المكونات والتكاليف)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            raw_material_cost REAL DEFAULT 0,
            labor_cost REAL DEFAULT 0,
            overhead_cost REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    # بيانات افتراضية
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role, full_name) VALUES ('admin', 'admin123', 'admin', 'مدير النظام')")

    cursor.execute("SELECT * FROM treasuries")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO treasuries (name, balance) VALUES ('الخزينة الرئيسية', 0)")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("تم تحديث قاعدة البيانات الشاملة بنجاح!")