# FinTrack - AI-Powered Personal Finance Tracker 💰

![MIT License](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-red.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-4.4+-green.svg)

## Overview 🚀
FinTrack is an advanced personal finance management application designed to help users track their expenses, analyze spending habits, and receive AI-powered financial insights. Built with Flask and MongoDB, FinTrack provides an intuitive and seamless experience for managing personal finances efficiently.

## Live Demo 
- **Live Demo:** [Click Here](https://fintrack-aj5l.onrender.com)

## Features ✨

### 🔐 Secure Authentication
- OTP-based user registration for added security.
- Secure login/logout functionality with session management.
- Password hashing to ensure user data privacy.

### 📊 Expense Management
- Add, edit, and delete expenses effortlessly.
- Auto-categorization of expenses.
- Track spending patterns with real-time updates.
- Advanced filtering and search functionalities.

### 📈 Smart Dashboard
- Get a real-time financial overview.
- Category-wise expense breakdown.
- Monthly spending trends analysis.
- Visual representation with charts and graphs.

### 🤖 AI-Powered Insights
- Personalized financial advice based on spending patterns.
- Potential savings suggestions and risk alerts.
- AI-driven recommendations for smarter financial decisions.

### 📑 Report Generation
- Generate detailed financial reports.
- Export reports in multiple formats (PDF, Excel, CSV).
- Customize report parameters for tailored insights.

### 💬 Smart Chat Assistant
- AI-powered financial assistant for real-time query resolution.
- Get insights into your spending patterns.
- Receive custom financial recommendations.

## Tech Stack 🛠️

### Backend:
- **Flask** - Web framework for backend development.
- **MongoDB** - NoSQL database for storing financial data.
- **Python** - Primary programming language.
- **Google Generative AI** - AI/ML capabilities for insights.
- **PyMongo** - MongoDB driver for Python.
- **ReportLab** - PDF generation.
- **Pandas** - Data manipulation and analysis.

### Frontend:
- **HTML/CSS** - Structuring and styling the UI.
- **JavaScript** - Interactive functionalities.
- **Tailwind CSS** - Modern styling framework.
- **Chart.js** - Data visualization through charts and graphs.
- **Alpine.js** - Lightweight JS framework for UI interactions.
- **Font Awesome** - Icons for UI enhancement.

### Security:
- **Werkzeug** - Secure password hashing.
- **Flask-Limiter** - Rate limiting for API security.
- **OTP Verification** - Email authentication for added protection.

## Installation 🚀

### Step 1: Clone the Repository
```sh
git clone https://github.com/TechWithAkash/Expense_tracker.git
cd Expense_tracker
```

### Step 2: Create a Virtual Environment
```sh
python -m venv venv
```

### Step 3: Activate the Virtual Environment
#### For Windows:
```sh
venv\Scripts\activate
```
#### For Unix/MacOS:
```sh
source venv/bin/activate
```

### Step 4: Install Dependencies
```sh
pip install -r requirements.txt
```

### Step 5: Set Up Environment Variables
Create a `.env` file in the project directory and add:
```
MONGODB_URI=your_mongodb_uri
GOOGLE_GENERATIVE_AI_API_KEY=your_api_key
SENDER_EMAIL=your_email
SENDER_APP_PASSWORD=your_app_password
```

### Step 6: Run the Application
```sh
python app.py
```

## Environment Variables 🔑
```
MONGODB_URI=your_mongodb_uri
GOOGLE_GENERATIVE_AI_API_KEY=your_api_key
SENDER_EMAIL=your_email
SENDER_APP_PASSWORD=your_app_password
```

## API Reference 📚
| Endpoint         | Method | Description                         |
|-----------------|--------|-------------------------------------|
| `/register`      | POST   | Register a new user                |
| `/login`        | POST   | Authenticate and log in a user     |
| `/add_expense`  | POST   | Add a new expense                  |
| `/generate_report` | POST | Generate financial reports         |
| `/ai-insights`  | GET    | Fetch AI-powered financial insights |
| `/ai-chat`      | POST   | Interact with AI assistant         |

## Screenshots 📸

## Login Page  
![Image](https://github.com/user-attachments/assets/47ab1e4c-32ac-4e03-807f-05934f56933d)

## Home Page  
![Image](https://github.com/user-attachments/assets/ef4d331f-6062-4dbe-9fdd-a16686dbff2d)

## Add Expense  
![Image](https://github.com/user-attachments/assets/c2c30998-f91d-44d2-8116-3feea1246875)

## Dashboard   
![Image](https://github.com/user-attachments/assets/2bd0f169-66ec-43c7-b655-5bb0482c9d8c)

## Contributing 🤝
Contributions are always welcome! If you want to contribute, please check out the [contributing guidelines](CONTRIBUTING.md).

## Authors 👨‍💻
- **@TechWithAkash**  

## License 📄
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Support the Project!
If you find this project useful, don't forget to **star the repo!** ⭐

[Live Demo](#) | [Report Bug](#) | [Request Feature](#)

