# EMR System Deployment Guide v2

## Overview

This guide provides simple, step-by-step instructions for deploying the EMR Training System locally or on AWS.

## Prerequisites

- **Local**: Docker Desktop installed and running
- **AWS**: EC2 instance (t3.medium or larger) with Docker installed

## Quick Local Setup (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/your-repo/EMR.git
cd EMR

# 2. Run the all-in-one setup script
./quick-setup.sh

# 3. Access the system
open http://localhost
```

That's it! The system will be running with sample data including:
- 25 patients with complete medical histories
- Clinical notes and documentation
- Vital signs and lab results
- FHIR API at http://localhost/fhir/R4/
- CDS Hooks at http://localhost/cds-hooks/

## AWS Deployment (10 minutes)

### Step 1: Launch EC2 Instance

1. Launch an EC2 instance with:
   - Amazon Linux 2 or Ubuntu
   - t3.medium or larger
   - Security group allowing ports: 22 (SSH), 80 (HTTP)

### Step 2: Deploy the System

```bash
# SSH into your instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Download and run deployment script
curl -O https://raw.githubusercontent.com/your-repo/EMR/main/deploy-aws.sh
chmod +x deploy-aws.sh
./deploy-aws.sh
```

The script will automatically:
- Install Docker if needed
- Clone the repository
- Build and start the containers
- Import sample patient data
- Configure nginx routing

### Step 3: Access Your System

Visit `http://your-instance-ip` and login with any provider from the list.

## What's Included

### Clinical Features
- **Patient Management**: View and manage patient records
- **Clinical Workspace**: Document visits, view trends, place orders
- **FHIR API**: Full FHIR R4 compliant API
- **CDS Hooks**: Clinical decision support integration
- **Quality Measures**: Track clinical quality metrics

### Sample Data
- 25+ patients with realistic medical histories
- 100+ clinical notes and documentation
- Thousands of vital signs and lab results
- Medications, conditions, and procedures
- All data generated by Synthea for realistic training

## Customization

### Generate More Patients

```bash
# Generate 50 patients with clinical notes
docker exec emr-backend bash -c "
  cd scripts && 
  ./run_synthea_with_notes.sh 50 &&
  python import_synthea_with_notes.py
"
```

### Add Clinical Notes to Existing Patients

```bash
docker exec emr-backend python scripts/add_clinical_notes.py
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│    Nginx    │────▶│   Backend   │
│  (React)    │     │   (Port 80) │     │  (Port 8000)│
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   SQLite    │
                                        │  Database   │
                                        └─────────────┘
```

## Troubleshooting

### No Patients Visible
```bash
# Import sample patients
docker exec emr-backend python scripts/optimized_comprehensive_setup.py --patients 25
```

### No Clinical Notes
```bash
# Add clinical notes
docker exec emr-backend python scripts/add_clinical_notes.py
```

### FHIR/CDS Not Working
```bash
# Check backend health
curl http://localhost/api/health
curl http://localhost/fhir/R4/metadata
curl http://localhost/cds-hooks/
```

### Frontend Shows "localhost" in API Calls
This is a common issue where the frontend tries to connect to localhost:8000 instead of using relative URLs.

**Fix:**
```bash
# For Docker deployments, the Dockerfile now automatically fixes this
# For manual deployments, update src/services/api.js:
docker exec emr-frontend sh -c "sed -i 's|http://localhost:8000|""|g' /usr/share/nginx/html/static/js/*.js"

# Or rebuild the frontend with proper environment:
cd frontend
REACT_APP_API_URL="" npm run build
```

### View Logs
```bash
# Backend logs
docker logs emr-backend

# Nginx logs
docker logs emr-nginx
```

## Environment Variables

Create `.env` file for customization:

```env
# API Configuration
# IMPORTANT: For production deployments behind nginx/proxy, leave REACT_APP_API_URL empty
# to use relative URLs. Only set this if frontend and backend are on different domains.
REACT_APP_API_URL=
# For separate domains use: REACT_APP_API_URL=http://api.your-domain.com

# CORS Configuration
CORS_ORIGINS=["*"]

# Database
DATABASE_URL=sqlite:///./data/emr.db

# Features
ENABLE_CDS_HOOKS=true
ENABLE_FHIR_API=true
```

## Security Notes

For production deployments:
1. Change CORS origins from "*" to your specific domain
2. Enable HTTPS with SSL certificates
3. Implement proper authentication
4. Use PostgreSQL instead of SQLite
5. Regular backups of the database

## Support

- Check logs: `docker logs emr-backend`
- Database issues: `docker exec emr-backend python scripts/check_database.py`
- Report issues: https://github.com/your-repo/EMR/issues