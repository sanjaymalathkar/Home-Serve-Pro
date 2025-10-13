#!/usr/bin/env python3
"""
Test script for Vendor Onboarding and Dashboard Implementation
Tests the complete flow from registration to approval
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5001"

# Test data
VENDOR_DATA = {
    "email": f"testvendor_{int(time.time())}@test.com",
    "password": "Test@123",
    "name": "Test Vendor",
    "phone": "9999999999",
    "role": "vendor",
    "pincode": "12345"
}

ADMIN_DATA = {
    "email": "admin@homeservepro.com",
    "password": "admin123"
}

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_result(test_name, success, message=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if message:
        print(f"    {message}")

def test_vendor_registration():
    """Test 1: Register a new vendor"""
    print_section("TEST 1: Vendor Registration")
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", json=VENDOR_DATA)
        data = response.json()

        if data.get('success'):
            print_result("Vendor Registration", True, f"Vendor registered: {VENDOR_DATA['email']}")
            # Get token and user_id from response
            token = data.get('data', {}).get('access_token') or data.get('access_token')
            user_id = data.get('data', {}).get('user', {}).get('user_id') or data.get('user', {}).get('user_id')
            print(f"    Token: {token[:20] if token else 'None'}...")
            print(f"    User ID: {user_id}")
            return token, user_id
        else:
            print_result("Vendor Registration", False, data.get('message'))
            return None, None
    except Exception as e:
        print_result("Vendor Registration", False, str(e))
        return None, None

def test_vendor_dashboard_access(token):
    """Test 2: Access vendor dashboard immediately after registration"""
    print_section("TEST 2: Vendor Dashboard Access")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/vendor/dashboard", headers=headers)
        data = response.json()
        
        if data.get('success'):
            vendor_info = data.get('vendor_info', {})
            print_result("Dashboard Access", True)
            print(f"    Status: {vendor_info.get('status')}")
            print(f"    Is Approved: {vendor_info.get('is_approved')}")
            print(f"    Documents Verified: {vendor_info.get('documents_verified')}")
            print(f"    Payouts Enabled: {vendor_info.get('payouts_enabled')}")
            return vendor_info
        else:
            print_result("Dashboard Access", False, data.get('message'))
            return None
    except Exception as e:
        print_result("Dashboard Access", False, str(e))
        return None

def test_verify_profile(token):
    """Test 3: Submit verification documents"""
    print_section("TEST 3: Submit Verification Documents")
    
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        documents = {
            "id_proof": "https://example.com/id_proof.pdf",
            "business_license": "https://example.com/business_license.pdf",
            "service_certification": "https://example.com/certification.pdf"
        }
        payload = {"documents": documents}
        
        response = requests.post(f"{BASE_URL}/api/vendor/verify_profile", 
                                headers=headers, json=payload)
        data = response.json()
        
        if data.get('success'):
            print_result("Document Submission", True, "Documents submitted successfully")
            return True
        else:
            print_result("Document Submission", False, data.get('message'))
            return False
    except Exception as e:
        print_result("Document Submission", False, str(e))
        return False

def test_create_service_before_approval(token):
    """Test 4: Try to create service before approval (should fail)"""
    print_section("TEST 4: Create Service Before Approval (Should Fail)")
    
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        service_data = {
            "name": "Emergency Plumbing",
            "category": "Plumbing",
            "price": 500,
            "duration": 60,
            "description": "24/7 emergency plumbing service",
            "availability": True
        }
        
        response = requests.post(f"{BASE_URL}/api/vendor/services/create", 
                                headers=headers, json=service_data)
        data = response.json()
        
        if not data.get('success') and response.status_code == 403:
            print_result("Service Creation Blocked", True, "Correctly blocked unapproved vendor")
            return True
        else:
            print_result("Service Creation Blocked", False, "Should have been blocked")
            return False
    except Exception as e:
        print_result("Service Creation Blocked", False, str(e))
        return False

def test_admin_login():
    """Test 5: Admin login"""
    print_section("TEST 5: Admin Login")
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_DATA)
        data = response.json()
        
        if data.get('success'):
            print_result("Admin Login", True, "Admin logged in successfully")
            return data.get('access_token')
        else:
            print_result("Admin Login", False, data.get('message'))
            return None
    except Exception as e:
        print_result("Admin Login", False, str(e))
        return None

def test_get_verification_requests(admin_token):
    """Test 6: Get vendor verification requests"""
    print_section("TEST 6: Get Verification Requests")
    
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/onboard_manager/vendor_verification_requests", 
                               headers=headers)
        data = response.json()
        
        if data.get('success'):
            requests_list = data.get('data', [])
            print_result("Get Verification Requests", True, f"Found {len(requests_list)} requests")
            if requests_list:
                print(f"    Latest request: {requests_list[0].get('vendor_info', {}).get('name')}")
            return requests_list
        else:
            print_result("Get Verification Requests", False, data.get('message'))
            return []
    except Exception as e:
        print_result("Get Verification Requests", False, str(e))
        return []

def test_approve_vendor(admin_token, vendor_id):
    """Test 7: Approve vendor"""
    print_section("TEST 7: Approve Vendor")
    
    try:
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        payload = {"notes": "All documents verified - Test approval"}
        
        response = requests.post(f"{BASE_URL}/api/onboard_manager/vendors/{vendor_id}/approve", 
                                headers=headers, json=payload)
        data = response.json()
        
        if data.get('success'):
            print_result("Vendor Approval", True, "Vendor approved successfully")
            return True
        else:
            print_result("Vendor Approval", False, data.get('message'))
            return False
    except Exception as e:
        print_result("Vendor Approval", False, str(e))
        return False

def test_vendor_dashboard_after_approval(token):
    """Test 8: Check vendor dashboard after approval"""
    print_section("TEST 8: Vendor Dashboard After Approval")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/vendor/dashboard", headers=headers)
        data = response.json()
        
        if data.get('success'):
            vendor_info = data.get('vendor_info', {})
            is_approved = vendor_info.get('is_approved')
            docs_verified = vendor_info.get('documents_verified')
            payouts_enabled = vendor_info.get('payouts_enabled')
            
            all_flags_set = is_approved and docs_verified and payouts_enabled
            
            print_result("Dashboard After Approval", all_flags_set)
            print(f"    Status: {vendor_info.get('status')}")
            print(f"    Is Approved: {is_approved}")
            print(f"    Documents Verified: {docs_verified}")
            print(f"    Payouts Enabled: {payouts_enabled}")
            
            return all_flags_set
        else:
            print_result("Dashboard After Approval", False, data.get('message'))
            return False
    except Exception as e:
        print_result("Dashboard After Approval", False, str(e))
        return False

def test_create_service_after_approval(token):
    """Test 9: Create service after approval (should succeed)"""
    print_section("TEST 9: Create Service After Approval")
    
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        service_data = {
            "name": "Emergency Plumbing",
            "category": "Plumbing",
            "price": 500,
            "duration": 60,
            "description": "24/7 emergency plumbing service",
            "availability": True
        }
        
        response = requests.post(f"{BASE_URL}/api/vendor/services/create", 
                                headers=headers, json=service_data)
        data = response.json()
        
        if data.get('success'):
            print_result("Service Creation", True, "Service created successfully")
            return True
        else:
            print_result("Service Creation", False, data.get('message'))
            return False
    except Exception as e:
        print_result("Service Creation", False, str(e))
        return False

def main():
    print("\n" + "🚀 "*20)
    print("VENDOR ONBOARDING & DASHBOARD TEST SUITE")
    print("🚀 "*20)
    
    # Test 1: Register vendor
    vendor_token, vendor_id = test_vendor_registration()
    if not vendor_token:
        print("\n❌ Cannot proceed without vendor token")
        return
    
    time.sleep(1)
    
    # Test 2: Access dashboard
    vendor_info = test_vendor_dashboard_access(vendor_token)
    if not vendor_info:
        print("\n❌ Cannot proceed without dashboard access")
        return
    
    time.sleep(1)
    
    # Test 3: Submit verification documents
    test_verify_profile(vendor_token)
    time.sleep(1)
    
    # Test 4: Try to create service before approval
    test_create_service_before_approval(vendor_token)
    time.sleep(1)
    
    # Test 5: Admin login
    admin_token = test_admin_login()
    if not admin_token:
        print("\n❌ Cannot proceed without admin token")
        return
    
    time.sleep(1)
    
    # Test 6: Get verification requests
    verification_requests = test_get_verification_requests(admin_token)
    time.sleep(1)
    
    # Test 7: Approve vendor
    if vendor_id:
        test_approve_vendor(admin_token, vendor_id)
        time.sleep(2)  # Wait for approval to process
    
    # Test 8: Check dashboard after approval
    test_vendor_dashboard_after_approval(vendor_token)
    time.sleep(1)
    
    # Test 9: Create service after approval
    test_create_service_after_approval(vendor_token)
    
    print("\n" + "🎉 "*20)
    print("TEST SUITE COMPLETED!")
    print("🎉 "*20 + "\n")

if __name__ == "__main__":
    main()

