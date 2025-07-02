#!/usr/bin/env node
/**
 * SharePoint Folder Size Calculator with Multiple Authentication Methods
 * This script calculates folder sizes recursively in SharePoint Online
 * using either client credentials or device code flow for authentication.
 */

import { spfi } from "@pnp/sp";
import "@pnp/sp/webs";
import "@pnp/sp/folders";
import "@pnp/sp/files";
import { PublicClientApplication, ConfidentialClientApplication } from "@azure/msal-node";
import { promises as fs } from 'fs';
import { createObjectCsvWriter } from 'csv-writer';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';
import chalk from 'chalk';
import ora from 'ora';

class AuthProvider {
    constructor(tenantId, clientId, siteUrl, clientSecret = null) {
        this.tenantId = tenantId;
        this.clientId = clientId;
        this.siteUrl = siteUrl;
        this.clientSecret = clientSecret;
        this.authority = `https://login.microsoftonline.com/${tenantId}`;
    }

    async authenticate() {
        if (this.clientSecret) {
            return await this.authenticateClientCredentials();
        } else {
            return await this.acquireTokenDeviceCode();
        }
    }

    async authenticateClientCredentials() {
        console.log('\n' + '='.repeat(50));
        console.log(chalk.bold.yellow('CLIENT CREDENTIALS AUTHENTICATION'));
        console.log('='.repeat(50));
        console.log(chalk.cyan('Authenticating with client secret...'));

        const config = {
            auth: {
                clientId: this.clientId,
                authority: this.authority,
                clientSecret: this.clientSecret
            }
        };

        const cca = new ConfidentialClientApplication(config);
        const tokenRequest = {
            scopes: [`${this.siteUrl}/.default`]
        };

        try {
            const response = await cca.acquireTokenByClientCredential(tokenRequest);
            console.log(chalk.green('✓ Authentication successful!'));
            console.log('='.repeat(50) + '\n');
            return response.accessToken;
        } catch (error) {
            console.error(chalk.red('✗ Authentication failed!'));
            console.error(chalk.red(`Error: ${error.message}`));
            return null;
        }
    }

    async acquireTokenDeviceCode() {
        const config = {
            auth: {
                clientId: this.clientId,
                authority: this.authority
            }
        };
        
        const pca = new PublicClientApplication(config);
        
        const deviceCodeRequest = {
            scopes: [`${this.siteUrl}/.default`],
            deviceCodeCallback: (response) => {
                console.log('\n' + '='.repeat(50));
                console.log(chalk.bold.yellow('DEVICE CODE AUTHENTICATION'));
                console.log('='.repeat(50));
                console.log(chalk.cyan('\nTo sign in, use a web browser to open the page:'));
                console.log(chalk.bold.blue(response.verificationUri));
                console.log(chalk.cyan('\nEnter the code:'), chalk.bold.green(response.userCode));
                console.log(chalk.yellow('\nWaiting for authentication...'));
                console.log('='.repeat(50) + '\n');
            }
        };

        try {
            const response = await pca.acquireTokenByDeviceCode(deviceCodeRequest);
            console.log(chalk.green('✓ Authentication successful!'));
            return response.accessToken;
        } catch (error) {
            console.error(chalk.red('✗ Authentication failed!'));
            console.error(chalk.red(`Error: ${error.message}`));
            return null;
        }
    }
}

class SharePointFolderSizeCalculator {
    constructor(siteUrl, accessToken) {
        this.siteUrl = siteUrl;
        this.sp = spfi(siteUrl).using((instance) => {
            instance.on.auth.replace(async (url, init) => {
                init.headers = {
                    ...init.headers,
                    "Authorization": `Bearer ${accessToken}`,
                };
                return [url, init];
            });
            return instance;
        });
    }

    async getFolderSizeRecursive(folderPath) {
        const spinner = ora(`Analyzing folder: ${folderPath}`).start();
        
        try {
            // Ensure folder path is properly formatted
            if (!folderPath.startsWith('/')) {
                folderPath = '/' + folderPath;
            }

            const result = {
                path: folderPath,
                name: folderPath.split('/').pop() || 'Root',
                totalSize: 0,
                fileCount: 0,
                folderCount: 0,
                files: [],
                subfolders: []
            };

            await this.processFolderRecursive(folderPath, result, spinner);
            
            spinner.succeed(`Analysis complete for: ${folderPath}`);
            return result;

        } catch (error) {
            spinner.fail(`Error accessing folder ${folderPath}`);
            console.error(chalk.red(`Error details: ${error.message}`));
            return null;
        }
    }

