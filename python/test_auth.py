#!/usr/bin/env python3
"""Test authentication methods for SharePoint"""

import os
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.client_credential import ClientCredential

# Get credentials from environment
tenant_id = os.environ.get('TENANT_ID')
client_id = os.environ.get('CLIENT_ID')
client_secret = os.environ.get('CLIENT_SECRET')
site_url = os.environ.get('SITE_URL')

print(f"Tenant ID: {tenant_id}")
print(f"Client ID: {client_id}")
print(f"Site URL: {site_url}")
print(f"Client Secret: {'*' * 10}")

# Test direct ClientCredential approach
print("\nTesting direct ClientCredential approach...")
try:
    ctx = ClientContext(site_url).with_credentials(
        ClientCredential(client_id, client_secret)
    )
    
    # Try to access the web
    web = ctx.web
    ctx.load(web)
    ctx.execute_query()
    
    print(f"✓ Success! Connected to: {web.properties['Title']}")
    print(f"Web URL: {web.properties['Url']}")
    
except Exception as e:
    print(f"✗ Failed: {str(e)}")
    print(f"Error type: {type(e).__name__}")