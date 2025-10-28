<artifact identifier="billing-service-readme" type="text/markdown" title="Billing Service README.md">
# 📊 Billing Service - Production Deployment Guide
Complete documentation for the Vysedeck Billing Service deployed on DigitalOcean.

📋 Table of Contents

Overview
System Architecture
Server Information
Directory Structure
How It Works
API Documentation
Deployment Guide
Daily Operations
Troubleshooting
Future Enhancements


🎯 Overview
The Billing Service is a FastAPI-based application that:

Generates monthly invoices for voice agent call services
Creates PDF invoices with detailed breakdowns
Generates CSV call logs for transparency
Stores invoice data in Firebase Firestore
Runs automatically on the 1st of every month via cron job
Note: Email functionality is currently disabled due to SMTP port restrictions


🏗️ System Architecture
┌─────────────────────────────────────────────────┐
│                   Internet                       │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │   Nginx (Port 80)   │
         │ Reverse Proxy       │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  Uvicorn (Port 8000)│
         │  FastAPI Application│
         └──────────┬──────────┘
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
┌───────────────┐      ┌──────────────────┐
│   Firebase    │      │  Local Storage   │
│   Firestore   │      │  /invoices/      │
└───────────────┘      └──────────────────┘

🖥️ Server Information
Server Details

Host: Ubuntu 22.04 LTS on DigitalOcean
IP Address: 159.65.149.31
SSH Alias: automatework
Login: ssh automatework or ssh root@159.65.149.31

Installed Software

Python: 3.10.12
Nginx: 1.18.0
Supervisor: 4.2.1
Git: 2.34.1

Important Ports

80: HTTP (Nginx)
8000: Application (Uvicorn - internal only)


📁 Directory Structure
/var/www/billing-service/
├── venv/                               # Python virtual environment
├── db_configs/
│   ├── firebase_db.py                 # Firebase connection
│   └── vysedeck-voiceagent-firebase-adminsdk-*.json
├── repositories/                       # Data access layer
│   ├── bill_repo.py                   # Invoice CRUD operations
│   ├── callLogs_repo.py              # Call logs queries
│   └── companies_repo.py             # Company data queries
├── services/                          # Business logic
│   ├── billing_service.py            # Core billing calculations
│   ├── csv_service.py                # CSV generation
│   ├── pdf_service.py                # PDF generation
│   ├── mailer_service.py             # Email (currently disabled)
│   ├── invoice_service.py            # CLI invoice generation
│   └── invoice_service_copy.py       # API invoice generation
├── routes/
│   └── billing_routes.py             # API endpoints
├── reqResVal_models/
│   └── billing_models.py             # Pydantic models
├── templates/                         # HTML templates
│   ├── invoice_template.html         # PDF invoice template
│   └── invoice_email_template.html   # Email template
├── invoices/                          # Generated files
│   ├── *.pdf                         # Invoice PDFs
│   └── *.csv                         # Call log CSVs
├── main.py                           # FastAPI app entry point
├── billing_cli.py                    # CLI script for cron
├── requirements.txt                  # Python dependencies
├── .env                             # Environment variables
└── run_billing.sh                   # Cron job script

🔄 How It Works
1. Invoice Generation Flow
User Request → API Endpoint → Billing Service
                                    ↓
                    1. Check if invoice exists in Firebase
                                    ↓
                    2. If not, fetch company billing details
                                    ↓
                    3. Fetch call logs from Firebase
                                    ↓
                    4. Calculate charges (calls + maintenance + GST)
                                    ↓
                    5. Generate CSV with call details
                                    ↓
                    6. Save invoice to Firebase
                                    ↓
                    7. Generate PDF invoice
                                    ↓
                    8. Return invoice data as JSON
2. Billing Calculation Example
python# Example Calculation for September 2025
Total Calls: 13 calls
Total Minutes: 12 minutes (rounded up per call)
Rate: ₹2/minute

Call Charges = 12 × ₹2 = ₹24
Maintenance Fee = ₹1,500
Subtotal = ₹24 + ₹1,500 = ₹1,524
GST (18%) = ₹274.32
Total = ₹1,798.32
3. Two Execution Modes
Mode A: API (On-Demand)

Trigger: HTTP POST request
Use Case: Manual invoice generation
URL: http://159.65.149.31/billing-api/billing/generate/{company}?month=9&year=2025

Mode B: CLI (Automated)