    async processFolderRecursive(folderPath, result, spinner, depth = 0) {
        const indent = '  '.repeat(depth);
        
        try {
            // Get folder object
            const folder = this.sp.web.getFolderByServerRelativePath(folderPath);
            
            // Get files in current folder
            const files = await folder.files.select("Name", "Length", "TimeLastModified", "ServerRelativeUrl")();
            
            // Process each file
            for (const file of files) {
                const fileInfo = {
                    name: file.Name,
                    size: file.Length,
                    lastModified: file.TimeLastModified,
                    path: file.ServerRelativeUrl
                };
                
                result.files.push(fileInfo);
                result.totalSize += file.Length;
                result.fileCount++;
                
                spinner.text = `${indent}  📄 ${file.Name} (${this.formatSize(file.Length)})`;
            }

            // Get subfolders
            const subfolders = await folder.folders.filter("Name ne 'Forms'")();
            
            // Process each subfolder
            for (const subfolder of subfolders) {
                // Skip hidden system folders
                if (subfolder.Name.startsWith('_')) {
                    continue;
                }
                
                spinner.text = `${indent}📁 ${subfolder.Name}/`;
                result.folderCount++;
                
                // Create subfolder result
                const subfolderResult = {
                    path: subfolder.ServerRelativeUrl,
                    name: subfolder.Name,
                    totalSize: 0,
                    fileCount: 0,
                    folderCount: 0,
                    files: [],
                    subfolders: []
                };
                
                // Recursively process subfolder
                await this.processFolderRecursive(
                    subfolder.ServerRelativeUrl, 
                    subfolderResult, 
                    spinner, 
                    depth + 1
                );
                
                // Add subfolder results to parent
                result.subfolders.push(subfolderResult);
                result.totalSize += subfolderResult.totalSize;
                result.fileCount += subfolderResult.fileCount;
                result.folderCount += subfolderResult.folderCount;
            }
        } catch (error) {
            spinner.warn(`${indent}⚠️  Error processing folder: ${error.message}`);
        }
    }

    formatSize(bytes) {
        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let size = bytes;
        let unitIndex = 0;
        
        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }
        
