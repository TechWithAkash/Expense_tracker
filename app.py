from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from functools import wraps
import os
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime,timedelta
import pymongo
from bson import ObjectId
from dotenv import load_dotenv
import sys
import os
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
import google.generativeai as genai
from dotenv import load_dotenv
import logging
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd
from io import BytesIO
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# 1. Load environment variables first
load_dotenv()


# 2. Configure Gemini with error handling
try:
    genai.configure(api_key=os.getenv("GOOGLE_GENERATIVE_AI_API_KEY"))
except Exception as e:
    print(f"Error configuring AI: {str(e)}")
    # Handle error appropriately for production
# Get the MongoDBURL from the environment   variable


# 3. Configure the database connection 
MONGODB_URI = os.getenv("MONGODB_URI")

# 4. Initialize Flask application 
app = Flask(__name__)


# 5. Set the secret key for session management
app.secret_key = os.urandom(24)

# 6. Configure Flask-Limiter
# Replace the existing Limiter configuration with this:
# limiter = Limiter(
#     get_remote_address,
#     app=app,
#     default_limits=["5 per minute", "100 per hour"],
#     storage_uri="memory://"
# )

# 6. Add these configurations after app creation
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['DEFAULT_AVATAR'] = 'user-icon.png' 

# 7. Create the allowed_file function that will be called when the application needs to check if a file is allowed
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

# 8. Jinja2 custom filter for date formatting
@app.template_filter('format_date')
def format_date(date):
    return date.strftime('%Y-%m-%d') if isinstance(date, datetime) else date

# 9. Add the detect_category function to the app.py file so that it can be used in the routes for filtering expenses and category detection
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

# 10. Add the get_user_stats function to the app.py file so that it can be used in the routes for user statistics
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

# 11. Add the login route to the app.py file
# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 12. Redirect the user to the dashboard if they are i.e user already logged in
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# 13. Redirect to dashboard route when user is logged in and logged out from dashboard route when user is logged out
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

# 14. Create a new expense with the given name and description and redirect to the dashboard route  when the user is logged in or when the user is not logged in redirect to the login route    
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

# 15. Register Route to  Creating an new New user 
# @app.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         email = request.form['email']
#         password = request.form['password']
#         name = request.form['name']
        
#         if users_collection.find_one({'email': email}):
#             flash('Email already exists', 'error')
#             return redirect(url_for('register'))
        
#         hashed_password = generate_password_hash(password)
#         user = {
#             'email': email,
#             'password': hashed_password,
#             'name': name,
#             'created_at': datetime.now()
#         }
#         users_collection.insert_one(user)
#         flash('Registration successful! Please login.', 'success')
#         return redirect(url_for('login'))
#     return render_template('register.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        
        if users_collection.find_one({'email': email}):
            flash('Email already exists', 'error')
            return redirect(url_for('register'))
        
        otp = random.randint(100000, 999999)
        send_otp(email, otp)
        session['otp'] = otp
        session['temp_user'] = {
            'email': email,
            'password': generate_password_hash(password),
            'name': name,
            'created_at': datetime.now()
        }
        flash('OTP sent to your email. Please verify.', 'info') 
        return redirect(url_for('verify_otp'))
    return render_template('register.html')

# @app.route('/verify_otp', methods=['GET', 'POST'])
# @limiter.limit("10 per minute")
# def verify_otp():
#     session["otp_attempts"] = session.get('otp_attempts', 0) + 1
#     if session["otp_attempts"] > 10:
#         flash('Too many attempts. Please try again later.', 'error')
#         return redirect(url_for('register'))
#     if request.method == 'POST':
#         if datetime.now() > session.get('otp_expiry', datetime.min):
#             flash('OTP expired. Please try again.', 'error')
#             return redirect(url_for('register'))

#         user_otp = request.form['otp']
#         if 'otp' in session and int(user_otp) == session['otp']:
#             user = session.pop('temp_user')
#             users_collection.insert_one(user)
#             flash('Registration successful! Please login.', 'success')
#             return redirect(url_for('login'))
#         else:
#             flash('Invalid OTP', 'error')
#     return render_template('verify_otp.html')
# def send_otp(email, otp):
#     sender_email = "vishwakarmaakashav17@gmail.com"
#     sender_password = "pfjk vvcd hljm xvcs"  # Use the App Password here
#     receiver_email = email

