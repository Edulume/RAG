# RAG Deployment Guide

Deploy Edulume RAG API to AWS EC2.

**Target:** `rag.rahulsain.com`

---

## Infrastructure

| Resource | Spec | Cost |
|----------|------|------|
| EC2 | t3.small (2GB RAM) | ~$15/month |
| Storage | 20GB gp3 | ~$2/month |
| **Total** | | **~$17/month** |

---

## Prerequisites

- AWS Account
- AWS CLI configured (`aws configure`)
- Domain DNS access (for rag.rahulsain.com)

---

## Deployment Steps

### Step 1: Create EC2 Instance

**Option A: AWS Console (Manual)**

1. Go to https://console.aws.amazon.com/ec2
2. Click "Launch Instance"
3. Settings:
   - Name: `edulume-rag`
   - OS: Ubuntu 24.04 LTS
   - Instance type: `t3.small`
   - Key pair: Create new → `edulume-rag-key` (download .pem)
   - Security group: Allow SSH (22), HTTP (80), HTTPS (443), Custom TCP (6969)
   - Storage: 20 GB gp3
4. Launch and note the Public IP

**Option B: AWS CLI (Automated)**

```bash
# Run the setup script
./deployment/scripts/01-create-ec2.sh
```

---

### Step 2: Connect to EC2

```bash
# Make key usable
chmod 400 ~/Downloads/edulume-rag-key.pem

# Connect
ssh -i ~/Downloads/edulume-rag-key.pem ubuntu@YOUR_EC2_IP
```

---

### Step 3: Setup Server

On EC2, run:

```bash
# Download and run setup script
curl -sSL https://raw.githubusercontent.com/Edulume/RAG/main/deployment/scripts/02-setup-server.sh | bash
```

Or manually:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip nginx git

# Clone repo
cd /home/ubuntu
git clone https://github.com/Edulume/RAG.git
cd RAG

# Setup Python
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create data directories
mkdir -p data indexes/ncert-content
```

---

### Step 4: Copy Data from Local

From your **local machine** (Mac):

```bash
EC2_IP="YOUR_EC2_IP"
KEY="~/Downloads/edulume-rag-key.pem"

# Copy FAISS index
scp -i $KEY -r /Users/rahulsain/Documents/kzr/Edulume/RAG/indexes/ncert-content/* \
  ubuntu@$EC2_IP:/home/ubuntu/RAG/indexes/ncert-content/

# Copy question bank
scp -i $KEY /Users/rahulsain/Documents/kzr/Edulume/RAG/data/question-bank.csv \
  ubuntu@$EC2_IP:/home/ubuntu/RAG/data/
```

---

### Step 5: Setup Systemd Service

On EC2:

```bash
# Copy service file
sudo cp /home/ubuntu/RAG/deployment/config/rag.service /etc/systemd/system/

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable rag
sudo systemctl start rag

# Check status
sudo systemctl status rag
```

---

### Step 6: Setup Nginx

```bash
# Copy nginx config
sudo cp /home/ubuntu/RAG/deployment/config/nginx-rag.conf /etc/nginx/sites-available/rag
sudo ln -sf /etc/nginx/sites-available/rag /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

---

### Step 7: Setup DNS

Add DNS record for your domain:

```
Type: A
Name: rag
Value: YOUR_EC2_IP
TTL: 300
```

Wait for DNS propagation (~5 minutes).

---

### Step 8: Setup SSL

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d rag.rahulsain.com
```

---

### Step 9: Verify

```bash
# Test endpoints
curl https://rag.rahulsain.com/health
curl https://rag.rahulsain.com/stats
```

---

## Management Commands

| Action | Command |
|--------|---------|
| Check status | `sudo systemctl status rag` |
| View logs | `sudo journalctl -u rag -f` |
| Restart | `sudo systemctl restart rag` |
| Stop | `sudo systemctl stop rag` |
| Start | `sudo systemctl start rag` |

---

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u rag -n 50

# Test manually
cd /home/ubuntu/RAG
source .venv/bin/activate
python api/server.py
```

### Out of memory
```bash
# Check memory
free -h

# If needed, upgrade to t3.medium (4GB)
```

### Index not found
```bash
# Re-copy from local or re-index
python pipelines/index-ncert/index.py --source data/ncert-books/
```

---

## Update Deployment

```bash
# SSH to server
ssh -i ~/Downloads/edulume-rag-key.pem ubuntu@YOUR_EC2_IP

# Pull latest code
cd /home/ubuntu/RAG
git pull

# Restart service
sudo systemctl restart rag
```

---

## Files in This Directory

```
deployment/
├── README.md              # This file
├── scripts/
│   ├── 01-create-ec2.sh   # Create EC2 instance (AWS CLI)
│   ├── 02-setup-server.sh # Setup server dependencies
│   └── 03-copy-data.sh    # Copy data from local
└── config/
    ├── rag.service        # Systemd service file
    └── nginx-rag.conf     # Nginx configuration
```
