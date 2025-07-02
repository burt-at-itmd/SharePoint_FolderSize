#!/usr/bin/env python3
"""
SharePoint Folder Size Calculator using Microsoft Graph API
This approach uses Microsoft Graph API which has better app-only support
"""

import os
import sys
import json
import csv
import argparse
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import requests
from urllib.parse import quote


class GraphClient:
    """Microsoft Graph API client for SharePoint access"""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
    def authenticate(self) -> bool:
        """Authenticate and get access token"""
        print("\n" + "="*50)
        print("AUTHENTICATING WITH MICROSOFT GRAPH")
        print("="*50)
        
        # Token endpoint
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        # Request body for Graph API
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        
        try:
            print("Requesting access token...")
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            
            if self.access_token:
                self.headers['Authorization'] = f'Bearer {self.access_token}'
                print("✓ Authentication successful!")
                return True
            else:
                print("✗ No access token received")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Authentication error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return False
            
    def get_site_id(self, site_url: str) -> Optional[str]:
        """Get the site ID from the site URL"""
        # Extract site path from URL
        # https://auroraexpeditions.sharepoint.com/sites/APACSales
        parts = site_url.replace('https://', '').split('/')
        hostname = parts[0]  # auroraexpeditions.sharepoint.com
        site_path = '/'.join(parts[1:])  # sites/APACSales
        
        # Graph API endpoint to get site
        api_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{site_path}"
        
        try:
            response = requests.get(api_url, headers=self.headers)
            if response.status_code == 200:
                site_data = response.json()
                site_id = site_data.get('id')
                site_name = site_data.get('displayName', 'Unknown')
                print(f"✓ Connected to site: {site_name}")
                return site_id
            else:
                print(f"✗ Failed to get site: {response.status_code}")
                print(f"Response: {response.text}")
                return None
        except Exception as e:
            print(f"✗ Error getting site: {str(e)}")
            return None
            
    def get_drive_id(self, site_id: str) -> Optional[str]:
        """Get the default document library drive ID"""
        api_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
        
        try:
            response = requests.get(api_url, headers=self.headers)
            if response.status_code == 200:
                drives_data = response.json()
                drives = drives_data.get('value', [])
                
                # Find the default document library (usually "Documents" or "Shared Documents")
                for drive in drives:
                    if drive.get('name') in ['Documents', 'Shared Documents']:
                        return drive.get('id')
                
                # If not found, return the first drive
                if drives:
                    return drives[0].get('id')
                    
            return None
        except Exception as e:
            print(f"✗ Error getting drives: {str(e)}")
            return None
            
    def get_folder_items(self, site_id: str, drive_id: str, folder_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Get items in a folder using Graph API"""
        # Clean folder path
        if folder_path.startswith('/sites/'):
            # Remove the site prefix
            parts = folder_path.split('/')
            folder_path = '/'.join(parts[3:]) if len(parts) > 3 else ''
        
        # Build API URL
        if folder_path and folder_path not in ['/', '', 'Shared Documents']:
            api_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{folder_path}:/children"
        else:
            # For root or empty path, get root children
            api_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children"
        
        files = []
        folders = []
        
        try:
            # Get all items with pagination
            while api_url:
                # print(f"Debug: Calling API: {api_url}")
                response = requests.get(api_url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('value', [])
                    
                    for item in items:
                        if 'folder' in item:
                            folders.append(item)
                        elif 'file' in item:
                            files.append(item)
                    
                    # Check for next page
                    api_url = data.get('@odata.nextLink')
                else:
                    print(f"✗ Failed to get folder items: {response.status_code}")
                    print(f"Response: {response.text}")
                    break
                    
        except Exception as e:
            print(f"✗ Error getting folder items: {str(e)}")
            
        return files, folders
        
    def calculate_folder_size(self, site_id: str, drive_id: str, folder_path: str, folder_name: str = None, depth: int = 0) -> Dict[str, Any]:
        """Calculate folder size recursively"""
        indent = "  " * depth
        display_name = folder_name or os.path.basename(folder_path) or 'Root'
        print(f"{indent}📁 {display_name}")
        
        result = {
            'path': folder_path,
            'name': display_name,
            'total_size': 0,
            'file_count': 0,
            'folder_count': 0,
            'files': [],
            'subfolders': []
        }
        
        try:
            files, folders = self.get_folder_items(site_id, drive_id, folder_path)
            
            # Process files
            for file in files:
                file_info = {
                    'name': file.get('name', ''),
                    'size': file.get('size', 0),
                    'last_modified': file.get('lastModifiedDateTime', ''),
                    'path': file.get('webUrl', '')
                }
                result['files'].append(file_info)
                result['total_size'] += file_info['size']
                result['file_count'] += 1
                
                size_str = self.format_size(file_info['size'])
                print(f"{indent}  📄 {file_info['name']} ({size_str})")
            
            # Process subfolders
            for folder in folders:
                folder_name = folder.get('name', '')
                # Skip system folders
                if folder_name.startswith('_') or folder_name == 'Forms':
                    continue
                    
                result['folder_count'] += 1
                
                # Build subfolder path - just use the folder name since we're at root
                subfolder_path = folder_name
                
                # Recursively process subfolder
                subfolder_result = self.calculate_folder_size(
                    site_id, drive_id, subfolder_path, folder_name, depth + 1
                )
                result['subfolders'].append(subfolder_result)
                
                # Add subfolder totals to parent
                result['total_size'] += subfolder_result['total_size']
                result['file_count'] += subfolder_result['file_count']
                result['folder_count'] += subfolder_result['folder_count']
                
        except Exception as e:
            print(f"{indent}✗ Error processing folder: {str(e)}")
            
        return result
        
    def format_size(self, size_in_bytes: int) -> str:
        """Convert bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.2f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.2f} PB"


