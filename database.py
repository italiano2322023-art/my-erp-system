import sqlite3
from werkzeug.security import generate_password_hash

class Database:
    def __init__(self, db_name="erp_system.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        self.create_tables()
        self.seed_default_data()

    def create_tables(self):
        # 1. جدول الأدوار/الصلاحيات
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                role_id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_name TEXT UNIQUE NOT NULL,
                description TEXT
            )
        ''')

        # 2. جدول المستخدمين (مع التشفير)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (role_id) REFERENCES roles(role_id)
            )
        ''')

        # 3. دليل الحسابات
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                account_code INTEGER PRIMARY KEY,
                account_name TEXT NOT NULL,
                account_type TEXT NOT NULL CHECK(account_type IN ('أصول', 'التزامات', 'حقوق ملكية', 'إيرادات', 'مصروفات')),
                parent_code INTEGER,
                FOREIGN KEY (parent_code) REFERENCES accounts(account_code)
            )
        ''')

        # 4. دليل العملاء
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                credit_limit REAL DEFAULT 0.0,
                account_code INTEGER,
                FOREIGN KEY (account_code) REFERENCES accounts(account_code)
            )
        ''')

        # 5. دليل الموردين
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                account_code INTEGER,
                FOREIGN KEY (account_code) REFERENCES accounts(account_code)
            )
        ''')

        # 6. دليل الأصناف والمخزون
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT UNIQUE,
                name TEXT NOT NULL,
                unit TEXT DEFAULT 'قطعة',
                cost_price REAL DEFAULT 0.0,
                selling_price REAL DEFAULT 0.0,
                quantity_on_hand REAL DEFAULT 0.0,
                min_stock_level REAL DEFAULT 0.0
            )
        ''')

        # 7. الخزائن والبنوك
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS treasuries (
                treasury_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                account_code INTEGER,
                balance REAL DEFAULT 0.0,
                FOREIGN KEY (account_code) REFERENCES accounts(account_code)
            )
        ''')

        # 8. الفواتير (مبيعات / مشتريات / مردودات)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_type TEXT NOT NULL CHECK(invoice_type IN ('مبيعات', 'مشتريات', 'مردودات مبيعات', 'مردودات مشتريات')),
                date TEXT NOT NULL,
                entity_type TEXT CHECK(entity_type IN ('عميل', 'مورد')),
                entity_id INTEGER,
                user_id INTEGER,
                total_amount REAL DEFAULT 0.0,
                discount REAL DEFAULT 0.0,
                net_amount REAL DEFAULT 0.0,
                paid_amount REAL DEFAULT 0.0,
                remaining_amount REAL DEFAULT 0.0,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        # 9. تفاصيل الفواتير
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            )
        ''')

        # 10. حركة وأذون المخزن
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_transactions (
                trans_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trans_type TEXT NOT NULL CHECK(trans_type IN ('إذن إضافة', 'إذن صرف', 'تسوية مخزنية')),
                date TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                unit_cost REAL DEFAULT 0.0,
                user_id INTEGER,
                reference_id INTEGER,
                notes TEXT,
                FOREIGN KEY (product_id) REFERENCES products(product_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        # 11. أذون النقدية (صرف / استلام)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS cash_transactions (
                voucher_id INTEGER PRIMARY KEY AUTOINCREMENT,
                voucher_type TEXT NOT NULL CHECK(voucher_type IN ('إذن استلام نقدية', 'إذن صرف نقدية')),
                date TEXT NOT NULL,
                treasury_id INTEGER NOT NULL,
                account_code INTEGER NOT NULL,
                amount REAL NOT NULL,
                user_id INTEGER,
                description TEXT,
                FOREIGN KEY (treasury_id) REFERENCES treasuries(treasury_id),
                FOREIGN KEY (account_code) REFERENCES accounts(account_code),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        # 12. قيود اليومية
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date TEXT NOT NULL,
                description TEXT,
                source_type TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_lines (
                line_id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                account_code INTEGER NOT NULL,
                debit REAL DEFAULT 0.0,
                credit REAL DEFAULT 0.0,
                FOREIGN KEY (entry_id) REFERENCES journal_entries(entry_id),
                FOREIGN KEY (account_code) REFERENCES accounts(account_code)
            )
        ''')

        self.conn.commit()

    def seed_default_data(self):
        """إدخال الأدوار الافتراضية والمستخدم الأدمن عند التشغيل لأول مرة"""
        # أدوار النظام
        roles = [('أدمن', 'مدير النظام بصلحيات كاملة'), ('محاسب', 'إدخال الفواتير والسندات والقيود'), ('مسؤول مخزن', 'إدارة المخزون والأذون')]
        for role in roles:
            self.cursor.execute("INSERT OR IGNORE INTO roles (role_name, description) VALUES (?, ?)", role)

        # إنشاء مستخدم Admin افتراضي (اسم المستخدم: admin / كلمة السر: admin123)
        self.cursor.execute("SELECT user_id FROM users WHERE username = 'admin'")
        if not self.cursor.fetchone():
            hashed_pwd = generate_password_hash('admin123')
            self.cursor.execute(
                "INSERT INTO users (username, password_hash, full_name, role_id) VALUES (?, ?, ?, ?)",
                ('admin', hashed_pwd, 'مدير النظام', 1)
            )
        self.conn.commit()

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    db = Database()
    print("تم إعداد قاعدة البيانات الشاملة مع نظام المستخدمين والأدوار بنجاح!")
    db.close()