Trigger: Cron job (1st of every month at 2 AM)
Use Case: Automatic monthly billing
Script: /var/www/billing-service/run_billing.sh
Log: /var/log/billing-cron.log


🔌 API Documentation
Base URL
http://159.65.149.31/billing-api
Endpoints
1. Health Check
httpGET /billing-api/
Response:
json{
  "message": "Billing API is running!"
}
2. Generate Invoice
httpPOST /billing-api/billing/generate/{company_name}?month={month}&year={year}
Parameters:

company_name (path): Company ID (e.g., "vysedeck", "webxpress", "dcgpac")
month (query, optional): Month (1-12). Defaults to last completed month
year (query, optional): Year. Defaults to current year

Example Request:
bashcurl -X POST "http://159.65.149.31/billing-api/billing/generate/vysedeck?month=9&year=2025"
Success Response (200):
json{
  "usageData": {
    "totalCalls": 13,
    "totalBilledMinutes": 12,
    "billingPolicy": "per-call"
  },
  "lineItems": [
    {
      "description": "Call Charges - 12 min × ₹2/min",
      "quantity": 12,
      "rate": 2.0,
      "amount": 24.0
    }
  ],
  "subtotal": 1524.0,
  "gstAmount": 274.32,
  "totalAmount": 1798.32,
  "invoiceDate": "2025-10-07T06:27:57.675160+00:00",
  "dueDate": "2025-10-14T06:27:57.675160+00:00",
  "companyId": "vysedeck",
  "billingPeriod": {
    "startDate": "2025-09-01T00:00:00+00:00",
    "endDate": "2025-09-30T23:59:59+00:00"
  }
}
Error Responses:
404 - Company Not Found:
json{
  "detail": "Invoice generation failed: Company 'xyz' not found"
}
500 - Internal Server Error:
json{
  "detail": "An unexpected error occurred during invoice generation."
}

🚀 Deployment Guide
Prerequisites

SSH access to the server
Git repository access: https://github.com/Vysedeck/BillingService
Firebase credentials JSON file

Initial Setup (Already Completed)
The initial deployment has been completed. The following components are configured:

✅ Python virtual environment
✅ Supervisor for process management
✅ Nginx reverse proxy
✅ Firebase connection
✅ Cron job for monthly automation

Deploying Code Changes
Follow these steps to deploy new code changes:
bash# 1. SSH into server
ssh automatework

# 2. Navigate to project directory
cd /var/www/billing-service

# 3. Pull latest changes from Git
git pull origin main

# 4. Activate virtual environment
source venv/bin/activate

# 5. Install any new dependencies (if requirements.txt changed)
pip install -r requirements.txt

# 6. Restart the application
sudo supervisorctl restart billing-api

# 7. Verify it's running
sudo supervisorctl status

