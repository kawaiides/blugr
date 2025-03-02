#!/bin/bash

# Set environment variables
export GOOGLE_API_KEY="AIzaSyA4z8Tbx0aH49WAVArXch7ZYytfMTCjxwQ"
export AWS_ACCESS_KEY_ID="AKIA6IY36EKFPK62JIL5"
export AWS_SECRET_ACCESS_KEY="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"
export AWS_DEFAULT_REGION="us-east-1"
export AWS_BUCKET_NAME="blooogerai"
export MONGO_DB_KEY="mongodb+srv://shyamthegoodboy:5sBOzYYOqg3V5PAO@blooogerai.spz14.mongodb.net/?retryWrites=true&w=majority&appName=blooogerai"
export GITHUB_TOKEN="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"

SG_NAME="video-processor-sg"
KEY_NAME="video-processor-key"

# Create key pair if it doesn't exist
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME >/dev/null 2>&1; then
    echo "Creating new key pair..."
    aws ec2 create-key-pair \
        --key-name $KEY_NAME \
        --query 'KeyMaterial' \
        --output text > ${KEY_NAME}.pem
    chmod 400 ${KEY_NAME}.pem
else
    echo "Key pair already exists"
fi

# Get latest Amazon Linux 2 AMI ID
echo "Getting latest Amazon Linux 2 AMI ID..."
AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --output text)

echo "Using AMI ID: $AMI_ID"

get_security_group_id() {
    aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=$SG_NAME" \
        --query 'SecurityGroups[0].GroupId' \
        --output text
}

# Check if security group exists
echo "Checking for existing security group..."
SG_ID=$(get_security_group_id)

if [ "$SG_ID" != "None" ] && [ ! -z "$SG_ID" ]; then
    echo "Found existing security group: $SG_ID"

    # Remove existing rules
    echo "Removing existing security group rules..."
    aws ec2 revoke-security-group-ingress \
        --group-id $SG_ID \
        --protocol all \
        --source-group $SG_ID >/dev/null 2>&1 \
        --output text

    aws ec2 revoke-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 22 \
        --cidr 0.0.0.0/0 >/dev/null 2>&1 \
        --output text

    aws ec2 revoke-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0 >/dev/null 2>&1 \
        --output text
else
    # Create new security group
    echo "Creating new security group..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SG_NAME \
        --description "Security group for video processor" \
        --query 'GroupId' \
        --output text)
fi

# Add inbound rules
echo "Adding security group rules..."
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --output text

aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 \
    --output text


cat << 'EOF' > user-data.sh
#!/bin/bash

# Enable logging
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "=== Starting user data script execution at $(date) ==="

# Update system and install required packages
echo "Updating system packages..."
yum update -y
yum install -y git docker

# Start Docker
echo "Starting Docker service..."
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
echo "Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/download/v2.18.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create app directory
echo "Creating app directory..."
mkdir -p /app
cd /app

echo "Creating requirements.txt..."
cat > requirements.txt << 'EOFREQ'
yt-dlp~=2025.2.19
python-multipart>=0.0.7
yt-dlp
scikit-learn~=1.6.1
pymongo==3.11
boto3~=1.37.4
anyio==3.7.1
certifi==2023.7.22
charset-normalizer==3.2.0
click==8.1.7
exceptiongroup==1.1.3
fastapi~=0.111.0
ffmpeg-python==0.2.0
future==0.18.3
h11==0.14.0
idna==3.4
requests==2.31.0
sniffio==1.3.0
urllib3==2.0.5
uvicorn>=0.12.0
pydantic>=2.10.0
annotated-types>=0.6.0
typing_extensions>=4.12.2
google~=3.0.0
botocore~=1.37.4
tqdm~=4.67.1
ytnoti
python-dotenv~=1.0.1
protobuf~=5.29.3
faster-whisper~=1.1.1
EOFREQ


# Clone repository
echo "Cloning repository..."

git clone https://oauth2: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@github.com/kawaiides/blugr.git
cd blugr
echo "pwd..."
pwd
echo "ls..."
ls
# Create .env file
echo "Creating .env file..."

cat << EOFENV > .env
GOOGLE_API_KEY="AIzaSyA4z8Tbx0aH49WAVArXch7ZYytfMTCjxwQ"
AWS_ACCESS_KEY_ID="AKIA6IY36EKFPK62JIL5"
AWS_SECRET_ACCESS_KEY="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"
AWS_DEFAULT_REGION=us-east-1
AWS_BUCKET_NAME="blooogerai"
MONGO_DB_KEY="mongodb+srv://shyamthegoodboy:5sBOzYYOqg3V5PAO@blooogerai.spz14.mongodb.net/?retryWrites=true&w=majority&appName=blooogerai"
GITHUB_TOKEN="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"
EOFENV

# Create data directory
mkdir -p /app/data/youtube
echo "ls..."
ls
# Create Dockerfile
echo "Creating Dockerfile..."
cat > Dockerfile << 'EOFD'
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "server_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]
EOFD

# Create docker-compose.yml first
echo "Creating docker-compose.yml..."
cat << 'EOFDC' > docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY="AIzaSyA4z8Tbx0aH49WAVArXch7ZYytfMTCjxwQ"
      - AWS_ACCESS_KEY_ID="AKIA6IY36EKFPK62JIL5"
      - AWS_SECRET_ACCESS_KEY="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"
      - AWS_DEFAULT_REGION="us-east-1"
      - AWS_BUCKET_NAME="blooogerai"
      - MONGO_DB_KEY="mongodb+srv://shyamthegoodboy:5sBOzYYOqg3V5PAO@blooogerai.spz14.mongodb.net/?retryWrites=true&w=majority&appName=blooogerai"
      - GITHUB_TOKEN="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"
    volumes:
      - ./data:/app/data
    restart: always
EOFDC

# Verify files and configurations
echo "Verifying setup..."
ls -la
echo "Docker Compose version:"
/usr/local/bin/docker-compose --version
echo "Docker version:"
docker --version

# Stop any existing containers
echo "Cleaning up existing containers..."
/usr/local/bin/docker-compose down

# Start the application
echo "Starting the application..."
/usr/local/bin/docker-compose up -d

# Wait for container to start
echo "Waiting for container to initialize..."
sleep 20

# Check container status
echo "Container status:"
docker ps -a

# Check container logs
echo "Container logs:"
docker logs $(docker ps -aq)

# Test application
echo "Testing application..."
curl -v localhost:8000/health

echo "=== User data script completed at $(date) ==="
EOF

# Make sure the script is executable
chmod +x user-data.sh

# Launch EC2 instance
echo "Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type t2.medium \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --user-data file://user-data.sh \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=video-processor}]' \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "Instance ID: $INSTANCE_ID"

# Wait for instance to be running
echo "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Get public IP
echo "Getting public IP..."
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "Deployment complete!"
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "Wait a few minutes for the instance to finish initializing..."

echo "To SSH into the instance:"
echo "ssh -i ${KEY_NAME}.pem ec2-user@${PUBLIC_IP}"

# Wait for instance to initialize
echo "Waiting for instance to initialize..."
sleep 60

# Test SSH connection
echo "Testing SSH connection..."
ssh -o StrictHostKeyChecking=no -i ${KEY_NAME}.pem ec2-user@${PUBLIC_IP} "echo 'SSH connection successful'"

# Monitor application startup
echo "Monitoring application startup..."
for i in {1..10}; do
    echo "Attempt $i: Checking application health..."
    if curl -s "http://${PUBLIC_IP}:8000/health"; then
        echo "Application is running!"
        break
    fi
    echo "Application not ready yet, waiting 30 seconds..."
    sleep 30
done