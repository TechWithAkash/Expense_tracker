from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from functools import wraps
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pymongo
from bson import ObjectId
from dotenv import load_dotenv
import sys
import os
import google.generativeai as genai
from dotenv import load_dotenv

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

# 27. AI-Powered Financial Chat Assistant to get the AI chat of the user of the specified user_id
# @app.route('/ai-chat', methods=['POST'])
# @login_required
# def ai_chat():
    try:
        user_id = session['user_id']
        user_message = request.json.get('message', '').strip()
        
        # Get user's financial data
        expenses = list(expenses_collection.find({'user_id': user_id}))
        if not expenses:
            return jsonify({"response": "You haven't recorded any expenses yet. Start adding expenses to get insights!"})
        
        # Process financial data
        daily_spending = {}
        category_spending = {}
        for e in expenses:
            date_str = e['date'].strftime('%Y-%m-%d')
            daily_spending[date_str] = daily_spending.get(date_str, 0) + e['amount']
            category_spending[e['category']] = category_spending.get(e['category'], 0) + e['amount']
        
        # Structure data for AI
        financial_context = f"""
        User's Financial Data:
        - Total expenses: {len(expenses)}
        - Total amount spent: ₹{sum(e['amount'] for e in expenses):.2f}
        - Daily spending peaks: {max(daily_spending.values(), default=0):.2f} on {max(daily_spending, key=daily_spending.get, default='N/A')}
        - Top category: {max(category_spending, key=category_spending.get, default='N/A')} (₹{max(category_spending.values(), default=0):.2f})
        Last 5 transactions:
        {chr(10).join([f"₹{e['amount']:.2f} on {e['date'].strftime('%d %b')} - {e['description']}" for e in expenses[-5:]])}
        """
        
        # Create instruction prompt
        prompt = f"""You are a financial assistant analyzing this data:
        {financial_context}

        User Question: {user_message}

        Response Guidelines:
        1. Answer ONLY using the provided data
        2. Be specific with dates/amounts
        3. Mention exact numbers from data
        4. If unsure, say "Not enough data"
        5. Use ₹ symbol for amounts
        6. Keep responses under 3 sentences

        Examples:
        Q: What day did I spend the most?
        A: Your highest spending was ₹{max(daily_spending.values()):.2f} on {max(daily_spending, key=daily_spending.get)}.

        Q: What's my most frequent category?
        A: You spend most on {max(category_spending, key=category_spending.get)} (₹{max(category_spending.values()):.2f} total).
        """
        
        # Get AI response
        model = genai.GenerativeModel('gemini-1.5-pro')  # Updated model name
        response = model.generate_content(prompt)
        
        return jsonify({"response": response.text})
        
    except Exception as e:
        print(f"Chat Error: {str(e)}")
        return jsonify({"response": "Please try again in a moment. Our AI is currently busy."})
# 28. Run the Flask application

# AI-Powered Financial Chat Assistant
# @app.route('/ai-chat', methods=['POST'])
# @login_required
# def ai_chat():
#     try:
#         user_id = session['user_id']
#         user_message = request.json.get('message', '').strip()
        
#         # Get user's financial data - extended period for better analysis
#         expenses = list(expenses_collection.find({'user_id': user_id}))
#         if not expenses:
#             return jsonify({"response": "You haven't recorded any expenses yet. Start adding expenses to get insights on your financial patterns!"})
        
#         # Advanced financial data analysis
#         total_spent = sum(e['amount'] for e in expenses)
#         avg_transaction = total_spent / len(expenses) if expenses else 0
        
#         # Time-based analysis
#         now = datetime.now()
#         expenses_by_date = {}
#         monthly_spending = {}
#         weekly_spending = {}
#         category_spending = {}
#         recurring_expenses = {}
        
#         # Get current month start and end for monthly view
#         current_month_start = datetime(now.year, now.month, 1)
#         current_month_end = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
        
#         # Previous month for comparison
#         if now.month == 1:  # January
#             prev_month = 12
#             prev_year = now.year - 1
#         else:
#             prev_month = now.month - 1
#             prev_year = now.year
            
#         prev_month_start = datetime(prev_year, prev_month, 1)
#         prev_month_end = datetime(prev_year, prev_month, calendar.monthrange(prev_year, prev_month)[1])
        
#         # Analyze each expense
#         for e in expenses:
#             # Daily analysis
#             date_str = e['date'].strftime('%Y-%m-%d')
#             expenses_by_date[date_str] = expenses_by_date.get(date_str, 0) + e['amount']
            