#     message = MIMEMultipart("alternative")
#     message["Subject"] = "Your OTP Code"
#     message["From"] = sender_email
#     message["To"] = receiver_email

#     text = f"Your OTP code is {otp}"
#     part = MIMEText(text, "plain")
#     message.attach(part)
#     session['otp_expiry'] = datetime.now() + timedelta(minutes=10) # OTP expires in 10 minutes

#     with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
#         server.login(sender_email, sender_password)
#         server.sendmail(sender_email, receiver_email, message.as_string())

# Modify the send_otp function
def send_otp(email, otp):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_APP_PASSWORD")
    receiver_email = email

    message = MIMEMultipart("alternative")
    message["Subject"] = "Your OTP Code"
    message["From"] = sender_email
    message["To"] = receiver_email

    text = f"Your OTP code is {otp}"
    part = MIMEText(text, "plain")
    message.attach(part)

    # Store expiry time as string
    expiry_time = (datetime.now() + timedelta(minutes=10)).replace(microsecond=0)
    session['otp_expiry'] = expiry_time.isoformat()

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, message.as_string())

# Modify the verify_otp route
@app.route('/verify_otp', methods=['GET', 'POST'])
# @limiter.limit("10 per minute")
def verify_otp():
    session["otp_attempts"] = session.get('otp_attempts', 0) + 1
    if session["otp_attempts"] > 10:
        flash('Too many attempts. Please try again later.', 'error')
        return redirect(url_for('register'))
        
    if request.method == 'POST':
        # Get current time and expiry time
        current_time = datetime.now().replace(microsecond=0)
        expiry_time = datetime.fromisoformat(session.get('otp_expiry', '2000-01-01T00:00:00'))
        
        if current_time > expiry_time:
            flash('OTP expired. Please try again.', 'error')
            return redirect(url_for('register'))

        user_otp = request.form['otp']
        if 'otp' in session and int(user_otp) == session['otp']:
            user = session.pop('temp_user')
            users_collection.insert_one(user)
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP', 'error')
            
    return render_template('verify_otp.html')

# 16. Login Route to login the user
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

# 17. Logout Route to logout the user
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# 18. Inject current time into Jinja2 globally
# Inject current time into Jinja2 globally
@app.context_processor
def inject_globals():
    return {
        'user_stats': get_user_stats(),
        'now': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Fixed issue
    }



# 19. Delete the expences of the user of the specified user_id and redirect to the dashboard route
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

# 20. Edit the expense of the user of the specified user_id and redirect to the dashboard route
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

# 21. Profile Route to get the profile of the user of the specified user_id
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

# 22. Update the profile of the user of the specified user_id and redirect to the profile route
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


# 23. Update the password of the user of the specified user_id and redirect to the profile route
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

# 24. Upload the avatar of the user of the specified user_id and redirect to the profile route
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


# 25. AI Insights Route to get the AI insights of the user of the specified user_id
@app.route('/ai-insights')
@login_required
def ai_insights():
    user_id = session['user_id']
    expenses = list(expenses_collection.find({'user_id': user_id}))
    
    # Prepare data for AI
    expense_data = "\n".join([
        f"{e['date'].strftime('%Y-%m-%d')}: ₹{e['amount']} ({e['category']}) - {e['description']}"
        for e in expenses[-20:]  # Last 20 expenses
    ])
    
    prompt = f"""Analyze this financial data and provide key insights in JSON format:
    {expense_data}
    
    Return JSON format with:
    - top_spending_category
    - weekly_trend
    - potential_savings
    - risk_alerts
    - personalized_advice
    """
    
    try:
        response = model.generate_content(prompt)
        insights = json.loads(response.text.replace('```json', '').replace('```', ''))
        return jsonify(insights)
    except Exception as e:
        return jsonify({
            "error": "AI insights currently unavailable",
            "details": str(e)
        }), 500

# Smart Expense Categorization:

# 26. Create Smart Expense Categorization from a list of Smart Expense Categorizations 
def detect_category(description):
    prompt = f"""Categorize this expense description into one of these categories: 
    food, transport, entertainment, utilities, shopping, healthcare, education, rent, other
    
    Description: {description}
    
    Respond only with the category name in lowercase."""
    
    try:
        response = model.generate_content(prompt)
        return response.text.strip().lower()
    except:
        return 'other'



@app.route('/generate_report', methods=['POST'])
@login_required



