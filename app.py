from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail, Message
import sqlite3
import random
import string
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Flask-Mail Configuration (Gmail example)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'rupyargaming60@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'engd xffg syvt alhs'     # Replace with App Password
app.config['MAIL_DEFAULT_SENDER'] = 'rupyargaming60@gmail.com'
mail = Mail(app)

# Temporary OTP storage (Use database in production)
otp_storage = {}

# Database Initialization
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            balance REAL DEFAULT 0.0,
            verified INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ads_viewed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            viewed_on DATE DEFAULT CURRENT_DATE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Helper Functions
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    msg = Message('Verify Your Email', recipients=[email])
    msg.body = f'Your OTP for registration is: {otp}'
    mail.send(msg)

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Results as dictionaries
    return conn

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check existing user
        if cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email)).fetchone():
            flash('Username/Email already exists!')
            conn.close()
            return redirect(url_for('register'))

        # Generate and send OTP
        otp = generate_otp()
        otp_storage[email] = {'otp': otp, 'data': (username, password, email)}
        send_otp_email(email, otp)

        conn.close()
        flash('OTP sent to your email!')
        return redirect(url_for('verify_otp', email=email))

    return render_template('register.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    email = request.args.get('email')
    
    if request.method == 'POST':
        user_otp = request.form['otp']
        
        if email in otp_storage and otp_storage[email]['otp'] == user_otp:
            # Save user to database
            username, password, email = otp_storage[email]['data']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password, email, verified) VALUES (?, ?, ?, 1)', 
                         (username, password, email))
            conn.commit()
            conn.close()
            
            del otp_storage[email]
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP!')

    return render_template('verify_otp.html', email=email)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                          (username, password)).fetchone()
        conn.close()

        if user:
            if user['verified']:
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            else:
                flash('Email not verified!')
        else:
            flash('Invalid credentials!')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Check ads viewed today
    ads_today = conn.execute('SELECT COUNT(*) FROM ads_viewed WHERE user_id = ? AND viewed_on = DATE("now")', 
                           (session['user_id'],)).fetchone()[0]
    
    conn.close()
    return render_template('dashboard.html', user=user, ads_today=ads_today)

@app.route('/view_ads')
def view_ads():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    # Check if already viewed 2 ads today
    ads_today = conn.execute('SELECT COUNT(*) FROM ads_viewed WHERE user_id = ? AND viewed_on = DATE("now")', 
                           (session['user_id'],)).fetchone()[0]
    
    if ads_today >= 2:
        flash('You have already viewed 2 ads today!')
        conn.close()
        return redirect(url_for('dashboard'))
    
    # Track ad view
    conn.execute('INSERT INTO ads_viewed (user_id) VALUES (?)', (session['user_id'],))
    conn.commit()
    conn.close()
    
    return render_template('ads.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
