#!/usr/bin/env python3
"""
SharePoint Folder Size Calculator v2
Direct REST API implementation for better control and reliability
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


class SharePointClient:
    """SharePoint REST API client with app-only authentication"""
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, site_url: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.site_url = site_url.rstrip('/')
        self.access_token = None
        self.headers = {
            'Accept': 'application/json;odata=verbose',
            'Content-Type': 'application/json;odata=verbose'
        }
        
    def authenticate(self) -> bool:
        """Authenticate and get access token"""
        print("\n" + "="*50)
        print("AUTHENTICATING")
        print("="*50)
        
        # Extract SharePoint resource
        # For SharePoint, we need to use the SharePoint resource ID
        sharepoint_resource = "00000003-0000-0ff1-ce00-000000000000"
        tenant_name = self.site_url.split('.sharepoint.com')[0].split('//')[-1]
        resource = f"{sharepoint_resource}/{tenant_name}.sharepoint.com@{self.tenant_id}"
        
        # SharePoint app-only token endpoint
        token_url = f"https://accounts.accesscontrol.windows.net/{self.tenant_id}/tokens/OAuth/2"
        
        # Request body for SharePoint app-only
        data = {
            'grant_type': 'client_credentials',
            'client_id': f"{self.client_id}@{self.tenant_id}",
            'client_secret': self.client_secret,
            'resource': resource
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
                
                # Test connection
                test_url = f"{self.site_url}/_api/web"
                test_response = requests.get(test_url, headers=self.headers)
                
                if test_response.status_code == 200:
                    web_data = test_response.json()
                    site_title = web_data.get('d', {}).get('Title', 'Unknown')
                    print(f"✓ Connected to: {site_title}")
                    print("="*50 + "\n")
                    return True
                else:
                    print(f"✗ Failed to connect to site: {test_response.status_code}")
                    print(f"Response: {test_response.text}")
                    return False
                    
            else:
                print("✗ No access token received")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Authentication error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return False
            
    def get_folder_items(self, folder_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Get files and folders in a specific folder"""
        # Encode the folder path
        encoded_path = quote(folder_path)
        
        # Get files
        files_url = f"{self.site_url}/_api/web/GetFolderByServerRelativeUrl('{encoded_path}')/Files"
        files_response = requests.get(files_url, headers=self.headers)
        
        files = []
        if files_response.status_code == 200:
            files_data = files_response.json()
            files = files_data.get('d', {}).get('results', [])
        
        # Get folders
        folders_url = f"{self.site_url}/_api/web/GetFolderByServerRelativeUrl('{encoded_path}')/Folders"
        folders_response = requests.get(folders_url, headers=self.headers)
        
        folders = []
        if folders_response.status_code == 200:
            folders_data = folders_response.json()
            folders = folders_data.get('d', {}).get('results', [])
            # Filter out system folders
            folders = [f for f in folders if not f['Name'].startswith('_') and f['Name'] != 'Forms']
        
        return files, folders
        
    def calculate_folder_size(self, folder_path: str, depth: int = 0) -> Dict[str, Any]:
        """Calculate folder size recursively"""
        indent = "  " * depth
        print(f"{indent}📁 Analyzing: {folder_path}")
        
        result = {
            'path': folder_path,
            'name': os.path.basename(folder_path) or 'Root',
            'total_size': 0,
            'file_count': 0,
            'folder_count': 0,
            'files': [],
            'subfolders': []
        }
        
        try:
            files, folders = self.get_folder_items(folder_path)
            
            # Process files
            for file in files:
                file_info = {
                    'name': file.get('Name', ''),
                    'size': file.get('Length', 0),
                    'last_modified': file.get('TimeLastModified', ''),
                    'path': file.get('ServerRelativeUrl', '')
                }
                result['files'].append(file_info)
                result['total_size'] += file_info['size']
                result['file_count'] += 1
                
                size_str = self.format_size(file_info['size'])
                print(f"{indent}  📄 {file_info['name']} ({size_str})")
            
            # Process subfolders
            for folder in folders:
                folder_path = folder.get('ServerRelativeUrl', '')
                result['folder_count'] += 1
                
                # Recursively process subfolder
                subfolder_result = self.calculate_folder_size(folder_path, depth + 1)
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
    
    def __init__(self, client: SharePointClient):
        self.client = client
        
    def analyze_folder(self, folder_path: str) -> Optional[Dict[str, Any]]:
        """Analyze a folder and return size information"""
        print(f"\n🔍 Starting folder analysis: {folder_path}")
        start_time = time.time()
        
        result = self.client.calculate_folder_size(folder_path)
        
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
        print(f"Path: {result['path']}")
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
        description='Calculate SharePoint folder sizes using REST API'
    )
    parser.add_argument('--tenant-id', required=True, help='Azure AD tenant ID')
    parser.add_argument('--client-id', required=True, help='Azure AD application client ID')
    parser.add_argument('--client-secret', help='Azure AD application client secret')
    parser.add_argument('--site-url', required=True, help='SharePoint site URL')
    parser.add_argument('--folder-path', required=True, help='Folder path to analyze')
    parser.add_argument('--output-csv', default='folder_sizes.csv', help='Output CSV filename')
    parser.add_argument('--output-json', default='folder_sizes.json', help='Output JSON filename')
    
    args = parser.parse_args()
    
    print("\n🚀 SharePoint Folder Size Calculator v2")
    print("=" * 60)
    
    # Check for client secret in environment if not provided
    client_secret = args.client_secret or os.environ.get('CLIENT_SECRET')
    
    if not client_secret:
        print("✗ Client secret not provided")
        sys.exit(1)
    
    # Create client
    client = SharePointClient(
        tenant_id=args.tenant_id,
        client_id=args.client_id,
        client_secret=client_secret,
        site_url=args.site_url
    )
    
    # Authenticate
    if not client.authenticate():
        print("✗ Authentication failed. Exiting.")
        sys.exit(1)
    
    # Create calculator
    calculator = FolderSizeCalculator(client)
    
    # Analyze folder
    result = calculator.analyze_folder(args.folder_path)
    
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