#!/usr/bin/env python3
"""
Simple test script to verify FastAPI server functionality
"""

import requests
import json
import time
import sys

SERVER_URL = "http://localhost:5127"

def test_endpoint(method, endpoint, data=None, description=""):
    """Test a single endpoint"""
    print(f"\n🧪 Testing {method} {endpoint} - {description}")
    
    try:
        if method == "GET":
            response = requests.get(f"{SERVER_URL}{endpoint}")
        elif method == "POST":
            headers = {"Content-Type": "application/json"}
            response = requests.post(f"{SERVER_URL}{endpoint}", 
                                   json=data, headers=headers)
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        
        if response.status_code in [200, 201]:
            print("   ✅ Success")
            return True
        else:
            print("   ❌ Failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("🚀 Testing NSE Announcements Tracker API")
    print(f"   Server URL: {SERVER_URL}")
    
    results = []
    
    # Test basic endpoints
    results.append(test_endpoint("GET", "/", description="Root endpoint"))
    results.append(test_endpoint("GET", "/health", description="Health check"))
    results.append(test_endpoint("GET", "/status", description="Get status"))
    results.append(test_endpoint("GET", "/items", description="Get all items"))
    
    # Test polling endpoints
    start_data = {
        "url": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
    }
    results.append(test_endpoint("POST", "/start-polling", start_data, 
                                description="Start polling"))
    
    # Wait a moment for polling to begin
    print("\n⏱️  Waiting 3 seconds for polling to start...")
    time.sleep(3)
    
    # Check status after starting polling
    results.append(test_endpoint("GET", "/status", description="Get status after start"))
    
    # Stop polling
    results.append(test_endpoint("POST", "/stop-polling", description="Stop polling"))
    
    # Check status after stopping
    results.append(test_endpoint("GET", "/status", description="Get status after stop"))
    
    # Summary
    print(f"\n📊 Test Results Summary:")
    passed = sum(results)
    total = len(results)
    print(f"   Passed: {passed}/{total}")
    
    if passed == total:
        print("   🎉 All tests passed!")
        return 0
    else:
        print("   ⚠️  Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 