# 8. Check logs for any errors
tail -f /var/log/billing-api.out.log
Press Ctrl+C to stop watching logs.
Configuration Files
1. Environment Variables (.env)
Location: /var/www/billing-service/.env
envSMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SENDER_EMAIL=shubham.mishra@vysedeck.com
SENDER_PASSWORD=evzp clsy edcu tsfa
GOOGLE_APPLICATION_CREDENTIALS=/var/www/billing-service/vysedeck-voiceagent-firebase-adminsdk-fbsvc-99ac27dfda.json
⚠️ IMPORTANT: Never commit .env or Firebase credentials to Git!
2. Supervisor Configuration
Location: /etc/supervisor/conf.d/billing-api.conf
ini[program:billing-api]
directory=/var/www/billing-service
command=/var/www/billing-service/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
user=root
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/billing-api.err.log
stdout_logfile=/var/log/billing-api.out.log
environment=PATH="/var/www/billing-service/venv/bin"
3. Nginx Configuration
Location: /etc/nginx/sites-available/vysedeck-ip
nginxserver {
    listen 80;
    listen [::]:80;
    server_name 159.65.149.31;
    
    root /var/www/vysedeck;
    index index.html;
    
    # Billing API
    location /billing-api {
        rewrite ^/billing-api(/.*)$ $1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
    
    # Original static files
    location / {
        try_files $uri $uri/ =404;
    }
}
4. Cron Job
View cron jobs:
bashcrontab -l
Current schedule:
cron# Run billing on 1st of every month at 2:00 AM
0 2 1 * * /var/www/billing-service/run_billing.sh
Edit cron jobs:
bashcrontab -e

📊 Daily Operations
Monitoring
Check Application Status
bashsudo supervisorctl status
Expected output:
billing-api                      RUNNING   pid 12345, uptime 5 days
View Real-Time Logs
bash# Application logs
tail -f /var/log/billing-api.out.log

# Error logs
tail -f /var/log/billing-api.err.log

# Cron job logs
tail -f /var/log/billing-cron.log
Check Generated Files
bash# List all invoices
ls -lh /var/www/billing-service/invoices/

# View recent files
ls -lht /var/www/billing-service/invoices/ | head -10
Common Operations
Restart the Application
bashsudo supervisorctl restart billing-api
Stop the Application
bashsudo supervisorctl stop billing-api
Start the Application
bashsudo supervisorctl start billing-api
Reload Nginx Configuration
bashsudo nginx -t  # Test configuration first
sudo systemctl reload nginx
Manual Invoice Generation
Via API:
bashcurl -X POST "http://159.65.149.31/billing-api/billing/generate/vysedeck?month=10&year=2025"
Via CLI (directly on server):
bashcd /var/www/billing-service
source venv/bin/activate
python billing_cli.py
Test Cron Job Manually
bash/var/www/billing-service/run_billing.sh
cat /var/log/billing-cron.log

🔧 Troubleshooting
Issue 1: API Returns 502 Bad Gateway
Symptoms:
html<html>
<head><title>502 Bad Gateway</title></head>
Solution:
bash# Check if application is running
sudo supervisorctl status

# Check error logs
tail -50 /var/log/billing-api.err.log

# Restart the application
sudo supervisorctl restart billing-api
Issue 2: Application Won't Start
Check for errors:
bashtail -100 /var/log/billing-api.err.log
Common causes:

Syntax errors in Python code: Fix the code and restart
Missing dependencies: Run pip install -r requirements.txt
Port 8000 already in use: Kill the process using sudo lsof -ti:8000 | xargs kill -9
Firebase credentials missing: Ensure .env file is correct

Issue 3: Invoice Generation Fails
Check logs:
bashtail -50 /var/log/billing-api.out.log
Common causes:

Firebase connection issue: Check credentials and network
No call data for the period: Verify data exists in Firebase
Permission issues: Ensure /var/www/billing-service/invoices/ is writable

bash# Fix permissions
sudo chmod -R 755 /var/www/billing-service/invoices/
Issue 4: Cron Job Not Running
Check cron logs:
bashcat /var/log/billing-cron.log
Verify cron job is configured:
bashcrontab -l
Test cron script manually:
bash/var/www/billing-service/run_billing.sh
Check cron service:
bashsudo systemctl status cron
Issue 5: Cannot Connect to Firebase
Error message:
Error connecting to Firebase: Invalid certificate argument: "None"
Solution:
bash# Check if credentials file exists
ls -la /var/www/billing-service/vysedeck-voiceagent-firebase-adminsdk-*.json

# Check .env file
cat /var/www/billing-service/.env | grep GOOGLE_APPLICATION_CREDENTIALS

# Verify Firebase connection
cd /var/www/billing-service
source venv/bin/activate
python -c "from db_configs.firebase_db import firestore_client; print('Connected!' if firestore_client else 'Failed')"
Issue 6: Git Pull Fails
Error: Modified files
bash# Stash local changes
git stash

# Pull latest code
git pull origin main

# Restore changes if needed
git stash pop
Error: Merge conflicts
bash# View conflicts
git status

# Resolve conflicts manually or reset to remote
git reset --hard origin/main

📈 Monitoring & Logs
Log Files Location
Log FilePurposeCommand/var/log/billing-api.out.logApplication stdouttail -f /var/log/billing-api.out.log/var/log/billing-api.err.logApplication errorstail -f /var/log/billing-api.err.log/var/log/billing-cron.logCron job outputtail -f /var/log/billing-cron.log/var/log/nginx/access.logNginx access logstail -f /var/log/nginx/access.log/var/log/nginx/error.logNginx error logstail -f /var/log/nginx/error.log
Key Metrics to Monitor

Application Health

Supervisor status: Should be RUNNING
Response time: Should be < 5 seconds
Error rate: Should be minimal


Generated Files

PDFs created successfully
CSVs contain correct data
Files saved in /var/www/billing-service/invoices/


Firebase Connectivity

Connection status on startup
Query response times
Data retrieval success rate


System Resources

bash# Check disk space
df -h

# Check memory usage
free -h

# Check CPU usage
top

🔮 Future Enhancements
1. Enable Email Functionality
Current Status: Disabled (SMTP ports blocked by DigitalOcean)
Options to enable:
Option A: Contact DigitalOcean Support

Submit a support ticket at https://cloud.digitalocean.com/support/tickets/new
Request to unblock SMTP ports (25, 587, 465)
Explain it's for legitimate business invoicing
Wait for approval (usually 24-48 hours)

Option B: Use SendGrid

Sign up at https://sendgrid.com/
Get API key
Update .env:

envSENDGRID_API_KEY=SG.your_api_key_here

Uncomment email code in services/invoice_service.py
Restart application

Option C: Use AWS SES or Mailgun
Similar process to SendGrid
2. Add More Companies
Current companies: vysedeck, webxpress, dcgpac
To add a new company:

Add company data to Firebase under companies/{company_id}
Include billing rates, contact info, GST details
Test invoice generation:

bashcurl -X POST "http://159.65.149.31/billing-api/billing/generate/new_company?month=10&year=2025"
3. Add Authentication
Recommended: Add API key authentication
python# Example: Add to billing_routes.py
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header()):
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API Key")
4. Add Monitoring/Alerting
Options:

