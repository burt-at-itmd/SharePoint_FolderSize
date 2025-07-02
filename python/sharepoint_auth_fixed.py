#!/usr/bin/env python3
"""
Fixed SharePoint authentication implementation
"""

import requests
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.runtime.auth.providers.acs_token_provider import ACSTokenProvider
from office365.runtime.http.request_options import RequestOptions


class AppOnlyAuthenticationProvider(object):
    """App-only authentication provider for SharePoint"""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._cached_token = None
        
    def authenticate_request(self, request):
        """Authenticate the request with bearer token"""
        if self._cached_token is None:
            self._acquire_token()
        request.set_header('Authorization', f'Bearer {self._cached_token}')
        
    def _acquire_token(self):
        """Acquire access token using client credentials"""
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        # Extract tenant name from any SharePoint URL
        tenant_name = "auroraexpeditions"  # Hardcoded for now
        
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': f'https://{tenant_name}.sharepoint.com/.default'
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self._cached_token = token_data['access_token']
        
    def get_authorization_header(self):
        """Get the authorization header"""
        if self._cached_token is None:
            self._acquire_token()
        return f'Bearer {self._cached_token}'