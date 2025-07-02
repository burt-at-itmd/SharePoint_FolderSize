#!/usr/bin/env python3
"""Test authentication with proper token acquisition"""

import os
import requests
from office365.sharepoint.client_context import ClientContext

# Get credentials
tenant_id = os.environ.get('TENANT_ID')
client_id = os.environ.get('CLIENT_ID')
client_secret = os.environ.get('CLIENT_SECRET')
site_url = os.environ.get('SITE_URL')

print("Testing OAuth2 token acquisition...")

# Step 1: Get access token
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
tenant_name = site_url.split('.sharepoint.com')[0].split('//')[1]  # Extract tenant name

# Try different scopes
scopes_to_try = [
    f"https://{tenant_name}.sharepoint.com/.default",
    "https://graph.microsoft.com/.default",
    f"{site_url}/.default"
]

for scope in scopes_to_try:
    print(f"\nTrying scope: {scope}")
    
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': scope
    }
    
    try:
        response = requests.post(token_url, data=data)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            token_type = token_data.get('token_type', 'Bearer')
            
            print("✓ Token acquired successfully!")
            
            # Test the token with SharePoint
            ctx = ClientContext(site_url)
            ctx.with_access_token(access_token)
            
            web = ctx.web
            ctx.load(web)
            ctx.execute_query()
            
            print(f"✓ Connected to SharePoint: {web.properties.get('Title', 'Unknown')}")
            print(f"Success with scope: {scope}")
            break
            
        else:
            print(f"✗ Token request failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"✗ Error: {str(e)}")