class FolderSizeCalculator:
    """Main application class"""
    
    def __init__(self, client: GraphClient):
        self.client = client
        
    def analyze_site(self, site_url: str, folder_path: str) -> Optional[Dict[str, Any]]:
        """Analyze a folder in a SharePoint site"""
        # Get site ID
        site_id = self.client.get_site_id(site_url)
        if not site_id:
            print("✗ Failed to get site ID")
            return None
            
        # Get drive ID
        drive_id = self.client.get_drive_id(site_id)
        if not drive_id:
            print("✗ Failed to get document library")
            return None
            
        print(f"\n🔍 Starting folder analysis...")
        print("="*50)
        start_time = time.time()
        
        # Clean up folder path
        if folder_path.startswith('/sites/'):
            parts = folder_path.split('/')
            folder_path = '/'.join(parts[3:]) if len(parts) > 3 else ''
        
        result = self.client.calculate_folder_size(site_id, drive_id, folder_path)
        
        end_time = time.time()
        print(f"\n⏱️  Analysis completed in {end_time - start_time:.2f} seconds")
        
        return result
        
    def print_summary(self, result: Dict[str, Any]):
        """Print analysis summary"""
        if not result:
            return
            
        print("\n" + "="*60)
        print("FOLDER SIZE SUMMARY")
        print("="*60)
        print(f"Folder: {result['name']}")
        print(f"Total Size: {self.client.format_size(result['total_size'])} ({result['total_size']:,} bytes)")
        print(f"Files: {result['file_count']:,}")
        print(f"Folders: {result['folder_count']:,}")
        print("="*60)
        
        # Get top 10 largest files
        all_files = self._get_all_files(result)
        all_files.sort(key=lambda x: x['size'], reverse=True)
        
        if all_files:
            print("\nTop 10 Largest Files:")
            print("-" * 60)
            for i, file in enumerate(all_files[:10], 1):
                print(f"{i:2d}. {file['name']:40s} {self.client.format_size(file['size']):>10s}")
                
    def _get_all_files(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all files recursively"""
        files = result['files'].copy()
        for subfolder in result['subfolders']:
            files.extend(self._get_all_files(subfolder))
        return files
        
    def export_to_csv(self, result: Dict[str, Any], filename: str):
        """Export results to CSV"""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Path', 'Name', 'Type', 'Size (bytes)', 'Size (formatted)', 'File Count', 'Folder Count'])
            
            def write_folder_data(folder_data: Dict[str, Any]):
                writer.writerow([
                    folder_data['path'],
                    folder_data['name'],
                    'Folder',
                    folder_data['total_size'],
                    self.client.format_size(folder_data['total_size']),
                    folder_data['file_count'],
                    folder_data['folder_count']
                ])
                
                # Write files
                for file in folder_data['files']:
                    writer.writerow([
                        file['path'],
                        file['name'],
                        'File',
                        file['size'],
                        self.client.format_size(file['size']),
                        0,
                        0
                    ])
                
                # Write subfolders
                for subfolder in folder_data['subfolders']:
                    write_folder_data(subfolder)
            
            write_folder_data(result)
        
        print(f"\n✓ Results exported to: {filename}")
        
    def export_to_json(self, result: Dict[str, Any], filename: str):
        """Export results to JSON"""
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(result, jsonfile, indent=2, default=str)
        
        print(f"✓ Results exported to: {filename}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Calculate SharePoint folder sizes using Microsoft Graph API'
    )
    parser.add_argument('--tenant-id', required=True, help='Azure AD tenant ID')
    parser.add_argument('--client-id', required=True, help='Azure AD application client ID')
    parser.add_argument('--client-secret', help='Azure AD application client secret')
    parser.add_argument('--site-url', required=True, help='SharePoint site URL')
    parser.add_argument('--folder-path', required=True, help='Folder path to analyze')
    parser.add_argument('--output-csv', default='folder_sizes.csv', help='Output CSV filename')
    parser.add_argument('--output-json', default='folder_sizes.json', help='Output JSON filename')
    
    args = parser.parse_args()
    
    print("\n🚀 SharePoint Folder Size Calculator (Graph API)")
    print("=" * 60)
    
    # Check for client secret in environment if not provided
    client_secret = args.client_secret or os.environ.get('CLIENT_SECRET')
    
    if not client_secret:
        print("✗ Client secret not provided")
        sys.exit(1)
    
    # Create client
    client = GraphClient(
        tenant_id=args.tenant_id,
        client_id=args.client_id,
        client_secret=client_secret
    )
    
    # Authenticate
    if not client.authenticate():
        print("✗ Authentication failed. Exiting.")
        sys.exit(1)
    
    # Create calculator
    calculator = FolderSizeCalculator(client)
    
    # Analyze folder
    result = calculator.analyze_site(args.site_url, args.folder_path)
    
    if result:
        calculator.print_summary(result)
        calculator.export_to_csv(result, args.output_csv)
        calculator.export_to_json(result, args.output_json)
        print("\n✅ Analysis complete!")
    else:
        print("\n❌ Failed to analyze folder.")
        sys.exit(1)


if __name__ == "__main__":
    main()