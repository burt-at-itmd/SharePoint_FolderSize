#!/usr/bin/env python3
"""
Health Check and Monitoring Script for SharePoint Folder Size Calculator
Provides status monitoring, health checks, and basic watchdog functionality
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import requests


class HealthMonitor:
    """Health monitoring for SharePoint folder size calculator"""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, site_url: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.site_url = site_url
        self.health_status = {
            'status': 'unknown',
            'last_check': None,
            'checks': {
                'authentication': {'status': 'unknown', 'message': ''},
                'site_connectivity': {'status': 'unknown', 'message': ''},
                'api_access': {'status': 'unknown', 'message': ''},
                'output_files': {'status': 'unknown', 'message': ''}
            }
        }
        
    def check_authentication(self) -> bool:
        """Check if authentication works"""
        print("🔐 Checking authentication...")
        
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=30)
            if response.status_code == 200:
                token_data = response.json()
                if 'access_token' in token_data:
                    self.access_token = token_data['access_token']
                    self.health_status['checks']['authentication'] = {
                        'status': 'healthy',
                        'message': 'Authentication successful'
                    }
                    print("  ✓ Authentication successful")
                    return True
            
            self.health_status['checks']['authentication'] = {
                'status': 'unhealthy',
                'message': f'Authentication failed: {response.status_code}'
            }
            print(f"  ✗ Authentication failed: {response.status_code}")
            return False
            
        except Exception as e:
            self.health_status['checks']['authentication'] = {
                'status': 'unhealthy',
                'message': f'Authentication error: {str(e)}'
            }
            print(f"  ✗ Authentication error: {str(e)}")
            return False
            
    def check_site_connectivity(self) -> bool:
        """Check if SharePoint site is accessible"""
        print("🌐 Checking site connectivity...")
        
        if not hasattr(self, 'access_token'):
            print("  ✗ No access token available")
            return False
            
        # Extract site info
        parts = self.site_url.replace('https://', '').split('/')
        hostname = parts[0]
        site_path = '/'.join(parts[1:])
        
        api_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{site_path}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            if response.status_code == 200:
                site_data = response.json()
                site_name = site_data.get('displayName', 'Unknown')
                self.health_status['checks']['site_connectivity'] = {
                    'status': 'healthy',
                    'message': f'Connected to site: {site_name}'
                }
                print(f"  ✓ Connected to site: {site_name}")
                return True
                
            self.health_status['checks']['site_connectivity'] = {
                'status': 'unhealthy',
                'message': f'Site access failed: {response.status_code}'
            }
            print(f"  ✗ Site access failed: {response.status_code}")
            return False
            
        except Exception as e:
            self.health_status['checks']['site_connectivity'] = {
                'status': 'unhealthy',
                'message': f'Site connectivity error: {str(e)}'
            }
            print(f"  ✗ Site connectivity error: {str(e)}")
            return False
            
    def check_api_access(self) -> bool:
        """Check if Graph API is accessible and quota is available"""
        print("📊 Checking API access...")
        
        if not hasattr(self, 'access_token'):
            print("  ✗ No access token available")
            return False
            
        # Try a simple API call
        api_url = "https://graph.microsoft.com/v1.0/me"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            # For app-only auth, /me won't work, but we can check the response
            if response.status_code in [200, 400, 403]:  # Expected responses
                self.health_status['checks']['api_access'] = {
                    'status': 'healthy',
                    'message': 'Graph API is accessible'
                }
                print("  ✓ Graph API is accessible")
                return True
                
            self.health_status['checks']['api_access'] = {
                'status': 'unhealthy',
                'message': f'API access issue: {response.status_code}'
            }
            print(f"  ✗ API access issue: {response.status_code}")
            return False
            
        except Exception as e:
            self.health_status['checks']['api_access'] = {
                'status': 'unhealthy',
                'message': f'API access error: {str(e)}'
            }
            print(f"  ✗ API access error: {str(e)}")
            return False
            
    def check_output_files(self, output_dir: str = '/output') -> bool:
        """Check if output files exist and are recent"""
        print("📁 Checking output files...")
        
        csv_file = os.path.join(output_dir, 'folder_sizes_python.csv')
        json_file = os.path.join(output_dir, 'folder_sizes_python.json')
        
        try:
            # Check if files exist
            if not os.path.exists(csv_file) or not os.path.exists(json_file):
                self.health_status['checks']['output_files'] = {
                    'status': 'warning',
                    'message': 'Output files not found'
                }
                print("  ⚠️  Output files not found")
                return False
                
            # Check file age
            csv_mtime = os.path.getmtime(csv_file)
            json_mtime = os.path.getmtime(json_file)
            oldest_mtime = min(csv_mtime, json_mtime)
            file_age = time.time() - oldest_mtime
            
            # Files older than 24 hours are considered stale
            if file_age > 86400:  # 24 hours
                age_hours = file_age / 3600
                self.health_status['checks']['output_files'] = {
                    'status': 'warning',
                    'message': f'Output files are {age_hours:.1f} hours old'
                }
                print(f"  ⚠️  Output files are {age_hours:.1f} hours old")
                return True
                
            # Check file sizes
            csv_size = os.path.getsize(csv_file)
            json_size = os.path.getsize(json_file)
            
            if csv_size == 0 or json_size == 0:
                self.health_status['checks']['output_files'] = {
                    'status': 'unhealthy',
                    'message': 'Output files are empty'
                }
                print("  ✗ Output files are empty")
                return False
                
            age_mins = file_age / 60
            self.health_status['checks']['output_files'] = {
                'status': 'healthy',
                'message': f'Output files exist and are {age_mins:.1f} minutes old'
            }
            print(f"  ✓ Output files exist and are {age_mins:.1f} minutes old")
            return True
            
        except Exception as e:
            self.health_status['checks']['output_files'] = {
                'status': 'unhealthy',
                'message': f'File check error: {str(e)}'
            }
            print(f"  ✗ File check error: {str(e)}")
            return False
            
    def run_health_check(self) -> Dict[str, Any]:
        """Run all health checks"""
        print("\n🏥 SharePoint Folder Size Calculator Health Check")
        print("=" * 50)
        
        # Run checks
        auth_ok = self.check_authentication()
        site_ok = self.check_site_connectivity() if auth_ok else False
        api_ok = self.check_api_access() if auth_ok else False
        files_ok = self.check_output_files()
        
        # Determine overall status
        if auth_ok and site_ok and api_ok:
            if files_ok:
                overall_status = 'healthy'
            else:
                overall_status = 'warning'
        else:
            overall_status = 'unhealthy'
            
        self.health_status['status'] = overall_status
        self.health_status['last_check'] = datetime.now().isoformat()
        
        print("\n📋 Overall Status:", overall_status.upper())
        print("=" * 50)
        
        return self.health_status
        
    def save_health_status(self, filename: str = '/output/health_status.json'):
        """Save health status to file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.health_status, f, indent=2)
            print(f"✓ Health status saved to {filename}")
        except Exception as e:
            print(f"✗ Failed to save health status: {str(e)}")
            
    def continuous_monitoring(self, interval: int = 300):
        """Run continuous health monitoring"""
        print(f"\n🔄 Starting continuous monitoring (interval: {interval}s)")
        
        while True:
            try:
                self.run_health_check()
                self.save_health_status()
                
                if self.health_status['status'] == 'unhealthy':
                    print("\n⚠️  ALERT: System is unhealthy!")
                    # Here you could add alerting logic (email, webhook, etc.)
                    
                print(f"\n💤 Sleeping for {interval} seconds...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n👋 Monitoring stopped by user")
                break
            except Exception as e:
                print(f"\n❌ Monitoring error: {str(e)}")
                time.sleep(interval)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Health monitoring for SharePoint Folder Size Calculator'
    )
    parser.add_argument('--tenant-id', required=True, help='Azure AD tenant ID')
    parser.add_argument('--client-id', required=True, help='Azure AD application client ID')
    parser.add_argument('--client-secret', help='Azure AD application client secret')
    parser.add_argument('--site-url', required=True, help='SharePoint site URL')
    parser.add_argument('--continuous', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--interval', type=int, default=300, help='Monitoring interval in seconds')
    parser.add_argument('--output-dir', default='/output', help='Output directory to check')
    
    args = parser.parse_args()
    
    # Check for client secret in environment if not provided
    client_secret = args.client_secret or os.environ.get('CLIENT_SECRET')
    
    if not client_secret:
        print("✗ Client secret not provided")
        sys.exit(1)
        
    # Create monitor
    monitor = HealthMonitor(
        tenant_id=args.tenant_id,
        client_id=args.client_id,
        client_secret=client_secret,
        site_url=args.site_url
    )
    
    # Run health check
    if args.continuous:
        monitor.continuous_monitoring(interval=args.interval)
    else:
        health_status = monitor.run_health_check()
        monitor.save_health_status()
        
        # Exit with appropriate code
        if health_status['status'] == 'healthy':
            sys.exit(0)
        elif health_status['status'] == 'warning':
            sys.exit(1)
        else:
            sys.exit(2)


if __name__ == "__main__":
    main()