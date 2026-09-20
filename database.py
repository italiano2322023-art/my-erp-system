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

    # 2. العملاء والموردين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL, -- 'customer' or 'supplier'
            phone TEXT,
            address TEXT,
            balance REAL DEFAULT 0
        )
    ''')

    # 3. المخازن والتصنيفات والمنتجات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS warehouses (
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
            warehouse_id INTEGER,
            quantity INTEGER DEFAULT 0,
            buy_price REAL DEFAULT 0,
            sell_price REAL DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (warehouse_id) REFERENCES warehouses (id)
        )
    ''')

    # 4. الفواتير (بيع / شراء / مرتجع بيع / مرتجع شراء)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            paid_amount REAL DEFAULT 0,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
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

    # 5. دفتر الحسابات المالية (Ledger / كشف حساب)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            description TEXT,
            debit REAL DEFAULT 0,
            credit REAL DEFAULT 0,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (entity_id) REFERENCES entities (id)
        )
    ''')

    # 6. الموارد البشرية (HR)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            salary REAL DEFAULT 0,
            hire_date DATE
        )
    ''')

    # إضافة مدير افتراضي (Admin)
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role, full_name) VALUES ('admin', 'admin123', 'admin', 'مدير النظام')")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database built successfully!")