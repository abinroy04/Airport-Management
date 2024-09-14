from flask import Flask, render_template, request, redirect, url_for, jsonify, g, session, flash
import pymysql
from flask_session import Session
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secret key for session management

def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host="localhost",
            user="root",
            password="12345",
            database="airport_management",
            cursorclass=pymysql.cursors.DictCursor
        )
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.before_request
def before_request():
    g.db = get_db()

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = g.db.cursor()
        
        cursor.execute("SELECT * FROM admin_users WHERE username = %s AND password = %s", (username, password))
        admin = cursor.fetchone()
        
        if admin:
            session.clear()  # Clear any existing session data
            session['logged_in'] = True
            session['admin_id'] = admin['id']
            return redirect(url_for('admin_mode'))
        else:
            flash('Invalid credentials. Please try again.','error')
            return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/user_mode', methods=['GET', 'POST'])
def user_mode():
    if request.method == 'POST':
        passenger_id = request.form['passenger_id']
        cursor = g.db.cursor()
        cursor.execute("SELECT * FROM baggage WHERE passenger_id = %s", (passenger_id,))
        baggages = cursor.fetchall()
        return render_template('user_mode.html', baggages=baggages, passenger_id=passenger_id)
    return render_template('user_mode.html', baggages=None, passenger_id=None)

@app.route('/admin_mode', methods=['GET', 'POST'])
def admin_mode():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        action = request.form['action']
        cursor = g.db.cursor()
        if action == 'issue_baggage':
            passenger_id = request.form['passenger_id']
            baggage_weights = request.form.getlist('baggage_weight[]')
            gate = request.form['gate']
            destination = request.form['destination']
            
            for weight in baggage_weights:
                cursor.execute(
                    "INSERT INTO baggage (passenger_id, weight, gate, destination, status) VALUES (%s, %s, %s, %s, 'Check-in')", 
                    (passenger_id, weight, gate, destination)
                )
            g.db.commit()
        elif action == 'update_status':
            passenger_id = request.form['passenger_id']
            baggage_id = request.form['baggage_id']
            new_status = request.form['new_status']
            new_weight = request.form['new_weight']
            
            cursor.execute("UPDATE baggage SET status = %s, weight = %s WHERE id = %s AND passenger_id = %s", 
                           (new_status, new_weight, baggage_id, passenger_id))
            g.db.commit()
    
    return render_template('admin_mode.html')

@app.route('/get_passenger_baggage', methods=['GET'])
def get_passenger_baggage():
    passenger_id = request.args.get('passenger_id')
    cursor = g.db.cursor()
    cursor.execute("SELECT id, weight, status FROM baggage WHERE passenger_id = %s", (passenger_id,))
    baggages = cursor.fetchall()
    return jsonify(baggages)

@app.route('/delete_passenger', methods=['POST'])
def delete_passenger():
    if request.method == 'POST':
        passenger_id = request.form['passenger_id']
        cursor = g.db.cursor()
        cursor.execute("DELETE FROM baggage WHERE passenger_id = %s", (passenger_id,))
        g.db.commit()
        return redirect(url_for('admin_mode'))
    
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear all session data
    return redirect(url_for('index'))

# Configure server-side session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, 'flask_session')
Session(app)

def clear_all_sessions():
    session_dir = app.config['SESSION_FILE_DIR']
    for filename in os.listdir(session_dir):
        file_path = os.path.join(session_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")


if __name__ == '__main__':
    with app.app_context():
        clear_all_sessions()  # Clear all sessions when the app starts
    app.run(debug=False)