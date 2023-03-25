from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, make_response
from flask_login import LoginManager
from flask_login import UserMixin
from flask_login import login_required
import psycopg2
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import random

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = 'mysecretkey'
app.config['SECRET_KEY'] = 'Sup3rS3cr3tk3y'

# Create a connection to the PostgreSQL database
db_connection_info = psycopg2.connect(
    host='127.0.0.1',
    user='postgres',
    password='201048',
    database='postgres'
)

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    cursor = db_connection_info.cursor()
    query = "SELECT * FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()
    
    if user:
        user_obj = UserMixin()
        user_obj.id = user[0]
        return user_obj
    else:
        return None

# Home page
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Retrieve the user data from the request body
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Generate a credit card number for the user
        cc_number = str(random.randint(1000000000000000, 9999999999999999))

        # Insert the user data into the database
        cursor = db_connection_info.cursor()
        query = "INSERT INTO users (name, email, password, cc_number) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (name, email, password, cc_number))
        db_connection_info.commit()
        cursor.close()

        # Return a success message to the client
        return jsonify({'message': 'User registered successfully'})
    else:
        return render_template('register.html')
    
# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = db_connection_info.cursor()
        query = "SELECT * FROM users WHERE email = %s AND password = %s"
        cursor.execute(query, (email, password))
        user = cursor.fetchone()
        cursor.close()

        if user:
            # Set the session cookie to be the user's ID
            session['user_id'] = user[0]

            # Redirect to the user's account page
            return redirect(url_for('profile', user_id=user[0]))
        else:
            # Display an error message
            flash('Invalid email or password')
            return redirect(url_for('login'))
    else:
        # Display the login form
        return render_template('login.html')
    
# Logout page
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
    
# Profile page
@app.route('/profile/<int:user_id>')
def profile(user_id):
    if 'user_id' not in session:
        # Redirect to the login page if the user is not logged in
        flash('Please log in to access this page')
        return redirect(url_for('login'))

    # Check if the user is authorized to access this page
    if session['user_id'] != user_id:
        # Redirect to the login page if the user is not authorized
        flash('You are not authorized to access this page')
        return redirect(url_for('login'))

    # Fetch the user data from the database
    cursor = db_connection_info.cursor()
    query = "SELECT * FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    user = cursor.fetchone()
    cursor.close()

    if user:
        # Retrieve the user's credit card number from the database
        cursor = db_connection_info.cursor()
        query = "SELECT cc_number FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        cc_number = cursor.fetchone()[0]
        cursor.close()

        # Render the profile page with the user's data and credit card number
        return render_template('profile.html', user=user, cc_number=cc_number)
    else:
        # Redirect to the login page
        flash('Please log in to access this page')
        return redirect(url_for('login'))

# About Us page
@app.route('/about')
def about():
    return render_template('about.html')

# Contact Us page
@app.route('/contact')
def contact():
    return render_template('contact.html')

# Transaction page
@app.route('/transactions')
def transactions():
    if 'user_id' not in session:  
        return redirect(url_for('login'))
    return render_template('transactions.html', user_id=session['user_id'])  

@app.route('/user_transactions')
def user_transactions():
    if 'user_id' not in session:
        flash('Please log in to access this page')
        return redirect(url_for('login'))
    user_id = session['user_id']
    
    # Fetch user transactions from the database
    cursor = db_connection_info.cursor()
    query = "SELECT * FROM transactions WHERE sender_id = %s OR recipient_id = %s ORDER BY date DESC"
    cursor.execute(query, (user_id, user_id))
    transactions = cursor.fetchall()
    cursor.close()
    
    return render_template('user_transactions.html', transactions=transactions)


@app.route('/api/transfer', methods=['POST'])
def transfer():
    data = request.get_json()
    sender_id = data.get('sender_id')
    recipient_id = data.get('recipient_id')
    amount = data.get('amount')

    if not all([sender_id, recipient_id, amount]):
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    cursor = db_connection_info.cursor()

    cursor.execute("SELECT balance FROM users WHERE id = %s", (sender_id,))
    sender_balance = cursor.fetchone()[0]

    if sender_balance < amount:
        return jsonify({'status': 'error', 'message': 'Insufficient balance'}), 400

    cursor.execute("SELECT balance FROM users WHERE id = %s", (recipient_id,))
    recipient_balance = cursor.fetchone()[0]

    new_sender_balance = sender_balance - amount
    new_recipient_balance = recipient_balance + amount

    cursor.execute("UPDATE users SET balance = %s WHERE id = %s", (new_sender_balance, sender_id))
    cursor.execute("UPDATE users SET balance = %s WHERE id = %s", (new_recipient_balance, recipient_id))

    query = "INSERT INTO transactions (sender_id, recipient_id, amount) VALUES (%s, %s, %s)"
    cursor.execute(query, (sender_id, recipient_id, amount))

    db_connection_info.commit()
    cursor.close()

    return jsonify({'status': 'success', 'message': 'Transfer successful'})


if __name__ == '__main__':
    app.run(debug=True)
