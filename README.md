# My Diary

A secure and feature-rich personal diary application built with Flask. Write, edit, and manage your personal journal entries with markdown support and privacy controls.

## ✨ Features

### 🔐 Security Features
- **Strong Password Policy**: Enforced 12+ character passwords with mixed case, numbers, and special characters
- **Account Security**: Failed login attempt tracking with automatic account lockout
- **Rate Limiting**: Protection against brute-force attacks (200 requests/day, 50/hour per user)
- **CSRF Protection**: Cross-Site Request Forgery prevention on all forms
- **Security Headers**: Comprehensive HTTP security headers (CSP, HSTS, XSS protection)
- **Session Security**: Secure, HTTP-only cookies with automatic timeout

### 📝 Diary Features
- **User Authentication**: Secure registration and login system with email verification
- **Rich Text Entries**: Write in markdown with live preview and syntax highlighting
- **Privacy Controls**: Mark entries as private or public with granular visibility settings
- **Mood Tracking**: Tag your entries with your current mood for emotional insights
- **Word Count**: Automatic word counting for each entry
- **Advanced Search**: Find entries by title, content, mood, or date range
- **Responsive Design**: Works seamlessly on desktop and mobile devices

### ⚡ Performance & UX
- **Database Optimization**: Strategic indexes for fast queries and searches
- **Caching**: Intelligent caching for improved response times
- **Dark/Light Theme**: System-aware theme switching with user preference persistence
- **Real-time Updates**: Live markdown preview and instant feedback
- **Export Ready**: Built-in support for future export functionality

### 🛠️ Developer Features
- **Modern Architecture**: Flask application factory pattern with blueprint organization
- **Comprehensive Logging**: Detailed logging with rotation and multiple levels
- **Environment Configuration**: Flexible configuration for development, testing, and production
- **Database Migrations**: Safe schema updates with Flask-Migrate

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- SQLite (included with Python)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/my-diary.git
   cd my-diary
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   # Create a .env file
   cp .env.example .env
   ```
   Edit the `.env` file with your configuration.

5. Initialize the database:
   ```bash
   flask db upgrade
   ```

### Running the Application

Start the development server:
```bash
flask run
```

Then open your browser and navigate to `http://localhost:5000`.

On Render (free tier compatible), set the **Start Command** to:
```bash
./render_start.sh
```
This script runs `flask db upgrade` before launching Gunicorn so migrations apply automatically without needing shell access.

## 🤖 Gemini Diary Assistant

The floating assistant in the UI uses Google Gemini for contextual answers based on your recent diary entries.

### Requirements

- `google-generativeai` and `python-dotenv` are included in `requirements.txt`.
- A valid Gemini API key with access to the model family listed below.

### Configuration

1. Add the key to your environment before starting the server (PowerShell example):
   ```powershell
   $env:GEMINI_API_KEY = "your-real-key"
   python run.py
   ```
   Or place the value in `.env`:
   ```ini
   GEMINI_API_KEY=your-real-key
   ```
2. Supported model IDs (update `app/routes/assistant.py` if Google changes availability):
   - `models/gemini-2.5-flash`
   - `models/gemini-2.5-pro`
   - `models/gemini-flash-latest`
   - `models/gemini-pro-latest`

If none of these models are available to your key, run the helper script in `logs/o.py` or execute the snippet below to discover accessible options:

```python
import google.generativeai as genai
genai.configure(api_key="YOUR_KEY")
for model in genai.list_models():
    if "generateContent" in model.supported_generation_methods:
        print(model.name)
```

Update the `model_candidates` list in `app/routes/assistant.py` accordingly.

## 🔒 Password Reset Email Setup

The "Forgot password" flow relies on SMTP credentials and signed reset tokens.

1. Set these variables in `.env` (Render → Environment tab in production):
   ```ini
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   MAIL_DEFAULT_SENDER=My Diary <your-email@gmail.com>
   PASSWORD_RESET_SALT=change-me
   PASSWORD_RESET_TOKEN_MAX_AGE=3600  # seconds
   ```
   For Gmail, create an App Password under security settings.
2. Install dependencies via `pip install -r requirements.txt` (includes `Flask-Mail`).
3. Restart the server so credentials load, then use **Forgot your password?** on the login screen.

Emails render using `app/templates/emails/reset_password.(txt|html)`.

## 🛠️ Project Structure

```
my-diary/
├── app/
│   ├── __init__.py       # Application factory
│   ├── models/           # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── entry.py
│   └── routes/           # Application routes
│       ├── __init__.py
│       ├── auth.py       # Authentication routes
│       └── main.py       # Main application routes
├── migrations/           # Database migrations
├── static/               # Static files (CSS, JS, images)
├── templates/            # HTML templates
├── .env                  # Environment variables
├── .gitignore
├── config.py             # Configuration settings
├── requirements.txt      # Project dependencies
└── wsgi.py              # WSGI entry point
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Application
FLASK_APP=wsgi.py
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-here

# Database
DATABASE_URL=sqlite:///app.db

# Security
SESSION_COOKIE_SECURE=false  # Set to true in production with HTTPS
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax

# Rate Limiting
RATELIMIT_STORAGE_URL=memory://  # Use Redis in production: redis://localhost:6379

# Email (for future features)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### Security Configuration

The application includes comprehensive security features:

- **Password Policy**: 12+ characters, mixed case, numbers, special characters
- **Account Lockout**: 5 failed attempts trigger 15-minute lockout
- **Rate Limiting**: 200 requests/day, 50 requests/hour per user
- **Session Management**: 30-minute automatic timeout
- **CSRF Protection**: All forms protected against cross-site request forgery

### Production Deployment

For production deployment:

1. Set `FLASK_ENV=production`
2. Use a production WSGI server (Gunicorn)
3. Enable HTTPS and set `SESSION_COOKIE_SECURE=true`
4. Configure proper logging and monitoring
5. Set up database backups

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Styled with [Bootstrap](https://getbootstrap.com/)
- Markdown support with [Python-Markdown](https://python-markdown.github.io/)

2. Run the application:
   ```bash
   python app.py
   ```

3. Open your browser and go to `http://localhost:5000`

## Usage

1. **Secure Registration**: Create an account with a strong password (12+ characters, mixed case, numbers, special characters)
2. **Safe Login**: The system tracks failed login attempts and temporarily locks accounts after 5 failed tries
3. **Write Entries**: Create rich markdown entries with mood tracking and privacy controls
4. **Search & Filter**: Use advanced search to find entries by content, mood, or date
5. **Theme Support**: Switch between light and dark themes (follows system preference)
6. **Manage Account**: Update your profile and change passwords securely

### Security Best Practices

- Use strong, unique passwords for your diary account
- Enable two-factor authentication when available
- Regularly update your password
- Be cautious with public entries
- Log out when using shared computers

### Performance Tips

- The application includes automatic caching for improved performance
- Database queries are optimized with strategic indexes
- Static assets are preloaded for faster page loads
- Rate limiting protects against abuse while maintaining usability
