from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from functools import wraps
import os
from werkzeug.utils import secure_filename

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

# Add these configurations after app creation
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['DEFAULT_AVATAR'] = 'user-icon.png'  # Add this line

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
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


# @app.route('/add_expense', methods=['GET', 'POST'])
# @login_required
# def add_expense():
#     if request.method == 'POST':
#         description = request.form['description']
#         amount = float(request.form['amount'])
#         category = detect_category(description)
        
#         expense = {
#             'user_id': session['user_id'],
#             'description': description,
#             'amount': amount,
#             'category': category,
#             'date': datetime.now()
#         }
#         expenses_collection.insert_one(expense)
#         flash('Expense added successfully!', 'success')
#         return redirect(url_for('dashboard'))
#     return render_template('add_expense.html',now=datetime.now())


@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        category = request.form['category']  # Get category directly from form
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        
        expense = {
            'user_id': session['user_id'],
            'description': description,
            'amount': amount,
            'category': category,  # Use the selected category
            'date': date
        }
        
        expenses_collection.insert_one(expense)
        flash('Expense added successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    # Get predefined categories for the form
    categories = [
        'food', 'transport', 'entertainment', 
        'utilities', 'shopping', 'healthcare',
        'education', 'rent', 'other'
    ]
    return render_template('add_expense.html', categories=categories,now = datetime.now())


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
    return redirect(url_for('index'))

# Inject current time into Jinja2 globally
@app.context_processor
def inject_globals():
    return {
        'user_stats': get_user_stats(),
        'now': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Fixed issue
    }



# Add these new routes to your app.py

@app.route('/delete_expense/<expense_id>')
@login_required
def delete_expense(expense_id):
    user_id = session['user_id']
    # Verify the expense belongs to the user before deleting
    expense = expenses_collection.find_one({
        '_id': ObjectId(expense_id),
        'user_id': user_id
    })
    
    if expense:
        expenses_collection.delete_one({'_id': ObjectId(expense_id)})
        flash('Expense deleted successfully!', 'success')
    else:
        flash('Expense not found or unauthorized!', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/edit_expense/<expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    user_id = session['user_id']
    expense = expenses_collection.find_one({
        '_id': ObjectId(expense_id),
        'user_id': user_id
    })
    
    if not expense:
        flash('Expense not found or unauthorized!', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        description = request.form['description']
        amount = float(request.form['amount'])
        category = request.form['category']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        
        expenses_collection.update_one(
            {'_id': ObjectId(expense_id)},
            {
                '$set': {
                    'description': description,
                    'amount': amount,
                    'category': category,
                    'date': date
                }
            }
        )
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('edit_expense.html', expense=expense)

@app.route('/profile')
@login_required
def profile():
    user_id = session['user_id']
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    
    # Calculate additional stats
    expenses = list(expenses_collection.find({'user_id': user_id}))
    total_spent = sum(expense['amount'] for expense in expenses)
    categories = {}
    for expense in expenses:
        categories[expense['category']] = categories.get(expense['category'], 0) + expense['amount']
    
    return render_template(
        'profile.html',
        user=user,
        total_spent=total_spent,
        category_distribution=categories,
        expense_count=len(expenses))

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        user_id = session['user_id']
        update_data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'address': request.form.get('address'),
            'currency': request.form.get('currency')
        }
        
        # Validate required fields
        if not update_data['name'] or not update_data['email']:
            flash('Name and Email are required fields', 'error')
            return redirect(url_for('profile'))
            
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        flash('Error updating profile', 'error')
        print(f"Profile update error: {str(e)}")
    return redirect(url_for('profile'))


@app.route('/update_password', methods=['POST'])
@login_required
def update_password():
    user_id = session['user_id']
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not check_password_hash(user['password'], old_password):
        flash('Old password is incorrect', 'error')
        return redirect(url_for('profile'))
    
    hashed_password = generate_password_hash(new_password)
    users_collection.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'password': hashed_password}}
    )
    flash('Password updated successfully!', 'success')
    return redirect(url_for('profile'))

@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    try:
        user_id = session['user_id']
        
        if 'avatar' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('profile'))

        file = request.files['avatar']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('profile'))

        if file and allowed_file(file.filename):
            # Create uploads directory if not exists
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            # Delete old avatar if it's not default
            user = users_collection.find_one({'_id': ObjectId(user_id)})
            if user.get('avatar') and user['avatar'] != app.config['DEFAULT_AVATAR']:
                old_file = os.path.join(app.config['UPLOAD_FOLDER'], user['avatar'])
                if os.path.exists(old_file):
                    os.remove(old_file)

            # Generate unique filename
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"avatar_{user_id}_{int(time.time())}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            
            # Update database
            users_collection.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'avatar': filename}}
            )
            flash('Profile picture updated successfully!', 'success')
        else:
            flash('Allowed file types: PNG, JPG, JPEG, GIF', 'error')
    except Exception as e:
        flash('Error updating avatar', 'error')
        print(f"Avatar upload error: {str(e)}")
    return redirect(url_for('profile'))

if __name__ == '__main__':
    app.run(debug=True)
