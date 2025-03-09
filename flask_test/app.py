#!/usr/bin/env python3
from flask import Flask, render_template_string, request
import socket
import subprocess
import datetime

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>WireGuard Test</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .info-box {
            background-color: #f0f0f0;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
        }
        h1 {
            color: #333;
        }
        pre {
            background-color: #eee;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <h1>WireGuard Tunnel Test</h1>

    <div class="info-box">
        <h2>Server Info</h2>
        <p><strong>Hostname:</strong> {{ hostname }}</p>
        <p><strong>Server Time:</strong> {{ current_time }}</p>
        <p><strong>Client IP:</strong> {{ client_ip }}</p>
    </div>

    <div class="info-box">
        <h2>Network Interfaces</h2>
        <pre>{{ network_interfaces }}</pre>
    </div>

    <div class="info-box">
        <h2>Connection Path</h2>
        <p>Mobile → VPS (10.8.0.1) → Home Node (10.8.0.3) → This Page</p>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    # Get hostname
    hostname = socket.gethostname()

    # Get current time
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Get client IP
    client_ip = request.remote_addr if 'request' in globals() else "Unknown"

    # Get network interfaces
    try:
        network_interfaces = subprocess.check_output(['ip', '-br', 'addr']).decode('utf-8')
    except:
        network_interfaces = "Could not retrieve network information"

    # Render template with all the data
    return render_template_string(
        HTML_TEMPLATE,
        hostname=hostname,
        current_time=current_time,
        client_ip=client_ip,
        network_interfaces=network_interfaces
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
