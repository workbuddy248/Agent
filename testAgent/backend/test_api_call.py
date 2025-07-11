#!/usr/bin/env python3
"""
Test script to simulate the API call that's failing
File: test_api_call.py
"""

import asyncio
import requests
import json

def test_parse_test_instructions_api():
    """Test the /parse_test_instructions endpoint"""
    
    # API endpoint
    url = "http://localhost:8000/parse_test_instructions"
    
    # Test data (same as from UI)
    test_data = {
        "prompt": "test login to the cluster",
        "url": "https://172.27.248.237:443/",
        "username": "admin1",
        "password": "password123"
    }
    
    print("Testing /parse_test_instructions API endpoint...")
    print("=" * 60)
    print(f"URL: {url}")
    print(f"Data: {json.dumps(test_data, indent=2)}")
    print("-" * 60)
    
    try:
        # Make the API call
        response = requests.post(url, json=test_data)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ API call successful!")
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print(f"✗ API call failed!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to the API. Make sure the backend is running on localhost:8000")
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")

if __name__ == "__main__":
    test_parse_test_instructions_api()