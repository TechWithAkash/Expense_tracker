from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from functools import wraps
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pymongo
from bson import ObjectId
from dotenv import load_dotenv
#Loaded the environment variables
load_dotenv()

# Get the MongoDBURL from the environment   variable
MONGODB_URI = os.getenv("MONGODB_URI")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB connection with timeout parameters
try:
    client = pymongo.MongoClient(MONGODB_URI, 
                                serverSelectionTimeoutMS=5000,
                                connectTimeoutMS=5000)
    client.admin.command('ping')
    db = client["finance_tracker"]
    users_collection = db["users"]
    expenses_collection = db["expenses"]
except pymongo.errors.ServerSelectionTimeoutError:
    print("Error: Could not connect to MongoDB. Please make sure MongoDB is running.")
    exit(1)

# Jinja2 custom filter for date formatting
@app.template_filter('format_date')
def format_date(date):
    return date.strftime('%Y-%m-%d') if isinstance(date, datetime) else date

def detect_category(description):
    description = description.lower()
    categories = {
        'food': ['restaurant', 'grocery', 'food', 'pizza', 'burger', 'meal'],
        'transport': ['gas', 'fuel', 'uber', 'taxi', 'bus', 'train'],
        'entertainment': ['movie', 'game', 'concert', 'show'],
        'utilities': ['electricity', 'water', 'internet', 'phone'],
        'shopping': ['clothes', 'shoes', 'amazon', 'mall'],
    }
    
    for category, keywords in categories.items():
        if any(keyword in description for keyword in keywords):
            return category
    return 'other'

def get_user_stats():
    if 'user_id' in session:
        user_id = session['user_id']
        expenses = list(expenses_collection.find({'user_id': user_id}))
        total_spent = sum(expense['amount'] for expense in expenses)
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        return {
            'total_spent': total_spent,
            'total_expenses': len(expenses),
            'name': user.get('name', 'User')
        }
    return None

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    
    expenses = list(expenses_collection.find({'user_id': user_id}).sort('date', -1))
    
    # Ensure all dates are datetime objects (Fix for strftime error)
    for expense in expenses:
        if isinstance(expense['date'], str):
            expense['date'] = datetime.fromisoformat(expense['date'])  # Convert string to datetime
    
    total_spent = sum(expense['amount'] for expense in expenses)
    categories = {}

    for expense in expenses:
        if expense['category'] in categories:
            categories[expense['category']] += expense['amount']
        else:
            categories[expense['category']] = expense['amount']

    monthly_totals = {}
    for expense in expenses:
        month_key = expense['date'].strftime('%Y-%m')
        if month_key in monthly_totals:
            monthly_totals[month_key] += expense['amount']
        else:
            monthly_totals[month_key] = expense['amount']

    return render_template(
        'dashboard.html',
        expenses=expenses,
        total_spent=total_spent,
        categories=categories,
        monthly_totals=monthly_totals,
        user=user,
        now=datetime.now()  # Pass current datetime
    )


@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        category = detect_category(description)
        
        expense = {
            'user_id': session['user_id'],
            'description': description,
            'amount': amount,
            'category': category,
            'date': datetime.now()
        }
        expenses_collection.insert_one(expense)
        flash('Expense added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_expense.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        
        if users_collection.find_one({'email': email}):
            flash('Email already exists', 'error')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        user = {
            'email': email,
            'password': hashed_password,
            'name': name,
            'created_at': datetime.now()
        }
        users_collection.insert_one(user)
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            flash(f'Welcome back, {user.get("name", "User")}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Inject current time into Jinja2 globally
@app.context_processor
def inject_globals():
    return {
        'user_stats': get_user_stats(),
        'now': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Fixed issue
    }

if __name__ == '__main__':
    app.run(debug=True)
