#!/usr/bin/env python3
"""
SharePoint Folder Size Calculator - Final Working Version
Uses Microsoft Graph API with proper folder path handling
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
            
    def get_site_and_drive(self, site_url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Get the site ID and document library drive ID"""
        # Extract site path from URL
        parts = site_url.replace('https://', '').split('/')
        hostname = parts[0]
        site_path = '/'.join(parts[1:])
        
        # Get site
        api_url = f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{site_path}"
        
        try:
            response = requests.get(api_url, headers=self.headers)
            if response.status_code == 200:
                site_data = response.json()
                site_id = site_data.get('id')
                site_name = site_data.get('displayName', 'Unknown')
                print(f"✓ Connected to site: {site_name}")
                
                # Get drives
                drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
                drives_response = requests.get(drives_url, headers=self.headers)
                
                if drives_response.status_code == 200:
                    drives_data = drives_response.json()
                    drives = drives_data.get('value', [])
                    
                    # Find the document library
                    for drive in drives:
                        if drive.get('name') in ['Documents', 'Shared Documents']:
                            return site_id, drive.get('id'), drive.get('name')
                    
                    # Return first drive if specific one not found
                    if drives:
                        return site_id, drives[0].get('id'), drives[0].get('name')
                        
            return None, None, None
        except Exception as e:
            print(f"✗ Error getting site: {str(e)}")
            return None, None, None
            
    def get_drive_item_by_path(self, site_id: str, drive_id: str, item_path: str) -> Optional[Dict]:
        """Get a drive item (file or folder) by its path"""
        if not item_path or item_path == '/':
            # Root folder
            api_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root"
        else:
            # Specific path
            encoded_path = quote(item_path)
            api_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{encoded_path}"
            
        try:
            response = requests.get(api_url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
            
    def get_folder_children(self, site_id: str, drive_id: str, folder_id: str) -> Tuple[List[Dict], List[Dict]]:
        """Get children of a folder using its ID"""
        api_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{folder_id}/children"
        
        files = []
        folders = []
        
        try:
            # Handle pagination
            while api_url:
                response = requests.get(api_url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('value', [])
                    
                    for item in items:
                        if 'folder' in item:
                            # Skip system folders
                            if not (item['name'].startswith('_') or item['name'] == 'Forms'):
                                folders.append(item)
                        elif 'file' in item:
                            files.append(item)
                    
                    # Check for next page
                    api_url = data.get('@odata.nextLink')
                else:
                    break
                    
        except Exception as e:
            print(f"  ✗ Error getting folder items: {str(e)}")
            
        return files, folders
        
    def calculate_folder_size(self, site_id: str, drive_id: str, folder_item: Dict, depth: int = 0) -> Dict[str, Any]:
        """Calculate folder size recursively using folder item"""
        indent = "  " * depth
        folder_name = folder_item.get('name', 'Unknown')
        folder_id = folder_item.get('id')
        
        print(f"{indent}📁 {folder_name}")
        
        result = {
            'id': folder_id,
            'path': folder_item.get('webUrl', ''),
            'name': folder_name,
            'total_size': 0,
            'file_count': 0,
            'folder_count': 0,
            'files': [],
            'subfolders': []
        }
        
        if not folder_id:
            return result
            
        try:
            files, folders = self.get_folder_children(site_id, drive_id, folder_id)
            
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
            result['folder_count'] = len(folders)
            for folder in folders:
                # Recursively process subfolder
                subfolder_result = self.calculate_folder_size(
                    site_id, drive_id, folder, depth + 1
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
        # Get site and drive IDs
        site_id, drive_id, drive_name = self.client.get_site_and_drive(site_url)
        if not site_id or not drive_id:
            print("✗ Failed to get site or document library")
            return None
            
        print(f"✓ Using document library: {drive_name}")
        
        # Clean up folder path
        if folder_path:
            # Remove site prefix if present
            if folder_path.startswith('/sites/'):
                parts = folder_path.split('/')
                folder_path = '/'.join(parts[3:]) if len(parts) > 3 else ''
            
            # Remove leading/trailing slashes
            folder_path = folder_path.strip('/')
            
        print(f"\n🔍 Starting folder analysis...")
        print("="*50)
        start_time = time.time()
        
        # Get the folder item
        if not folder_path or folder_path in ['', 'Shared Documents', 'Documents']:
            # Analyze root of document library
            folder_item = self.client.get_drive_item_by_path(site_id, drive_id, '')
        else:
            # Specific folder
            folder_item = self.client.get_drive_item_by_path(site_id, drive_id, folder_path)
            
        if not folder_item:
            print(f"✗ Folder not found: {folder_path}")
            return None
            
        # Calculate folder size
        result = self.client.calculate_folder_size(site_id, drive_id, folder_item)
        
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
    
    print("\n🚀 SharePoint Folder Size Calculator")
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