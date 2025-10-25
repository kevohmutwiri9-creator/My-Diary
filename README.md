# My Diary

A secure and feature-rich personal diary application built with Flask. Write, edit, and manage your personal journal entries with markdown support and privacy controls.

## ✨ Features

- **User Authentication**: Secure registration and login system
- **Rich Text Entries**: Write in markdown with live preview
- **Privacy Controls**: Mark entries as private or public
- **Mood Tracking**: Tag your entries with your current mood
- **Responsive Design**: Works on desktop and mobile devices
- **Search & Filter**: Find entries by date, mood, or keywords
- **Export**: Download your entries in various formats (coming soon)

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

Available configuration options in `.env`:

```
FLASK_APP=wsgi.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///diary.db
```

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

1. **Register** a new account or **login** if you already have one
2. **Write** new diary entries from the dashboard
3. **View** your entries and track your thoughts over time
4. **Delete** entries you no longer want to keep

## Database

The application uses SQLite by default. The database file `diary.db` will be created automatically in the project directory.

## Security Note

Remember to change the `SECRET_KEY` in the app configuration before using in production!
