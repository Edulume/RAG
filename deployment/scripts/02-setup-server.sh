#!/bin/bash
# Setup RAG server on EC2
# Run this ON the EC2 instance
# Usage: curl -sSL https://raw.githubusercontent.com/Edulume/RAG/main/deployment/scripts/02-setup-server.sh | bash

set -e

echo "🚀 Setting up Edulume RAG Server..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "📦 Installing dependencies..."
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nginx \
    git \
    curl \
    htop

# Clone repo
echo "📥 Cloning RAG repository..."
cd /home/ubuntu
if [ -d "RAG" ]; then
    cd RAG
    git pull
else
    git clone https://github.com/Edulume/RAG.git
    cd RAG
fi

# Setup Python virtual environment
echo "🐍 Setting up Python environment..."
python3.11 -m venv .venv
source .venv/bin/activate

# Install Python packages
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install faiss-cpu sentence-transformers pypdf numpy fastapi uvicorn pydantic

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data indexes/ncert-content

# Setup systemd service
echo "⚙️ Setting up systemd service..."
sudo cp /home/ubuntu/RAG/deployment/config/rag.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rag

# Setup nginx
echo "🌐 Setting up Nginx..."
sudo cp /home/ubuntu/RAG/deployment/config/nginx-rag.conf /etc/nginx/sites-available/rag
sudo ln -sf /etc/nginx/sites-available/rag /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ Server Setup Complete!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo ""
echo "1. Copy data from your local machine:"
echo "   Run on your Mac:"
echo "   ./deployment/scripts/03-copy-data.sh YOUR_EC2_IP"
echo ""
echo "2. Start the service:"
echo "   sudo systemctl start rag"
echo ""
echo "3. Setup DNS and SSL:"
echo "   - Point rag.rahulsain.com to this server's IP"
echo "   - Run: sudo certbot --nginx -d rag.rahulsain.com"
echo ""