Uptime monitoring: UptimeRobot, Pingdom
Application monitoring: New Relic, DataDog
Log management: Papertrail, Loggly

5. Setup SSL Certificate
Using Let's Encrypt (Free):
bashsudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
6. Add Database Backup
Firebase backup strategy:

Use Firebase scheduled exports
Store backups in Google Cloud Storage
Configure in Firebase Console

7. Implement Rate Limiting
Prevent API abuse:
pythonfrom slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/billing/generate/{company}")
@limiter.limit("10/hour")
async def generate_invoice(...):
    ...

📞 Support & Contacts
Key Personnel

Primary Contact: Shashank Trivedi
Email: shashank.trivedi@vysedeck.com
Backup Contact: Vishruth Ramesh (vishruth.ramesh@vysedeck.com)

External Services

Hosting: DigitalOcean (IP: 159.65.149.31)
Database: Firebase Firestore
Repository: GitHub - Vysedeck/BillingService

Useful Links

Firebase Console: https://console.firebase.google.com/
DigitalOcean Dashboard: https://cloud.digitalocean.com/
GitHub Repository: https://github.com/Vysedeck/BillingService


📝 Quick Reference Commands
bash# SSH into server
ssh automatework

# Navigate to project
cd /var/www/billing-service

# Activate virtual environment
source venv/bin/activate

# Check application status
sudo supervisorctl status

# Restart application
sudo supervisorctl restart billing-api

# View logs
tail -f /var/log/billing-api.out.log

# Deploy new code
git pull && sudo supervisorctl restart billing-api

# Test API
curl http://159.65.149.31/billing-api/

# Generate invoice manually
curl -X POST "http://159.65.149.31/billing-api/billing/generate/vysedeck?month=10&year=2025"

# View generated files
ls -lh /var/www/billing-service/invoices/

# Check cron job
crontab -l

# Test cron job manually
/var/www/billing-service/run_billing.sh

⚠️ Important Notes

Never commit sensitive files to Git:

.env
*-firebase-adminsdk-*.json
Any files in invoices/


Always test before deploying:

Test locally first
Use a staging environment if possible
Check logs after deployment


Backup important data:

Firebase data is automatically backed up by Google
Generated invoices are stored locally (consider backing up)


Email is currently disabled:

SMTP ports are blocked by DigitalOcean
Invoices are generated but not emailed
PDF and CSV files are available in /var/www/billing-service/invoices/


Cron job runs automatically:

Executes on the 1st of every month at 2:00 AM
Generates invoices for all companies
Check /var/log/billing-cron.log for results




🎓 Learning Resources
FastAPI

Official docs: https://fastapi.tiangolo.com/
Tutorial: https://fastapi.tiangolo.com/tutorial/

Firebase

Firestore docs: https://firebase.google.com/docs/firestore
Python SDK: https://firebase.google.com/docs/admin/setup

Nginx

Beginner's guide: https://nginx.org/en/docs/beginners_guide.html
Reverse proxy: https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/

Supervisor

Official docs: http://supervisord.org/
Configuration: http://supervisord.org/configuration.html


📄 License
Internal company project - Vysedeck AI Ventures Pvt Ltd

Last Updated: October 8, 2025
Version: 1.0.0
Maintained by: Shashank Trivedi
</artifact>