def generate_report():
    try:
        user_id = session['user_id']
        report_type = request.form.get('report_type', 'monthly')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d')
        format_type = request.form.get('format', 'pdf')
        
        # Get expenses for the date range
        expenses = list(expenses_collection.find({
            'user_id': user_id,
            'date': {
                '$gte': start_date,
                '$lte': end_date
            }
        }).sort('date', -1))

        if not expenses:
            flash('No expenses found for the selected date range', 'error')
            return redirect(url_for('dashboard'))

        # Generate report based on format
        if format_type == 'pdf':
            return generate_pdf_report(expenses, report_type, start_date, end_date)
        elif format_type == 'excel':
            return generate_excel_report(expenses, report_type, start_date, end_date)
        else:  # CSV
            return generate_csv_report(expenses, report_type, start_date, end_date)

    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('dashboard'))




def generate_pdf_report(expenses, report_type, start_date, end_date):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Add title
    title = f"Financial Report ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 20))

    # Summary section
    total_spent = sum(expense['amount'] for expense in expenses)
    summary_data = [
        ['Total Expenses', f'₹{total_spent:.2f}'],
        ['Number of Transactions', str(len(expenses))],
    ]
    
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # Expense details
    expense_data = [[
        'Date', 'Description', 'Category', 'Amount'
    ]]
    for expense in expenses:
        expense_data.append([
            expense['date'].strftime('%Y-%m-%d'),
            expense['description'],
            expense['category'],
            f'₹{expense["amount"]:.2f}'
        ])

    expense_table = Table(expense_data)
    expense_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(expense_table)

    # Generate PDF
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'financial_report_{datetime.now().strftime("%Y%m%d")}.pdf',
        mimetype='application/pdf'
    )

def generate_excel_report(expenses, report_type, start_date, end_date):
    df = pd.DataFrame(expenses)
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    df = df[['date', 'description', 'category', 'amount']]
    
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Expenses', index=False)
    
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'financial_report_{datetime.now().strftime("%Y%m%d")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

def generate_csv_report(expenses, report_type, start_date, end_date):
    df = pd.DataFrame(expenses)
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%%d')
    df = df[['date', 'description', 'category', 'amount']]
    
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'financial_report_{datetime.now().strftime("%Y%m%d")}.csv',
        mimetype='text/csv'
    )
# 27. AI-Powered Financial Chat Assistant to get the AI chat of the user of the specified user_id

@app.route('/ai-chat', methods=['POST'])
@login_required
def ai_chat():
    """
    AI-powered financial chat route for FinTrack
    
    Returns:
        JSON response with financial insights
    """
    try:
        # Get user information and message
        user_id = session['user_id']
        user_message = request.json.get('message', '').strip()
        
        # Fetch user's expenses
        expenses = list(expenses_collection.find({'user_id': user_id}))
        
        # Handle no expenses scenario
        if not expenses:
            return jsonify({
                "response": "Welcome to FinTrack! You haven't recorded any expenses yet. Start tracking your spending to get personalized financial insights."
            })
        
        # Convert dates if needed
        for expense in expenses:
            if not isinstance(expense['date'], datetime):
                expense['date'] = datetime.fromisoformat(str(expense['date']))
        
        # Prepare financial context
        total_spent = sum(e['amount'] for e in expenses)
        category_spending = {}
        for e in expenses:
            category_spending[e['category']] = category_spending.get(e['category'], 0) + e['amount']
        
        # Sort categories by spending
        sorted_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)
        
        # Create prompt for AI model
        prompt = f"""
        Financial Context:
        - Total Expenses: ₹{total_spent:.2f}
        - Top Categories: {', '.join([f"{cat}: ₹{amount:.2f}" for cat, amount in sorted_categories[:3]])}
        - Total Transactions: {len(expenses)}

        User Query: {user_message}

        Provide a concise, helpful financial insight or advice based on the context and query.
        """
        
        # Generate AI response
        model = genai.GenerativeModel('gemini-1.5-pro')
        generation_config = {
            "temperature": 0.2,
            "max_output_tokens": 200
        }
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return jsonify({"response": response.text})
    
    except Exception as e:
        # Simple error handling
        app.logger.error(f"FinTrack AI Chat Error: {e}")
        
        return jsonify({
            "response": "I'm having trouble processing your request. Could you please try again?"
        })




if __name__ == '__main__':
    app.run(debug=True)
