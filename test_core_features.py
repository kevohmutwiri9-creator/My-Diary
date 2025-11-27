#!/usr/bin/env python3
"""
Core Features Testing Script
Tests all essential functionality of the My Diary application
"""

import os
import sys
import requests
import time
from urllib.parse import urljoin
from datetime import datetime

class FeatureTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.auth_token = None
        
    def log_test(self, test_name, status, details="", response_time=0):
        """Log test results"""
        result = {
            'test': test_name,
            'status': status,
            'details': details,
            'response_time': response_time,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status} ({response_time:.3f}s)")
        if details:
            print(f"   Details: {details}")
    
    def test_endpoint(self, endpoint, method="GET", data=None, expected_status=200):
        """Test an endpoint and return response"""
        url = urljoin(self.base_url, endpoint)
        start_time = time.time()
        
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, data=data)
            elif method == "PUT":
                response = self.session.put(url, data=data)
            elif method == "DELETE":
                response = self.session.delete(url)
            
            response_time = time.time() - start_time
            return response, response_time
            
        except Exception as e:
            response_time = time.time() - start_time
            return None, response_time
    
    def test_basic_connectivity(self):
        """Test if the application is running"""
        print("\n🔍 Testing Basic Connectivity")
        print("=" * 40)
        
        response, response_time = self.test_endpoint("/")
        
        if response and response.status_code == 200:
            self.log_test("Basic Connectivity", "PASS", "Application is running", response_time)
            return True
        else:
            status = response.status_code if response else "No response"
            self.log_test("Basic Connectivity", "FAIL", f"Status: {status}", response_time)
            return False
    
    def test_login_page(self):
        """Test login page accessibility"""
        print("\n🔐 Testing Authentication Pages")
        print("=" * 40)
        
        # Test login page
        response, response_time = self.test_endpoint("/auth/login")
        if response and response.status_code == 200:
            self.log_test("Login Page", "PASS", "Login page accessible", response_time)
        else:
            self.log_test("Login Page", "FAIL", f"Status: {response.status_code if response else 'No response'}", response_time)
            return False
        
        # Test registration page
        response, response_time = self.test_endpoint("/auth/register")
        if response and response.status_code == 200:
            self.log_test("Registration Page", "PASS", "Registration page accessible", response_time)
        else:
            self.log_test("Registration Page", "FAIL", f"Status: {response.status_code if response else 'No response'}", response_time)
        
        return True
    
    def test_user_login(self):
        """Test user login functionality"""
        print("\n🔑 Testing User Login")
        print("=" * 40)
        
        login_data = {
            'email': 'admin@example.com',
            'password': 'Admin123!',
            'remember': False
        }
        
        response, response_time = self.test_endpoint("/auth/login", "POST", login_data, expected_status=302)
        
        if response and response.status_code in [302, 200]:
            # Check if login was successful by checking if we're redirected or get success response
            if response.status_code == 302 or "dashboard" in response.text.lower():
                self.log_test("User Login", "PASS", "Login successful", response_time)
                return True
            else:
                self.log_test("User Login", "FAIL", "Login failed - invalid credentials", response_time)
        else:
            self.log_test("User Login", "FAIL", f"Login failed - status: {response.status_code if response else 'No response'}", response_time)
        
        return False
    
    def test_dashboard_access(self):
        """Test dashboard access after login"""
        print("\n📊 Testing Dashboard Access")
        print("=" * 40)
        
        response, response_time = self.test_endpoint("/dashboard")
        
        if response and response.status_code == 200:
            if "dashboard" in response.text.lower() or "entries" in response.text.lower():
                self.log_test("Dashboard Access", "PASS", "Dashboard loaded successfully", response_time)
                return True
            else:
                self.log_test("Dashboard Access", "FAIL", "Dashboard content not found", response_time)
        else:
            self.log_test("Dashboard Access", "FAIL", f"Status: {response.status_code if response else 'No response'}", response_time)
        
        return False
    
    def test_entry_creation(self):
        """Test diary entry creation"""
        print("\n✍️ Testing Entry Creation")
        print("=" * 40)
        
        # Test new entry page
        response, response_time = self.test_endpoint("/new")
        if response and response.status_code == 200:
            self.log_test("New Entry Page", "PASS", "New entry page accessible", response_time)
            
            # Test entry creation
            entry_data = {
                'title': 'Test Entry',
                'content': 'This is a test entry created during automated testing.',
                'mood': 'neutral',
                'tags': 'testing,automation',
                'is_private': False
            }
            
            response, response_time = self.test_endpoint("/new", "POST", entry_data, expected_status=302)
            
            if response and response.status_code in [302, 200]:
                self.log_test("Entry Creation", "PASS", "Entry created successfully", response_time)
                return True
            else:
                self.log_test("Entry Creation", "FAIL", f"Failed to create entry - status: {response.status_code if response else 'No response'}", response_time)
        else:
            self.log_test("New Entry Page", "FAIL", f"Status: {response.status_code if response else 'No response'}", response_time)
        
        return False
    
    def test_admin_access(self):
        """Test admin panel access"""
        print("\n👤 Testing Admin Access")
        print("=" * 40)
        
        # Test admin dashboard
        response, response_time = self.test_endpoint("/admin")
        if response and response.status_code == 200:
            self.log_test("Admin Dashboard", "PASS", "Admin dashboard accessible", response_time)
        elif response and response.status_code == 403:
            self.log_test("Admin Dashboard", "FAIL", "Access denied - user not admin", response_time)
        else:
            self.log_test("Admin Dashboard", "FAIL", f"Status: {response.status_code if response else 'No response'}", response_time)
        
        # Test admin settings
        response, response_time = self.test_endpoint("/admin/settings")
        if response and response.status_code == 200:
            self.log_test("Admin Settings", "PASS", "Admin settings accessible", response_time)
        elif response and response.status_code == 403:
            self.log_test("Admin Settings", "FAIL", "Access denied - user not admin", response_time)
        else:
            self.log_test("Admin Settings", "FAIL", f"Status: {response.status_code if response else 'No response'}", response_time)
        
        return True
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        print("\n🔌 Testing API Endpoints")
        print("=" * 40)
        
        api_tests = [
            ("/api/productivity/stats", "Productivity Stats API"),
            ("/admin/api/stats", "Admin Stats API"),
        ]
        
        for endpoint, name in api_tests:
            response, response_time = self.test_endpoint(endpoint)
            
            if response and response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success'):
                        self.log_test(name, "PASS", "API response successful", response_time)
                    else:
                        self.log_test(name, "FAIL", "API returned success=False", response_time)
                except:
                    self.log_test(name, "FAIL", "Invalid JSON response", response_time)
            else:
                self.log_test(name, "FAIL", f"Status: {response.status_code if response else 'No response'}", response_time)
        
        return True
    
    def test_static_files(self):
        """Test static file serving"""
        print("\n📁 Testing Static Files")
        print("=" * 40)
        
        static_tests = [
            ("/static/css/custom_clean.css", "CSS File"),
            ("/static/js/theme.js", "JavaScript File"),
            ("/static/icon/diary.png", "Favicon"),
        ]
        
        for file_path, name in static_tests:
            response, response_time = self.test_endpoint(file_path)
            
            if response and response.status_code == 200:
                self.log_test(name, "PASS", f"File size: {len(response.content)} bytes", response_time)
            else:
                self.log_test(name, "FAIL", f"Status: {response.status_code if response else 'No response'}", response_time)
        
        return True
    
    def test_error_pages(self):
        """Test error page functionality"""
        print("\n⚠️ Testing Error Pages")
        print("=" * 40)
        
        # Test 404 page
        response, response_time = self.test_endpoint("/nonexistent-page-12345")
        if response and response.status_code == 404:
            self.log_test("404 Error Page", "PASS", "Custom 404 page working", response_time)
        else:
            self.log_test("404 Error Page", "FAIL", f"Expected 404, got: {response.status_code if response else 'No response'}", response_time)
        
        return True
    
    def run_all_tests(self):
        """Run all core feature tests"""
        print("🧪 My Diary Core Features Test Suite")
        print("=" * 50)
        print(f"Testing URL: {self.base_url}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        
        tests = [
            self.test_basic_connectivity,
            self.test_login_page,
            self.test_user_login,
            self.test_dashboard_access,
            self.test_entry_creation,
            self.test_admin_access,
            self.test_api_endpoints,
            self.test_static_files,
            self.test_error_pages,
        ]
        
        passed = 0
        failed = 0
        warnings = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                print(f"❌ {test.__name__}: ERROR - {e}")
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️ Warnings: {warnings}")
        print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "N/A")
        
        # Detailed results
        print("\n📋 Detailed Results:")
        for result in self.test_results:
            status_icon = "✅" if result['status'] == "PASS" else "❌" if result['status'] == "FAIL" else "⚠️"
            print(f"{status_icon} {result['test']}: {result['status']} ({result['response_time']:.3f}s)")
        
        return failed == 0

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test My Diary core features')
    parser.add_argument('--url', default='http://localhost:5000', help='Base URL to test')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    tester = FeatureTester(args.url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
