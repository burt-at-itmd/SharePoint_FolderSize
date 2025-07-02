# SharePoint Storage Analyzer Setup Guide

This guide will help you set up the SharePoint Storage Analyzer to discover hidden storage usage in your SharePoint sites. The tool reveals version history, recycle bins, and other hidden storage that SharePoint doesn't show in its UI.

## Prerequisites

- Docker Desktop installed (Windows, Mac, or Linux)
- Global Administrator or Application Administrator role in Azure AD
- Access to SharePoint Admin Center
- Basic understanding of Azure AD app registrations

## Step 1: Create Azure AD App Registration

1. Navigate to [Azure Portal](https://portal.azure.com)
2. Go to **Azure Active Directory** → **App registrations**
3. Click **"New registration"**
4. Enter details:
   - **Name**: SharePoint Storage Analyzer
   - **Supported account types**: Single tenant
   - **Redirect URI**: Leave blank
5. Click **"Register"**
6. Copy and save:
   - Application (client) ID
   - Directory (tenant) ID

## Step 2: Create Client Secret

1. In your app registration, go to **"Certificates & secrets"**
2. Click **"New client secret"**
3. Add description: "SharePoint Storage Analyzer"
4. Choose expiration (recommended: 24 months)
5. Click **"Add"**
6. **IMMEDIATELY copy the secret value** - you cannot retrieve it later!

## Step 3: Configure API Permissions

1. In your app registration, go to **"API permissions"**
2. Click **"Add a permission"**
3. Select **"Microsoft Graph"**
4. Choose **"Application permissions"**
5. Add these permissions:
   - `Sites.Read.All`
   - `Sites.Selected` (REQUIRED)
6. Click **"Add permissions"**
7. Click **"Grant admin consent for [Your Organization]"**
8. Confirm the consent

## Step 4: Grant Access to Specific SharePoint Site

This step uses Microsoft Graph Explorer to grant your app access to the specific SharePoint site:

1. Navigate to https://graph.microsoft.com
2. Sign in with your Global Administrator account
3. Click **"Modify permissions"** and ensure you have `Sites.FullControl.All`
4. Find your site ID:
   - **Method**: GET
   - **URL**: `https://graph.microsoft.com/v1.0/sites?search=yoursite`
   - Click **"Run query"**
   - Copy the site ID from the response

5. Grant app access to the site:
   - **Method**: POST
   - **URL**: `https://graph.microsoft.com/v1.0/sites/{site-id}/permissions`
   - **Request body**:
   ```json
   {
     "roles": ["read"],
     "grantedToIdentities": [{
       "application": {
         "id": "YOUR-APP-CLIENT-ID",
         "displayName": "SharePoint Storage Analyzer"
       }
     }]
   }
   ```
   - Replace `YOUR-APP-CLIENT-ID` with your app's client ID
   - Click **"Run query"**
   - You should receive a 201 Created response

## Step 5: Set Up the SharePoint Storage Analyzer

1. Download or clone the SharePoint Storage Analyzer repository
2. Navigate to the project folder
3. Copy `template/.env.template` to `.env`
4. Edit the `.env` file with your values:
   - `TENANT_ID`: Your Azure AD tenant ID
   - `CLIENT_ID`: Your app's client ID
   - `CLIENT_SECRET`: Your app's client secret
   - `SITE_URL`: Your SharePoint site URL
   - `FOLDER_PATH`: Usually `/sites/yoursite/Shared Documents`

## Step 6: Run the Analysis

Open a terminal/command prompt in the project folder and run:

1. Build the Docker containers:
   ```bash
   docker-compose build
   ```

2. Run the comprehensive analysis:
   ```bash
   docker-compose run --rm comprehensive-analyzer
   ```

3. Wait for completion (may take several minutes for large sites)

4. Find your results in the `output/` folder:
   - `folder_tree_summary.csv` - Hierarchical folder breakdown
   - `all_files_detailed.json` - Complete file inventory with versions
   - `storage_mystery_solved.csv` - Executive summary

## Understanding the Results

The analyzer reveals hidden storage that SharePoint doesn't show:

- **Active Files**: What you see in SharePoint UI
- **Version History**: Previous versions of every file (often 50-80% of total storage!)
- **Recycle Bin**: Deleted items retained for 93 days
- **System/Hidden**: Metadata, indexes, and compliance data

Common findings:
- PowerPoint files often have hundreds of versions
- Auto-save creates a new version every few minutes
- Default SharePoint settings keep ALL versions forever
- Setting version limits to 5-10 can reclaim 80% of version storage

## Troubleshooting

### Common Issues:

1. **"Authentication failed"**
   - Verify your CLIENT_SECRET is correct
   - Check the secret hasn't expired
   - Ensure admin consent was granted

2. **"Access denied" or "403 Forbidden"**
   - Verify Sites.Selected permission was granted
   - Confirm you ran the Graph Explorer permission grant
   - Check the site URL is correct

3. **"Docker command not found"**
   - Ensure Docker Desktop is installed and running
   - On Windows, you may need to restart after installation

4. **Analysis takes too long**
   - Large sites with many versions can take 10-30 minutes
   - Use `docker logs` to monitor progress

## Security Notes

- The analyzer has **READ-ONLY** access - it cannot modify or delete any data
- Store your `.env` file securely and never commit it to version control
- The client secret should be rotated periodically
- Consider removing the app registration when analysis is complete
- Results may contain sensitive file names - handle output files appropriately

## Support

For issues or questions:
- Check the troubleshooting section above
- Review logs: `docker-compose logs`
- Consult the README.md for additional documentation
- Report issues on the project's GitHub repository