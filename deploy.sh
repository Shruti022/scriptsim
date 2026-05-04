#!/bin/bash
set -e

VM_NAME="scriptsim-demo"
ZONE="us-central1-a"

echo "=== 1/5: Pushing local changes to GitHub ==="
git push origin master || echo "Assuming already pushed or continuing anyway..."

echo "=== 2/5: Provisioning Google Compute Engine VM ($VM_NAME) ==="
# Using a standard Ubuntu image
gcloud compute instances create $VM_NAME \
    --machine-type=e2-standard-4 \
    --zone=$ZONE \
    --tags=http-server,scriptsim-ports \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=50GB \
    --scopes=https://www.googleapis.com/auth/cloud-platform

echo "Waiting for VM to boot up..."
sleep 20

echo "=== 3/5: Opening Firewall Ports (3000, 8000, 5000, 5001, 5002) ==="
gcloud compute firewall-rules create scriptsim-allow-ports \
    --action=ALLOW \
    --rules=tcp:3000,tcp:8000,tcp:5000,tcp:5001,tcp:5002 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=scriptsim-ports || echo "Firewall rule likely already exists."

echo "=== 4/5: Transferring files (including .env and GCP credentials) to the VM ==="
# Compress the directory excluding node_modules and venv for faster transfer
echo "Compressing files..."
tar --exclude='node_modules' --exclude='venv' --exclude='.git' --exclude='.next' -czf scriptsim-deploy.tar.gz .

echo "Uploading files via SCP..."
gcloud compute scp scriptsim-deploy.tar.gz $VM_NAME:~ --zone=$ZONE
# Also securely copy the application default credentials so the backend can use Vertex AI
gcloud compute scp ~/.config/gcloud/application_default_credentials.json $VM_NAME:~ --zone=$ZONE || echo "Warning: Could not copy ADC. Backend may fail Vertex AI calls if service account lacks permissions."

echo "=== 5/5: Installing Docker and Starting Services on the VM ==="
gcloud compute ssh $VM_NAME --zone=$ZONE --command="
    # Extract files
    mkdir -p ~/scriptsim
    tar -xzf scriptsim-deploy.tar.gz -C ~/scriptsim
    
    # Place GCP credentials where docker-compose expects them (~/.config/gcloud/)
    mkdir -p ~/.config/gcloud
    mv ~/application_default_credentials.json ~/.config/gcloud/ || true

    # Install Docker and Docker Compose
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(. /etc/os-release && echo \"\$VERSION_CODENAME\") stable\" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add user to docker group to run without sudo
    sudo usermod -aG docker \$USER

    # Start services
    cd ~/scriptsim
    sudo docker compose up -d --build
"

echo ""
echo "=========================================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo ""
EXTERNAL_IP=$(gcloud compute instances describe $VM_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
echo "Your ScriptSim Dashboard is live at:"
echo "👉 http://$EXTERNAL_IP:3000"
echo "=========================================================="
