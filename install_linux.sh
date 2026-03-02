#!/bin/bash
# NSFW Guard Pro - Linux Deployment Script (CPU/GPU)

echo "------------------------------------------------"
echo "NSFW Guard Pro - Linux Installer"
echo "------------------------------------------------"

# 1. Install System Dependencies
echo "[1/5] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip libgl1 libglib2.0-0

# 2. Setup Virtual Environment
echo "[2/5] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 3. Detect Hardware & Install Python Dependencies
if command -v nvidia-smi &> /dev/null; then
    echo ">> NVIDIA GPU Detected! Installing GPU version..."
    pip install -r requirements-gpu.txt
else
    echo ">> No GPU detected. Installing CPU-optimized version..."
    pip install -r requirements.txt
fi

# 4. Setup Environment Variables
if [ -z "$NSFW_API_KEY" ]; then
    DEFAULT_KEY="NSFW_PRO_$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)"
    echo "[4/5] Setting up API Key..."
    echo "export NSFW_API_KEY=$DEFAULT_KEY" >> ~/.bashrc
    export NSFW_API_KEY=$DEFAULT_KEY
    echo ">> Your API Key is: $NSFW_API_KEY (Saved to ~/.bashrc)"
fi

# 5. Create Systemd Service (Optional but recommended)
echo "[5/5] Creating background service (nsfw_guard.service)..."
cat <<EOF | sudo tee /etc/systemd/system/nsfw_guard.service
[Unit]
Description=NSFW Guard Pro API
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
Environment="NSFW_API_KEY=$NSFW_API_KEY"
Environment="PYTHONPATH=$(pwd)"
ExecStart=$(pwd)/venv/bin/python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
echo ">> Installation complete!"
echo ">> To start service: sudo systemctl start nsfw_guard"
echo ">> To enable on boot: sudo systemctl enable nsfw_guard"
echo ">> To view logs: journalctl -u nsfw_guard -f"
echo "------------------------------------------------"
