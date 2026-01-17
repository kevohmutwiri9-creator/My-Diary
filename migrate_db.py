#!/usr/bin/env python3
"""
Database migration script to add new columns for premium features
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Import models after database initialization
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    theme = db.Column(db.String(20), nullable=True)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

class Entry(db.Model):
    __tablename__ = 'entry'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)
    mood = db.Column(db.String(30), nullable=True)
    tags = db.Column(db.String(300), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    is_favorite = db.Column(db.Boolean, nullable=False, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

def migrate_database():
    """Add new columns to existing database"""
    with app.app_context():
        try:
            # Check if columns exist and add them if they don't
            inspector = db.inspect(db.engine)
            
            # Check User table columns (user is a reserved keyword in SQL Server)
            user_columns = [col['name'] for col in inspector.get_columns('user')]
            
            if 'theme' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE [user] ADD theme VARCHAR(20)'))
                print("Added 'theme' column to user table")
            
            if 'reset_token' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE [user] ADD reset_token VARCHAR(100)'))
                print("Added 'reset_token' column to user table")
            
            if 'reset_token_expires' not in user_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE [user] ADD reset_token_expires DATETIME'))
                print("Added 'reset_token_expires' column to user table")
            
            # Check Entry table columns
            entry_columns = [col['name'] for col in inspector.get_columns('entry')]
            
            if 'category' not in entry_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE entry ADD category VARCHAR(50)'))
                print("Added 'category' column to entry table")
            
            if 'is_favorite' not in entry_columns:
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE entry ADD is_favorite BIT DEFAULT 0'))
                print("Added 'is_favorite' column to entry table")
            
            print("Database migration completed successfully!")
            
        except Exception as e:
            print(f"Migration error: {e}")
            print("You may need to run this manually in your database.")

if __name__ == '__main__':
    migrate_database()
