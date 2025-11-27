#!/usr/bin/env python3
"""
Comprehensive Test Suite
Tests all aspects of the My Diary application
"""

import os
import sys
import unittest
import tempfile
import json
from datetime import datetime, timedelta
from flask import Flask
from app import create_app, db
from app.models.user import User
from app.models.entry import Entry
from config import TestingConfig

class MyDiaryTestCase(unittest.TestCase):
    """Base test case for My Diary"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.app = create_app(TestingConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create test database
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app.config['DATABASE_URL'] = f'sqlite:///{self.db_path}'
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['TESTING'] = True
        
        db.create_all()
        self.client = self.app.test_client()
        
        # Create test user
        self.test_user = User(
            username='testuser',
            email='test@example.com',
            password='Test123!@#'
        )
        db.session.add(self.test_user)
        db.session.commit()
    
    def tearDown(self):
        """Clean up test fixtures"""
        db.session.remove()
        db.drop_all()
        os.close(self.db_fd)
        os.unlink(self.db_path)
        self.app_context.pop()

class AuthenticationTests(MyDiaryTestCase):
    """Test authentication functionality"""
    
    def test_registration_page_loads(self):
        """Test that registration page loads"""
        response = self.client.get('/auth/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Register', response.data)
    
    def test_login_page_loads(self):
        """Test that login page loads"""
        response = self.client.get('/auth/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign In', response.data)
    
    def test_valid_registration(self):
        """Test valid user registration"""
        response = self.client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'NewUser123!@',
            'confirm_password': 'NewUser123!@'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        user = User.query.filter_by(email='newuser@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'newuser')
    
    def test_invalid_registration_weak_password(self):
        """Test registration with weak password"""
        response = self.client.post('/auth/register', data={
            'username': 'weakuser',
            'email': 'weak@example.com',
            'password': '123',
            'confirm_password': '123'
        })
        
        self.assertEqual(response.status_code, 200)
        user = User.query.filter_by(email='weak@example.com').first()
        self.assertIsNone(user)
    
    def test_valid_login(self):
        """Test valid user login"""
        response = self.client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'Test123!@#',
            'remember_me': False
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)
    
    def test_invalid_login(self):
        """Test invalid login credentials"""
        response = self.client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid email or password', response.data)
    
    def test_logout(self):
        """Test user logout"""
        # Login first
        self.client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'Test123!@#'
        })
        
        # Then logout
        response = self.client.get('/auth/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'My Diary', response.data)

class DashboardTests(MyDiaryTestCase):
    """Test dashboard functionality"""
    
    def login_test_user(self):
        """Helper method to login test user"""
        self.client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'Test123!@#'
        })
    
    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication"""
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_dashboard_loads(self):
        """Test that dashboard loads for authenticated user"""
        self.login_test_user()
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome back', response.data)
    
    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        self.login_test_user()
        
        # Create test entries
        for i in range(5):
            entry = Entry(
                title=f'Test Entry {i}',
                content=f'This is test entry number {i}',
                mood='happy',
                user_id=self.test_user.id
            )
            db.session.add(entry)
        db.session.commit()
        
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'5', response.data)  # Should show entry count

