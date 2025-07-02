#!/usr/bin/env python3
"""
Monitoring Dashboard for SharePoint Folder Size Calculator
Provides a simple web interface to view health status and metrics
"""

import os
import json
import time
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from typing import Dict, Any, Optional

app = Flask(__name__)

# HTML template for the dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SharePoint Folder Size Monitor</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background-color: #333;
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .status-card {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .status-healthy {
            border-left: 5px solid #4CAF50;
        }
        .status-warning {
            border-left: 5px solid #FFC107;
        }
        .status-unhealthy {
            border-left: 5px solid #F44336;
        }
        .status-unknown {
            border-left: 5px solid #9E9E9E;
        }
        .metric {
            display: inline-block;
            margin: 10px 20px 10px 0;
        }
        .metric-label {
            color: #666;
            font-size: 14px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        .check-item {
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            background-color: #f9f9f9;
        }
        .check-healthy {
            background-color: #E8F5E9;
        }
        .check-warning {
            background-color: #FFF3E0;
        }
        .check-unhealthy {
            background-color: #FFEBEE;
        }
        .refresh-info {
            text-align: right;
            color: #666;
            font-size: 14px;
        }
    </style>
    <script>
        function refreshData() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => updateDashboard(data));
        }
        
        function updateDashboard(data) {
            // Update overall status
            const statusElement = document.getElementById('overall-status');
            statusElement.className = 'status-card status-' + data.health_status.status;
            
            // Update status text
            document.getElementById('status-text').textContent = data.health_status.status.toUpperCase();
            
            // Update last check time
            if (data.health_status.last_check) {
                const lastCheck = new Date(data.health_status.last_check);
                document.getElementById('last-check').textContent = lastCheck.toLocaleString();
            }
            
            // Update file metrics
            if (data.file_metrics) {
                document.getElementById('csv-size').textContent = formatFileSize(data.file_metrics.csv_size);
                document.getElementById('json-size').textContent = formatFileSize(data.file_metrics.json_size);
                document.getElementById('file-age').textContent = formatAge(data.file_metrics.age_seconds);
            }
            
            // Update health checks
            const checksContainer = document.getElementById('health-checks');
            checksContainer.innerHTML = '';
            
            for (const [check, result] of Object.entries(data.health_status.checks)) {
                const checkDiv = document.createElement('div');
                checkDiv.className = 'check-item check-' + result.status;
                checkDiv.innerHTML = `
                    <strong>${check.replace('_', ' ').toUpperCase()}</strong>: 
                    ${result.status} - ${result.message}
                `;
                checksContainer.appendChild(checkDiv);
            }
            
            // Update refresh time
            document.getElementById('refresh-time').textContent = new Date().toLocaleTimeString();
        }
        
        function formatFileSize(bytes) {
            if (!bytes) return 'N/A';
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
        }
        
        function formatAge(seconds) {
            if (!seconds) return 'N/A';
            if (seconds < 3600) return Math.round(seconds / 60) + ' minutes';
            if (seconds < 86400) return Math.round(seconds / 3600) + ' hours';
            return Math.round(seconds / 86400) + ' days';
        }
        
        // Refresh every 30 seconds
        setInterval(refreshData, 30000);
        
        // Initial load
        window.onload = refreshData;
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SharePoint Folder Size Monitor</h1>
            <p>Real-time monitoring dashboard for SharePoint folder size calculations</p>
        </div>
        
        <div id="overall-status" class="status-card status-unknown">
            <h2>System Status: <span id="status-text">LOADING...</span></h2>
            <p>Last Check: <span id="last-check">N/A</span></p>
        </div>
        
        <div class="status-card">
            <h3>Output File Metrics</h3>
            <div class="metric">
                <div class="metric-label">CSV Size</div>
                <div class="metric-value" id="csv-size">N/A</div>
            </div>
            <div class="metric">
                <div class="metric-label">JSON Size</div>
                <div class="metric-value" id="json-size">N/A</div>
            </div>
            <div class="metric">
                <div class="metric-label">File Age</div>
                <div class="metric-value" id="file-age">N/A</div>
            </div>
        </div>
        
        <div class="status-card">
            <h3>Health Checks</h3>
            <div id="health-checks">
                <p>Loading...</p>
            </div>
        </div>
        
        <div class="refresh-info">
            Last refreshed: <span id="refresh-time">N/A</span>
        </div>
    </div>
</body>
</html>
"""

def get_health_status() -> Dict[str, Any]:
    """Read the latest health status from file"""
    health_file = '/output/health_status.json'
    
    if os.path.exists(health_file):
        try:
            with open(health_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    
    return {
        'status': 'unknown',
        'last_check': None,
        'checks': {
            'authentication': {'status': 'unknown', 'message': 'No data available'},
            'site_connectivity': {'status': 'unknown', 'message': 'No data available'},
            'api_access': {'status': 'unknown', 'message': 'No data available'},
            'output_files': {'status': 'unknown', 'message': 'No data available'}
        }
    }

def get_file_metrics() -> Dict[str, Any]:
    """Get metrics about output files"""
    csv_file = '/output/folder_sizes_python.csv'
    json_file = '/output/folder_sizes_python.json'
    
    metrics = {
        'csv_size': None,
        'json_size': None,
        'age_seconds': None
    }
    
    try:
        if os.path.exists(csv_file):
            metrics['csv_size'] = os.path.getsize(csv_file)
            csv_mtime = os.path.getmtime(csv_file)
            
        if os.path.exists(json_file):
            metrics['json_size'] = os.path.getsize(json_file)
            json_mtime = os.path.getmtime(json_file)
            
        if 'csv_mtime' in locals() and 'json_mtime' in locals():
            oldest_mtime = min(csv_mtime, json_mtime)
            metrics['age_seconds'] = time.time() - oldest_mtime
            
    except Exception:
        pass
        
    return metrics

@app.route('/')
def dashboard():
    """Render the dashboard"""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/api/status')
def api_status():
    """API endpoint for status data"""
    return jsonify({
        'health_status': get_health_status(),
        'file_metrics': get_file_metrics(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    """Simple health check endpoint"""
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    print("Starting SharePoint Monitor Dashboard...")
    print("Access the dashboard at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)