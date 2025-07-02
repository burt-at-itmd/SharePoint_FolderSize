# SharePoint Folder Size Calculator

A Docker-based solution to calculate folder sizes in SharePoint Online using Microsoft Graph API with app-only authentication. Available in both Python and Node.js implementations.

## Features

- **App-Only Authentication**: Uses Azure AD application credentials for unattended operation
- **Microsoft Graph API**: Reliable access using Microsoft's recommended API
- **Recursive Folder Analysis**: Calculates total size including all subfolders
- **Multiple Export Formats**: CSV and JSON output
- **Progress Tracking**: Real-time progress indicators
- **Top Files Report**: Shows the largest files in the analyzed folders
- **READ-ONLY Operations**: Only reads data, never modifies anything
- **Health Monitoring**: Built-in health checks and monitoring capabilities
- **Watchdog Service**: Automatic monitoring and restart functionality

## Prerequisites

- Docker and Docker Compose installed
- Azure AD Application with appropriate permissions
- Access to the SharePoint site you want to analyze

## Azure AD App Registration

Before using this tool, you need to register an application in Azure AD:

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to Azure Active Directory > App registrations
3. Click "New registration"
4. Configure the app:
   - Name: "SharePoint Folder Size Calculator"
   - Supported account types: "Accounts in this organizational directory only"
   - Redirect URI: Leave blank
5. After creation, note down:
   - **Application (client) ID**
   - **Directory (tenant) ID**