#             # Monthly analysis
#             month_str = e['date'].strftime('%Y-%m')
#             monthly_spending[month_str] = monthly_spending.get(month_str, 0) + e['amount']
            
#             # Weekly analysis (Monday as start of week)
#             week_start = e['date'] - timedelta(days=e['date'].weekday())
#             week_str = week_start.strftime('%Y-%m-%d')
#             weekly_spending[week_str] = weekly_spending.get(week_str, 0) + e['amount']
            
#             # Category analysis
#             category_spending[e['category']] = category_spending.get(e['category'], 0) + e['amount']
            
#             # Track potential recurring expenses by description
#             desc_key = e['description'].lower().strip()
#             if desc_key not in recurring_expenses:
#                 recurring_expenses[desc_key] = []
#             recurring_expenses[desc_key].append(e['date'])
        
#         # Calculate current month spending
#         current_month_expenses = [e for e in expenses if current_month_start <= e['date'] <= current_month_end]
#         current_month_total = sum(e['amount'] for e in current_month_expenses)
        
#         # Calculate previous month spending
#         prev_month_expenses = [e for e in expenses if prev_month_start <= e['date'] <= prev_month_end]
#         prev_month_total = sum(e['amount'] for e in prev_month_expenses)
        
#         # Monthly spending trend (increase/decrease)
#         monthly_change = 0
#         if prev_month_total > 0:
#             monthly_change = ((current_month_total - prev_month_total) / prev_month_total) * 100
        
#         # Identify potential recurring expenses (appearing at least twice with similar dates)
#         potential_subscriptions = []
#         for desc, dates in recurring_expenses.items():
#             if len(dates) >= 2:
#                 # Find expenses that occur on similar days of month
#                 day_counts = {}
#                 for date in dates:
#                     day = date.day
#                     day_counts[day] = day_counts.get(day, 0) + 1
                
#                 # If an expense occurs on similar days of month multiple times
#                 if any(count >= 2 for count in day_counts.values()):
#                     matching_expenses = [e for e in expenses if e['description'].lower().strip() == desc]
#                     amount = matching_expenses[0]['amount'] if matching_expenses else 0
#                     potential_subscriptions.append({
#                         'description': desc,
#                         'amount': amount,
#                         'occurrences': len(dates)
#                     })
        
#         # Find unusual spending (more than 50% above the average for that category)
#         unusual_spending = []
#         for cat, total in category_spending.items():
#             cat_expenses = [e for e in expenses if e['category'] == cat]
#             cat_avg = total / len(cat_expenses)
            
#             for e in cat_expenses:
#                 if e['amount'] > (cat_avg * 1.5) and e['amount'] > 500:  # Significant amount over average
#                     unusual_spending.append({
#                         'date': e['date'].strftime('%Y-%m-%d'),
#                         'amount': e['amount'],
#                         'description': e['description'],
#                         'category': cat
#                     })
        
#         # Sort unusual spending by amount (highest first)
#         unusual_spending.sort(key=lambda x: x['amount'], reverse=True)
        
#         # Calculate spending frequency
#         days_with_expenses = len(expenses_by_date)
#         date_range = (max([e['date'] for e in expenses]) - min([e['date'] for e in expenses])).days + 1
#         spending_frequency = days_with_expenses / date_range if date_range > 0 else 0
#         spending_frequency_pct = spending_frequency * 100
        
#         # Structure advanced financial insights
#         financial_context = f"""
#         USER FINANCIAL PROFILE:
#         - Total recorded expenses: {len(expenses)}
#         - Total amount spent: ₹{total_spent:.2f}
#         - Average transaction: ₹{avg_transaction:.2f}
#         - Spending frequency: {spending_frequency_pct:.1f}% of days have expenses
        
#         MONTHLY INSIGHTS:
#         - Current month spending: ₹{current_month_total:.2f}
#         - Previous month spending: ₹{prev_month_total:.2f}
#         - Month-over-month change: {monthly_change:+.1f}%
        
#         SPENDING PATTERNS:
#         - Highest daily spending: ₹{max(expenses_by_date.values(), default=0):.2f} on {max(expenses_by_date, key=expenses_by_date.get, default='N/A')}
#         - Top spending category: {max(category_spending, key=category_spending.get, default='N/A')} (₹{max(category_spending.values(), default=0):.2f})
#         - Category breakdown: {', '.join([f"{k}: ₹{v:.2f}" for k, v in sorted(category_spending.items(), key=lambda item: item[1], reverse=True)[:3]])}
        
