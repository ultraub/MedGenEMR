# EMR Training System

A comprehensive Electronic Medical Records (EMR) training system with FHIR R4 support, synthetic patient generation, and Clinical Decision Support (CDS) Hooks integration.

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd emr-training-system
   ```

2. **Run the setup script**
   ```bash
   ./setup_emr_system.sh
   ```

3. **Access the system**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Docker Deployment

```bash
docker-compose -f docker-compose.standalone.yml up -d
```

Access the system at http://localhost

## 🌟 Features

- **Patient Management**: Create, read, update patient records
- **Clinical Workspace**: View medications, conditions, vitals, and clinical notes
- **FHIR R4 Compliance**: Full support for FHIR resources
- **CDS Hooks**: Clinical decision support integration
- **Synthetic Data**: Automated generation of realistic patient data using Synthea
- **Provider Management**: Multiple provider support with patient assignment

## 📁 Architecture

```
emr-training-system/
├── backend/               # FastAPI backend application
│   ├── api/              # API endpoints and routers
│   ├── models/           # SQLAlchemy database models
│   ├── schemas/          # Pydantic schemas
│   └── scripts/          # Utility scripts
├── frontend/             # React frontend application
│   ├── public/          # Static assets
│   └── src/             # React components
├── synthea/             # Synthetic patient data generator
└── deployment/          # Deployment configurations
```

## 🔧 System Requirements

- Python 3.9+
- Node.js 18+
- Java 8+ (for Synthea)
- 4GB RAM minimum
- 10GB disk space

## 📦 Dependencies

### Backend
- FastAPI 0.104.1
- Pydantic 2.5.0
- SQLAlchemy 2.0.23
- FHIR Resources 6.5.0

### Frontend
- React 18.2.0
- Material-UI 5.14.18
- Axios 1.6.2

## 🚀 AWS Deployment

### Option 1: One-Click CloudFormation Deployment (Recommended)

Deploy the entire EMR system with a single CloudFormation template. This is the easiest method and handles all setup automatically.

#### Prerequisites

1. **AWS Account**: Active AWS account with appropriate permissions
2. **EC2 Key Pair**: Required for SSH access (create one if needed)
3. **AWS CLI** (optional): For command-line deployment

#### Step-by-Step Deployment

##### Create EC2 Key Pair (if needed)

**Using AWS Console:**
1. Go to EC2 Console → Key Pairs
2. Click "Create key pair"
3. Name: `emr-training-key` (or your choice)
4. Format: PEM (Mac/Linux) or PPK (Windows)
5. Download and save securely

**Using AWS CLI:**
```bash
aws ec2 create-key-pair --key-name emr-training-key \
  --query 'KeyMaterial' --output text > emr-training-key.pem
chmod 400 emr-training-key.pem
```

##### Deploy with CloudFormation Console (Easiest)

1. **Open CloudFormation**
   - Go to [AWS CloudFormation Console](https://console.aws.amazon.com/cloudformation)
   - Select your region (e.g., us-east-1)

2. **Create Stack**
   - Click "Create stack" → "With new resources"
   - Choose "Upload a template file"
   - Select `cloudformation-emr.yaml`
   - Click "Next"

3. **Configure Parameters**
   - **Stack name**: `emr-training-system`
   - **InstanceType**: `t3.medium` (recommended)
   - **KeyPairName**: Select from dropdown
   - **AllowedIPRange**: `0.0.0.0/0` or your IP: `YOUR_IP/32`
   - **PatientCount**: `50` (adjustable: 10-500)
   - Click "Next"

4. **Review and Create**
   - Accept defaults or add tags
   - Check: "I acknowledge that AWS CloudFormation might create IAM resources"
   - Click "Create stack"

5. **Monitor Progress**
   - Wait 5-10 minutes for "CREATE_COMPLETE"
   - Check "Events" tab for progress

6. **Access Your System**
   - Go to "Outputs" tab
   - Copy the `PublicURL` value
   - Open in browser (may take 5 more minutes for initial setup)

##### Deploy with AWS CLI

```bash
# Deploy stack
aws cloudformation create-stack \
  --stack-name emr-training-system \
  --template-body file://cloudformation-emr.yaml \
  --parameters \
    ParameterKey=KeyPairName,ParameterValue=emr-training-key \
    ParameterKey=InstanceType,ParameterValue=t3.medium \
    ParameterKey=AllowedIPRange,ParameterValue=0.0.0.0/0 \
    ParameterKey=PatientCount,ParameterValue=50 \
  --capabilities CAPABILITY_IAM \
  --region us-east-1

# Check status
aws cloudformation describe-stacks \
  --stack-name emr-training-system \
  --query 'Stacks[0].StackStatus'

# Get outputs
aws cloudformation describe-stacks \
  --stack-name emr-training-system \
  --query 'Stacks[0].Outputs'
```

#### Post-Deployment

**SSH Access** (if needed):
```bash
ssh -i emr-training-key.pem ec2-user@<PUBLIC_IP>

