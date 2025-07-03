#!/usr/bin/env python3
"""
Load Test Runner - Easy way to run different test scenarios
"""

import sys
import os

def run_basic_tests():
    """Run basic load tests"""
    print("🚀 Running basic load tests...")
    os.system("python3 load_testing/basic_load_test.py")

def run_api_tests():
    """Run API-specific tests"""
    print("🤖 Running API load tests...")
    os.system("python3 load_testing/api_load_test.py")

def run_quick_health_check():
    """Quick health check"""
    import requests
    import time
    
    url = "https://hd-produkt-jibeo-c8f5arcrcmg2cpgz.southeastasia-01.azurewebsites.net/"
    
    print("🏥 Quick Health Check...")
    start_time = time.time()
    
    try:
        response = requests.get(url, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            print(f"✅ App is healthy! Response time: {end_time - start_time:.3f}s")
            return True
        else:
            print(f"⚠️ App responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ App is not responding: {e}")
        return False

def main():
    print("🔥 HD-Produkt-Jibeo Load Testing Suite")
    print("=" * 50)
    
    # Quick health check first
    if not run_quick_health_check():
        print("\n❌ App is not healthy. Fix the app before load testing.")
        return
    
    print("\nSelect test type:")
    print("  1. Basic load tests (response times, concurrent requests)")
    print("  2. API load tests (chat endpoints, realistic payloads)")
    print("  3. Both (comprehensive testing)")
    print("  4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        run_basic_tests()
    elif choice == "2":
        run_api_tests()
    elif choice == "3":
        print("\n" + "="*50)
        run_basic_tests()
        print("\n" + "="*50)
        run_api_tests()
    elif choice == "4":
        print("👋 Goodbye!")
    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    main() 