#         POTENTIAL RECURRING EXPENSES:
#         {chr(10).join([f"- {sub['description'].title()}: ₹{sub['amount']:.2f} (detected {sub['occurrences']} times)" for sub in potential_subscriptions[:3]])}
        
#         UNUSUAL TRANSACTIONS:
#         {chr(10).join([f"- ₹{unu['amount']:.2f} on {unu['date']} - {unu['description']}" for unu in unusual_spending[:3]])}
        
#         RECENT TRANSACTIONS:
#         {chr(10).join([f"- ₹{e['amount']:.2f} on {e['date'].strftime('%d %b')} - {e['description']}" for e in sorted(expenses, key=lambda x: x['date'], reverse=True)[:5]])}
#         """
        
#         # Create finance-specific prompt with expert knowledge
#         prompt = f"""You are an expert financial advisor analyzing personal financial data with 15+ years of experience in personal finance and wealth management user can ask anything spedific to finance please answer it wisely and perfectly.

#         USER DATA:
#         {financial_context}

#         User Question: {user_message}

#         INSTRUCTIONS:
#         1. Provide professional financial insights strictly based on the user's data
#         2. Use precise financial terminology while keeping explanations accessible
#         3. Include specific amounts, dates, and percentages when relevant
#         4. For spending patterns, highlight areas of concern or optimization
#         5. For personal finance questions, provide actionable advice based on the data
#         6. Focus on both short-term patterns and long-term implications
#         7. Be compassionate about financial situations but factual about the data 
#         8. If data is insufficient for a complete answer, be transparent about limitations
#         9. Use ₹ symbol for all monetary values
#         10. Keep responses concise and focused - typically 2-4 sentences
        
#         RESPONSE FORMAT:
#         - Start with a direct answer to the question
#         - Follow with 1-2 insights from the data
#         - End with a brief, actionable recommendation if appropriate
#         """
        
#         # Get AI response
#         model = genai.GenerativeModel('gemini-1.5-pro')
#         generation_config = {
#             "temperature": 0.2,  # Lower temperature for more focused, professional responses
#             "top_p": 0.95,
#             "top_k": 40,
#             "max_output_tokens": 200,  # Keep responses concise
#         }
        
#         response = model.generate_content(
#             prompt,
#             generation_config=generation_config
#         )
        
#         return jsonify({"response": response.text})
        
#     except Exception as e:
#         print(f"Chat Error: {str(e)}")
        
#         # Provide intelligent fallback responses based on the question
#         try:
#             if "what is finance" in user_message.lower():
#                 return jsonify({"response": "Finance is the management of money, investments, and other assets. Looking at your data, you have expenses across various categories, with your highest spending in " + max(category_spending, key=category_spending.get, default='N/A') + "."})
            
#             elif any(word in user_message.lower() for word in ["budget", "spending", "spend", "spent"]):
#                 return jsonify({"response": f"Your total spending is ₹{total_spent:.2f} across {len(expenses)} transactions. Your highest spending category is {max(category_spending, key=category_spending.get, default='N/A')} at ₹{max(category_spending.values(), default=0):.2f}."})
            
#             elif any(word in user_message.lower() for word in ["category", "expense", "expenses"]):
#                 categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)
#                 return jsonify({"response": f"Your top 3 spending categories are: {categories[0][0]} (₹{categories[0][1]:.2f}), {categories[1][0]} (₹{categories[1][1]:.2f}), and {categories[2][0]} (₹{categories[2][1]:.2f})."})
            
#             elif any(word in user_message.lower() for word in ["trend", "pattern", "increase", "decrease"]):
#                 trend_msg = f"Your spending has {'increased' if monthly_change > 0 else 'decreased'} by {abs(monthly_change):.1f}% compared to last month."
#                 return jsonify({"response": trend_msg})
            
#             else:
#                 return jsonify({"response": f"Based on your {len(expenses)} recorded expenses totaling ₹{total_spent:.2f}, you spend most frequently on {max(category_spending, key=category_spending.get, default='N/A')}. I can analyze trends, categories, and specific expense patterns if you'd like more detailed insights."})
                
#         except Exception:
#             # Ultimate fallback if even the fallbacks fail
#             return jsonify({"response": "I'm analyzing your financial data. Could you please try a more specific question about your spending, categories, or financial trends?"})


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
