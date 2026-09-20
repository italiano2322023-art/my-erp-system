import sqlite3

def init_db():
    conn = sqlite3.connect('erp_system.db')
    cursor = conn.cursor()

    # 1. إدارة المستخدمين والصلاحيات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user', -- 'admin' or 'user'
            full_name TEXT
        )
    ''')

    # 2. المبيعات وخدمة العملاء (CRM)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            balance REAL DEFAULT 0
        )
    ''')

    # 3. المشتريات والموردين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            balance REAL DEFAULT 0
        )
    ''')

    # 4. المخازن والتصنيفات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE,
            category_id INTEGER,
            quantity INTEGER DEFAULT 0,
            buy_price REAL DEFAULT 0,
            sell_price REAL DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')

    # 5. الفواتير (مبيعات، مشتريات، مرتجعات)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_type TEXT NOT NULL, -- 'sale', 'purchase', 'sale_return', 'purchase_return'
            entity_type TEXT NOT NULL,  -- 'customer' or 'supplier'
            entity_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            paid_amount REAL DEFAULT 0,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # 6. المالية وكشف الحسابات (Ledger)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL, -- 'customer' or 'supplier'
            entity_id INTEGER NOT NULL,
            description TEXT,
            debit REAL DEFAULT 0,  -- مدين
            credit REAL DEFAULT 0, -- دائن
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 7. الموارد البشرية (HR)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            salary REAL DEFAULT 0,
            hire_date DATE
        )
    ''')

    # إضافة مدير افتراضي (Admin) إذا لم يكن موجوداً
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role, full_name) VALUES ('admin', 'admin123', 'admin', 'مدير النظام')")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("تم إنشاء كافة جداول موديولات ERP بنجاح!")