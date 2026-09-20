from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'erp_super_secret_key'

def get_db_connection():
    conn = sqlite3.connect('erp_system.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()

        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            return "اسم المستخدم أو كلمة المرور غير صحيحة"
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# مسار شاشة إعدادات المستخدمين (للأدمن فقط)
@app.route('/users_settings', methods=['GET', 'POST'])
def users_settings():
    if 'role' not in session or session['role'] != 'admin':
        return "غير مسموح لك بالدخول لهذه الصفحة، هذه الصفحة مخصصة للأدمن فقط."
    
    conn = get_db_connection()
    if request.method == 'POST':
        new_user = request.form['username']
        new_pass = request.form['password']
        role = request.form['role']
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (new_user, new_pass, role))
        conn.commit()

    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('users_settings.html', users=users)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)