class EntryTests(MyDiaryTestCase):
    """Test diary entry functionality"""
    
    def login_test_user(self):
        """Helper method to login test user"""
        self.client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'Test123!@#'
        })
    
    def test_new_entry_page_loads(self):
        """Test that new entry page loads"""
        self.login_test_user()
        response = self.client.get('/new')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'New Entry', response.data)
    
    def test_create_entry(self):
        """Test creating a new diary entry"""
        self.login_test_user()
        
        response = self.client.post('/new', data={
            'title': 'Test Entry',
            'content': 'This is a test entry content.',
            'mood': 'happy',
            'tags': 'test,happy',
            'is_private': False
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        entry = Entry.query.filter_by(title='Test Entry').first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.content, 'This is a test entry content.')
        self.assertEqual(entry.mood, 'happy')
    
    def test_view_entry(self):
        """Test viewing a diary entry"""
        self.login_test_user()
        
        # Create test entry
        entry = Entry(
            title='Test Entry',
            content='Test content',
            mood='happy',
            user_id=self.test_user.id
        )
        db.session.add(entry)
        db.session.commit()
        
        response = self.client.get(f'/entry/{entry.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Entry', response.data)
    
    def test_edit_entry(self):
        """Test editing a diary entry"""
        self.login_test_user()
        
        # Create test entry
        entry = Entry(
            title='Original Title',
            content='Original content',
            mood='happy',
            user_id=self.test_user.id
        )
        db.session.add(entry)
        db.session.commit()
        
        response = self.client.post(f'/edit/{entry.id}', data={
            'title': 'Updated Title',
            'content': 'Updated content',
            'mood': 'excited',
            'tags': 'updated',
            'is_private': False
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        updated_entry = Entry.query.get(entry.id)
        self.assertEqual(updated_entry.title, 'Updated Title')
        self.assertEqual(updated_entry.content, 'Updated content')
        self.assertEqual(updated_entry.mood, 'excited')
    
    def test_delete_entry(self):
        """Test deleting a diary entry"""
        self.login_test_user()
        
        # Create test entry
        entry = Entry(
            title='Test Entry',
            content='Test content',
            mood='happy',
            user_id=self.test_user.id
        )
        db.session.add(entry)
        db.session.commit()
        
        response = self.client.post(f'/delete/{entry.id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        deleted_entry = Entry.query.get(entry.id)
        self.assertIsNone(deleted_entry)

class SearchTests(MyDiaryTestCase):
    """Test search functionality"""
    
    def login_test_user(self):
        """Helper method to login test user"""
        self.client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'Test123!@#'
        })
    
    def test_search_page_loads(self):
        """Test that search page loads"""
        self.login_test_user()
        response = self.client.get('/search')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Search', response.data)
    
    def test_search_by_title(self):
        """Test searching by title"""
        self.login_test_user()
        
        # Create test entries
        entry1 = Entry(
            title='Happy Day',
            content='Content about happiness',
            mood='happy',
            user_id=self.test_user.id
        )
        entry2 = Entry(
            title='Sad Day',
            content='Content about sadness',
            mood='sad',
            user_id=self.test_user.id
        )
        db.session.add(entry1)
        db.session.add(entry2)
        db.session.commit()
        
        response = self.client.get('/search?search=Happy&search_type=title')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Happy Day', response.data)
        self.assertNotIn(b'Sad Day', response.data)
    
    def test_search_by_content(self):
        """Test searching by content"""
        self.login_test_user()
        
        # Create test entry
        entry = Entry(
            title='Test Entry',
            content='This is about happiness and joy',
            mood='happy',
            user_id=self.test_user.id
        )
        db.session.add(entry)
        db.session.commit()
        
        response = self.client.get('/search?search=happiness&search_type=content')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Entry', response.data)

class SecurityTests(MyDiaryTestCase):
    """Test security features"""
    
    def test_csrf_protection(self):
        """Test CSRF protection (when enabled)"""
        # This test would need CSRF enabled to be meaningful
        pass
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        # Test multiple rapid requests
        responses = []
        for i in range(15):  # Exceed typical rate limit
            response = self.client.post('/auth/login', data={
                'email': 'test@example.com',
                'password': 'wrongpassword'
            })
            responses.append(response.status_code)
        
        # Should eventually hit rate limit
        self.assertIn(429, responses)  # Too Many Requests
    
    def test_password_strength_validation(self):
        """Test password strength requirements"""
        weak_passwords = ['123', 'password', 'abc', 'test']
        
        for password in weak_passwords:
            response = self.client.post('/auth/register', data={
                'username': f'user_{password}',
                'email': f'{password}@example.com',
                'password': password,
                'confirm_password': password
            })
            
            # Should reject weak passwords
            self.assertEqual(response.status_code, 200)
            user = User.query.filter_by(email=f'{password}@example.com').first()
            self.assertIsNone(user)

class PerformanceTests(MyDiaryTestCase):
    """Test performance aspects"""
    
    def login_test_user(self):
        """Helper method to login test user"""
        self.client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'Test123!@#'
        })
    
    def test_dashboard_load_time(self):
        """Test dashboard load time with many entries"""
        self.login_test_user()
        
        # Create many entries
        for i in range(100):
            entry = Entry(
                title=f'Entry {i}',
                content=f'Content for entry {i}',
                mood='happy',
                user_id=self.test_user.id
            )
            db.session.add(entry)
        db.session.commit()
        
        start_time = datetime.now()
        response = self.client.get('/dashboard')
        load_time = (datetime.now() - start_time).total_seconds()
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(load_time, 2.0)  # Should load in under 2 seconds
    
    def test_search_performance(self):
        """Test search performance with large dataset"""
        self.login_test_user()
        
        # Create many entries
        for i in range(200):
            entry = Entry(
                title=f'Entry {i}',
                content=f'Content with keyword test_{i}',
                mood='happy',
                user_id=self.test_user.id
            )
            db.session.add(entry)
        db.session.commit()
        
        start_time = datetime.now()
        response = self.client.get('/search?search=test')
        search_time = (datetime.now() - start_time).total_seconds()
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(search_time, 1.0)  # Should search in under 1 second