        return `${size.toFixed(2)} ${units[unitIndex]}`;
    }

    printSummary(result) {
        if (!result) return;
        
        console.log('\n' + '='.repeat(60));
        console.log(chalk.bold.cyan('FOLDER SIZE SUMMARY'));
        console.log('='.repeat(60));
        console.log(chalk.white(`Path: ${chalk.yellow(result.path)}`));
        console.log(chalk.white(`Total Size: ${chalk.green(this.formatSize(result.totalSize))} (${result.totalSize.toLocaleString()} bytes)`));
        console.log(chalk.white(`Files: ${chalk.blue(result.fileCount.toLocaleString())}`));
        console.log(chalk.white(`Folders: ${chalk.blue(result.folderCount.toLocaleString())}`));
        console.log('='.repeat(60));
        
        // Print top 10 largest files
        const allFiles = this.getAllFiles(result);
        allFiles.sort((a, b) => b.size - a.size);
        
        if (allFiles.length > 0) {
            console.log('\n' + chalk.bold.cyan('Top 10 Largest Files:'));
            console.log('-'.repeat(60));
            
            const top10 = allFiles.slice(0, 10);
            top10.forEach((file, index) => {
                const num = chalk.gray(`${index + 1}.`.padStart(3));
                const name = chalk.white(file.name.padEnd(40));
                const size = chalk.green(this.formatSize(file.size).padStart(10));
                console.log(`${num} ${name} ${size}`);
            });
        }
    }

    getAllFiles(result) {
        let files = [...result.files];
        for (const subfolder of result.subfolders) {
            files = files.concat(this.getAllFiles(subfolder));
        }
        return files;
    }

    async exportToCSV(result, filename) {
        const records = [];
        
        const collectRecords = (folderData) => {
            // Add folder record
            records.push({
                path: folderData.path,
                name: folderData.name,
                type: 'Folder',
                sizeBytes: folderData.totalSize,
                sizeFormatted: this.formatSize(folderData.totalSize),
                fileCount: folderData.fileCount,
                folderCount: folderData.folderCount
            });
            
            // Add file records
            for (const file of folderData.files) {
                records.push({
                    path: file.path,
                    name: file.name,
                    type: 'File',
                    sizeBytes: file.size,
                    sizeFormatted: this.formatSize(file.size),
                    fileCount: 0,
                    folderCount: 0
                });
            }
            
            // Process subfolders
            for (const subfolder of folderData.subfolders) {
                collectRecords(subfolder);
            }
        };
        
        collectRecords(result);
        
        const csvWriter = createObjectCsvWriter({
            path: filename,
            header: [
                { id: 'path', title: 'Path' },
                { id: 'name', title: 'Name' },
                { id: 'type', title: 'Type' },
                { id: 'sizeBytes', title: 'Size (bytes)' },
                { id: 'sizeFormatted', title: 'Size (formatted)' },
                { id: 'fileCount', title: 'File Count' },
                { id: 'folderCount', title: 'Folder Count' }
            ]
        });
        
        await csvWriter.writeRecords(records);
        console.log(chalk.green(`\n✓ Results exported to: ${filename}`));
    }

    async exportToJSON(result, filename) {
        await fs.writeFile(filename, JSON.stringify(result, null, 2));
        console.log(chalk.green(`✓ Results exported to: ${filename}`));
    }
}

async function main() {
    const argv = yargs(hideBin(process.argv))
        .option('tenant-id', {
            describe: 'Azure AD tenant ID',
            type: 'string',
            demandOption: true
        })
        .option('client-id', {
            describe: 'Azure AD application client ID',
            type: 'string',
            demandOption: true
        })
        .option('client-secret', {
            describe: 'Azure AD application client secret (for app-only auth)',
            type: 'string'
        })
        .option('site-url', {
            describe: 'SharePoint site URL',
            type: 'string',
            demandOption: true
        })
        .option('folder-path', {
            describe: 'Folder path to analyze',
            type: 'string',
            demandOption: true
        })
        .option('output-csv', {
            describe: 'Output CSV filename',
            type: 'string',
            default: 'folder_sizes.csv'
        })
        .option('output-json', {
            describe: 'Output JSON filename',
            type: 'string',
            default: 'folder_sizes.json'
        })
        .help()
        .argv;

    console.log(chalk.bold.magenta('\n🚀 SharePoint Folder Size Calculator'));
    console.log('='.repeat(60));

    // Check for client secret in environment if not provided
    const clientSecret = argv.clientSecret || process.env.CLIENT_SECRET;

    // Authenticate
    const authProvider = new AuthProvider(
        argv.tenantId,
        argv.clientId,
        argv.siteUrl,
        clientSecret
    );

    const accessToken = await authProvider.authenticate();
    if (!accessToken) {
        console.error(chalk.red('✗ Authentication failed. Exiting.'));
        process.exit(1);
    }

    // Calculate folder sizes
    const calculator = new SharePointFolderSizeCalculator(argv.siteUrl, accessToken);
    
    const startTime = Date.now();
    const result = await calculator.getFolderSizeRecursive(argv.folderPath);
    const endTime = Date.now();

    if (result) {
        calculator.printSummary(result);
        await calculator.exportToCSV(result, argv.outputCsv);
        await calculator.exportToJSON(result, argv.outputJson);
        
        const duration = ((endTime - startTime) / 1000).toFixed(2);
        console.log(chalk.cyan(`\n⏱️  Processing time: ${duration} seconds`));
        console.log(chalk.green.bold('\n✅ Analysis complete!'));
    } else {
        console.error(chalk.red.bold('\n❌ Failed to analyze folder.'));
        process.exit(1);
    }
}

// Run the main function
main().catch(error => {
    console.error(chalk.red('Unexpected error:'), error);
    process.exit(1);
});