6. Create a client secret:
   - Go to "Certificates & secrets"
   - Click "New client secret"
   - Add a description and select expiry
   - **Copy the secret value immediately** (it won't be shown again)
7. Configure API permissions:
   - Click "API permissions" > "Add a permission"
   - Select "Microsoft Graph" > "Application permissions"
   - Add: Sites.Selected
   - Click "Grant admin consent"
8. Grant access to specific SharePoint site:
   - Use SharePoint Admin Center or PowerShell
   - Grant the app access to your specific site
   - See Microsoft documentation for Sites.Selected permission

## Quick Start

### Using Docker Compose

1. Clone this repository:
   ```bash
   cd sharepoint-folder-size
   ```

2. Create an `.env` file with your configuration:
   ```bash
   TENANT_ID=your-tenant-id
   CLIENT_ID=your-client-id
   CLIENT_SECRET=your-client-secret
   SITE_URL=https://yourtenant.sharepoint.com/sites/yoursite
   FOLDER_PATH=/Shared Documents/YourFolder
   ```

3. Build and run using Docker Compose:

   **For Python implementation:**
   ```bash
   docker-compose run --rm python
   ```

   **For Node.js implementation:**
   ```bash
   docker-compose run --rm nodejs
   ```

4. The application will automatically:
   - Authenticate using the provided credentials
   - Connect to your SharePoint site
   - Analyze the specified folder
   - Generate CSV and JSON reports

5. Results will be saved in the `output/` directory:
   - `folder_sizes_python.csv` - Tabular format
   - `folder_sizes_python.json` - Hierarchical format

### Using Docker Directly

**Python version:**
```bash
# Build
docker build -t sp-folder-size-python ./python

# Run
docker run -it --rm \
  -v $(pwd)/output:/output \
  sp-folder-size-python \
  python sharepoint_folder_size.py \
  --tenant-id "your-tenant-id" \
  --client-id "your-client-id" \
  --site-url "https://yourtenant.sharepoint.com/sites/yoursite" \
  --folder-path "/sites/yoursite/Shared Documents/YourFolder" \
  --output-csv /output/folder_sizes.csv \
  --output-json /output/folder_sizes.json
```

**Node.js version:**
```bash
# Build
docker build -t sp-folder-size-nodejs ./nodejs

# Run
docker run -it --rm \
  -v $(pwd)/output:/output \
  sp-folder-size-nodejs \
  node sharepoint-folder-size.js \
  --tenant-id "your-tenant-id" \
  --client-id "your-client-id" \
  --site-url "https://yourtenant.sharepoint.com/sites/yoursite" \
  --folder-path "/sites/yoursite/Shared Documents/YourFolder" \
  --output-csv /output/folder_sizes.csv \
  --output-json /output/folder_sizes.json
```

## Command Line Options

Both implementations support the same options:

| Option | Description | Required |
|--------|-------------|----------|
| `--tenant-id` | Azure AD tenant ID | Yes |
| `--client-id` | Azure AD application client ID | Yes |
| `--client-secret` | Azure AD application client secret | Yes |
| `--site-url` | SharePoint site URL | Yes |
| `--folder-path` | Path to the folder to analyze | Yes |
| `--output-csv` | Output CSV filename (default: folder_sizes.csv) | No |
| `--output-json` | Output JSON filename (default: folder_sizes.json) | No |

## Health Monitoring

The application includes comprehensive health monitoring capabilities:

### Running Health Checks

```bash
# One-time health check
docker-compose run --rm python python health_check.py \
  --tenant-id "$TENANT_ID" \
  --client-id "$CLIENT_ID" \
  --site-url "$SITE_URL"

# Continuous monitoring
docker-compose run --rm python python health_check.py \
  --tenant-id "$TENANT_ID" \
  --client-id "$CLIENT_ID" \
  --site-url "$SITE_URL" \
  --continuous
```

### Watchdog Service

The watchdog automatically monitors and reruns the application:

```bash
# Make executable
chmod +x watchdog.sh

# Run watchdog
./watchdog.sh
```

### Monitoring Dashboard

A web-based monitoring dashboard is available:

```bash
# Install Flask (if not in Docker)
pip install flask

# Start dashboard
python monitor_dashboard.py
```

Access at: http://localhost:5000

## Output Formats

### CSV Output
The CSV file contains:
- Path: Full path to the file/folder
- Name: File/folder name
- Type: "File" or "Folder"
- Size (bytes): Size in bytes
- Size (formatted): Human-readable size
- File Count: Number of files (for folders)
- Folder Count: Number of subfolders (for folders)

### JSON Output
The JSON file contains a hierarchical structure with:
- Complete folder tree
- File details including size and last modified date
- Aggregated statistics for each folder

### Console Output
The tool displays:
- Real-time progress during analysis
- Summary statistics
- Top 10 largest files
- Processing time

## Folder Path Examples

- Document Library root: `/sites/yoursite/Shared Documents`
- Specific folder: `/sites/yoursite/Shared Documents/Projects/2024`
- Personal OneDrive: `/personal/user_domain_com/Documents`

## Performance Considerations

- Large folders (>10,000 files) may take several minutes to analyze
- The tool processes folders recursively, one at a time
- Network speed affects performance
- Consider analyzing specific subfolders rather than entire document libraries

## Troubleshooting

### Authentication Issues

1. **"AADSTS700016: Application not found"**
   - Verify the client ID is correct
   - Ensure the app is registered in the correct tenant

2. **"AADSTS50059: No tenant-identifying information found"**
   - Check that the tenant ID is correct
   - Verify the site URL matches your tenant

3. **"Access denied" errors**
   - Ensure your account has read access to the folder
   - Verify API permissions are granted in Azure AD

### Docker Issues

1. **"Cannot connect to Docker daemon"**
   - Ensure Docker is running
   - On Linux, you may need to use `sudo`

2. **"No such file or directory"**
   - Create the output directory: `mkdir -p output`

## Security Notes

- This tool uses app-only authentication with client credentials
- Store your client secret securely (use environment variables, never commit to Git)
- Access tokens are only held in memory during execution
- The tool performs READ-ONLY operations
- Uses Microsoft Graph API with Sites.Selected permission for minimal access
- Consider using Azure Key Vault for production deployments

## Python vs Node.js Implementation

Both implementations provide the same functionality. Choose based on:

- **Python**: More detailed error messages, better for debugging
- **Node.js**: Slightly faster performance, colored output

## Development

### Running without Docker

**Python:**
```bash
cd python
pip install -r requirements.txt
python sharepoint_folder_size.py --help
```

**Node.js:**
```bash
cd nodejs
npm install
node sharepoint-folder-size.js --help
```

## License

MIT License - feel free to use and modify as needed.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify your Azure AD app configuration
3. Ensure you have appropriate SharePoint permissions
4. Check Docker logs: `docker-compose logs`