#!/bin/bash
# Copy RAG data to EC2 server
# Run this from your LOCAL machine (Mac)
# Usage: ./03-copy-data.sh EC2_IP

set -e

if [ -z "$1" ]; then
    echo "Usage: ./03-copy-data.sh EC2_IP"
    echo "Example: ./03-copy-data.sh 54.123.45.67"
    exit 1
fi

EC2_IP=$1
KEY="${KEY_PATH:-$HOME/edulume-rag-key.pem}"
RAG_DIR="/Users/rahulsain/Documents/kzr/Edulume/RAG"

echo "🚀 Copying RAG data to EC2..."
echo "   EC2 IP: $EC2_IP"
echo "   Key: $KEY"
echo ""

# Check key exists
if [ ! -f "$KEY" ]; then
    echo "❌ Key file not found: $KEY"
    echo "   Set KEY_PATH environment variable or place key at $KEY"
    exit 1
fi

# Check local data exists
if [ ! -d "$RAG_DIR/indexes/ncert-content" ]; then
    echo "❌ Index not found at $RAG_DIR/indexes/ncert-content"
    echo "   Run indexing first: python pipelines/index-ncert/index.py"
    exit 1
fi

# Copy FAISS index
echo "📤 Copying FAISS index..."
scp -i "$KEY" -r \
    "$RAG_DIR/indexes/ncert-content/"* \
    ubuntu@$EC2_IP:/home/ubuntu/RAG/indexes/ncert-content/

# Copy question bank
echo "📤 Copying question bank..."
scp -i "$KEY" \
    "$RAG_DIR/data/question-bank.csv" \
    ubuntu@$EC2_IP:/home/ubuntu/RAG/data/

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ Data Copied Successfully!"
echo "════════════════════════════════════════════════════════"
echo ""
echo "Next steps on EC2:"
echo ""
echo "1. SSH to server:"
echo "   ssh -i $KEY ubuntu@$EC2_IP"
echo ""
echo "2. Start the RAG service:"
echo "   sudo systemctl start rag"
echo ""
echo "3. Test:"
echo "   curl http://$EC2_IP:6969/health"
echo ""
