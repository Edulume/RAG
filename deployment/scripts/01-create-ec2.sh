#!/bin/bash
# Create EC2 instance for Edulume RAG
# Usage: ./01-create-ec2.sh

set -e

echo "🚀 Creating Edulume RAG EC2 Instance..."

# Configuration
INSTANCE_NAME="edulume-rag"
INSTANCE_TYPE="t3.small"
AMI_ID="ami-0f58b397bc5c1f2e8"  # Ubuntu 24.04 LTS ap-south-1
KEY_NAME="edulume-rag-key"
REGION="ap-south-1"
SECURITY_GROUP_NAME="edulume-rag-sg"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not installed"
    exit 1
fi

# Check credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Run: aws configure"
    exit 1
fi

echo "✅ AWS CLI configured"

# Create key pair if not exists
if ! aws ec2 describe-key-pairs --key-names $KEY_NAME --region $REGION &> /dev/null; then
    echo "📝 Creating key pair: $KEY_NAME"
    aws ec2 create-key-pair \
        --key-name $KEY_NAME \
        --region $REGION \
        --query 'KeyMaterial' \
        --output text > ~/$KEY_NAME.pem
    chmod 400 ~/$KEY_NAME.pem
    echo "✅ Key saved to ~/$KEY_NAME.pem"
else
    echo "✅ Key pair exists: $KEY_NAME"
fi

# Create security group if not exists
SG_ID=$(aws ec2 describe-security-groups \
    --group-names $SECURITY_GROUP_NAME \
    --region $REGION \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "")

if [ -z "$SG_ID" ] || [ "$SG_ID" == "None" ]; then
    echo "📝 Creating security group: $SECURITY_GROUP_NAME"

    SG_ID=$(aws ec2 create-security-group \
        --group-name $SECURITY_GROUP_NAME \
        --description "Edulume RAG API Security Group" \
        --region $REGION \
        --query 'GroupId' \
        --output text)

    # Add rules
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0 --region $REGION
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $REGION
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0 --region $REGION
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 6969 --cidr 0.0.0.0/0 --region $REGION

    echo "✅ Security group created: $SG_ID"
else
    echo "✅ Security group exists: $SG_ID"
fi

# Launch instance
echo "📝 Launching EC2 instance..."

INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --key-name $KEY_NAME \
    --security-group-ids $SG_ID \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3"}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --region $REGION \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "✅ Instance launched: $INSTANCE_ID"

# Wait for instance to be running
echo "⏳ Waiting for instance to start..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $REGION \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ EC2 Instance Created!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Instance ID:  $INSTANCE_ID"
echo "Public IP:    $PUBLIC_IP"
echo "Key file:     ~/$KEY_NAME.pem"
echo ""
echo "Connect with:"
echo "  ssh -i ~/$KEY_NAME.pem ubuntu@$PUBLIC_IP"
echo ""
echo "Next steps:"
echo "  1. Wait 1-2 minutes for instance to fully boot"
echo "  2. Run: ./02-setup-server.sh $PUBLIC_IP"
echo ""