# Check deployment logs
sudo tail -f /var/log/user-data.log

# Monitor Docker containers
sudo docker ps
sudo docker-compose logs -f
```

**Stack Management:**
- **Update**: CloudFormation Console → Stack → Update
- **Stop/Start**: EC2 Console → Stop instance (preserves data)
- **Delete**: `aws cloudformation delete-stack --stack-name emr-training-system`

#### Troubleshooting

| Issue | Solution |
|-------|----------|
| Stack creation failed | Check Events tab for specific error |
| Can't access URL | Wait 10-15 minutes for full deployment |
| "Connection refused" | Check security group allows port 80 |
| Invalid key pair | Ensure key exists in selected region |

#### Cost Optimization

- **Estimated Cost**: ~$30-40/month (t3.medium running 24/7)
- **Save Money**:
  - Stop instance when not in use
  - Use t3.small for testing ($15-20/month)
  - Set up auto-stop schedule with Lambda

Access the system via the URL in CloudFormation outputs (typically ready in 10-15 minutes).

### Option 2: Docker Container Deployment

#### Build and Push to ECR

```bash
# Configure AWS credentials
aws configure

# Run the deployment script
./deploy-aws.sh ec2
```

#### Deploy to EC2

1. **Using the generated user-data.sh**:
   - Launch an EC2 instance (Amazon Linux 2)
   - Choose t3.medium or larger
   - Configure security group (ports 80, 22)
   - Paste user-data.sh contents in Advanced Details

2. **Using AWS CLI**:
   ```bash
   aws ec2 run-instances \
     --image-id ami-0c02fb55956c7d316 \
     --instance-type t3.medium \
     --key-name your-keypair \
     --security-group-ids sg-xxxxxx \
     --user-data file://user-data.sh
   ```

#### Deploy to ECS Fargate

```bash
# Build and push image
./deploy-aws.sh ecs

# Create ECS cluster
aws ecs create-cluster --cluster-name emr-cluster

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service (update JSON with your subnet/security group)
aws ecs create-service --cluster emr-cluster --cli-input-json file://service-definition.json
```

#### Deploy to App Runner

```bash
# Build and push image
./deploy-aws.sh apprunner

# Create App Runner service
aws apprunner create-service --cli-input-json file://apprunner-service.json
```

### Option 3: Manual Docker Deployment on EC2

1. **Launch EC2 instance** (Amazon Linux 2, t3.medium)

2. **SSH into instance**:
   ```bash
   ssh -i your-key.pem ec2-user@your-instance-ip
   ```

3. **Install Docker**:
   ```bash
   sudo yum update -y
   sudo amazon-linux-extras install docker -y
   sudo service docker start
   sudo usermod -a -G docker ec2-user
   ```

4. **Clone repository and deploy**:
   ```bash
   git clone <repository-url>
   cd emr-training-system
   docker-compose -f docker-compose.standalone.yml up -d
   ```

### Deployment Configuration

#### Environment Variables

Configure these in your deployment:

- `PATIENT_COUNT`: Number of synthetic patients to generate (default: 25)
- `SKIP_SYNTHEA`: Skip patient generation if true (default: false)
- `SKIP_IMPORT`: Skip data import if true (default: false)

#### Security Groups

Required inbound rules:
- Port 80 (HTTP) - From your IP or 0.0.0.0/0
- Port 22 (SSH) - From your IP only

#### Instance Sizing

- **Development**: t3.small (2 vCPU, 2 GB RAM)
- **Training**: t3.medium (2 vCPU, 4 GB RAM) - Recommended
- **Production**: t3.large (2 vCPU, 8 GB RAM) or larger

## 🔐 Security Considerations

- Always use HTTPS in production (configure with ALB or CloudFront)
- Restrict security groups to known IP ranges
- Use AWS Secrets Manager for sensitive configuration
- Enable CloudWatch logs for monitoring
- Regularly update dependencies

## 📊 Data Management

### Generating Synthetic Data

```bash
cd backend
python scripts/generate_synthea_data.py --patients 100
```

### Importing FHIR Data

```bash
python scripts/optimized_synthea_import.py \
  --input-dir data/synthea_output/fhir \
  --batch-size 20
```

### Adding Reference Ranges

```bash
python scripts/add_reference_ranges.py
```

## 🛠️ Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 80, 3000, 8000 are available
2. **Memory issues**: Increase Docker memory allocation or instance size
3. **Database locked**: Restart the backend service
4. **Missing data**: Re-run the import scripts

### Logs

- Backend logs: `/app/backend/logs/backend.log`
- Nginx logs: `/var/log/nginx/access.log`
- Docker logs: `docker-compose logs -f`

## 📚 API Documentation

Once deployed, access the interactive API documentation at:
- Swagger UI: `http://your-domain/docs`
- ReDoc: `http://your-domain/redoc`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Synthea for synthetic patient data generation
- FHIR community for healthcare data standards
- FastAPI and React communities

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting guide
- Review the API documentation

---

Built with ❤️ for healthcare training and education