class AccessibilityTests(MyDiaryTestCase):
    """Test accessibility features"""
    
    def test_semantic_html_structure(self):
        """Test proper semantic HTML structure"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Check for semantic elements
        self.assertIn(b'<header>', response.data)
        self.assertIn(b'<main>', response.data)
        self.assertIn(b'<nav>', response.data)
    
    def test_alt_text_for_images(self):
        """Test that images have alt text"""
        # This would require images in templates to test properly
        pass
    
    def test_form_labels(self):
        """Test that form inputs have proper labels"""
        response = self.client.get('/auth/register')
        self.assertEqual(response.status_code, 200)
        
        # Check for form labels
        self.assertIn(b'<label', response.data)

class IntegrationTests(MyDiaryTestCase):
    """Integration tests for complete workflows"""
    
    def test_complete_user_journey(self):
        """Test complete user journey from registration to entry creation"""
        # Register new user
        response = self.client.post('/auth/register', data={
            'username': 'journeyuser',
            'email': 'journey@example.com',
            'password': 'JourneyUser123!@',
            'confirm_password': 'JourneyUser123!@'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Login
        response = self.client.post('/auth/login', data={
            'email': 'journey@example.com',
            'password': 'JourneyUser123!@'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)
        
        # Create entry
        response = self.client.post('/new', data={
            'title': 'My First Entry',
            'content': 'This is my first diary entry!',
            'mood': 'happy',
            'tags': 'first,happy',
            'is_private': False
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify entry exists
        user = User.query.filter_by(email='journey@example.com').first()
        entry = Entry.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.title, 'My First Entry')
        
        # Search for entry
        response = self.client.get('/search?search=First')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'My First Entry', response.data)

def run_all_tests():
    """Run all test suites"""
    print("My Diary Comprehensive Test Suite")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        AuthenticationTests,
        DashboardTests,
        EntryTests,
        SearchTests,
        SecurityTests,
        PerformanceTests,
        AccessibilityTests,
        IntegrationTests
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    if result.wasSuccessful():
        print("\nAll tests passed!")
        return True
    else:
        print("\nSome tests failed!")
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run My Diary test suite')
    parser.add_argument('--class', dest='test_class', help='Run specific test class')
    parser.add_argument('--method', dest='test_method', help='Run specific test method')
    args = parser.parse_args()
    
    if args.test_class:
        # Run specific test class
        suite = unittest.TestSuite()
        loader = unittest.TestLoader()
        
        if args.test_method:
            # Run specific test method
            suite.addTest(getattr(sys.modules[__name__], args.test_class)(args.test_method))
        else:
            # Run entire test class
            suite.addTests(loader.loadTestsFromTestCase(getattr(sys.modules[__name__], args.test_class)))
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
    else:
        # Run all tests
        success = run_all_tests()
        sys.exit(0 if success else 1)
