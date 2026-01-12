
# ==========================================
# PRODUCTION DEPLOYMENT SCRIPT
# ==========================================
# Usage: .\deploy_prod.ps1
# Prerequisites: SSH access configured for the server

# --- CONFIGURATION (EDIT THESE) ---
$SERVER_IP = "YOUR_SERVER_IP"  # e.g., "192.168.1.100" or "myserver.com"
$SERVER_USER = "Administrator" # Windows Server User or Linux User (e.g., "ubuntu")
$PROJECT_DIR = "C:\ai-doc-presentation" # Directory on server where repo is cloned
$CONTAINER_NAME = "ai-doc-app" # Name of your docker container (if applicable)

# --- SCRIPT ---

Write-Host "[DEPLOY] Starting Production Deployment to $SERVER_IP..." -ForegroundColor Cyan

# 1. Login and Pull Code
Write-Host "[DEPLOY] Connecting to server to pull latest code..." -ForegroundColor Yellow
ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && git pull"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Git pull failed. Please check SSH connection and directory path." -ForegroundColor Red
    exit 1
}

# 2. Restart Docker (Optional - Adjust based on your setup)
# Assuming a standard docker restart, or a python script restart
Write-Host "[DEPLOY] Restarting Application..." -ForegroundColor Yellow
# Example 1: If using Docker Compose
# ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && docker-compose restart"

# Example 2: If just restarting a container
# ssh $SERVER_USER@$SERVER_IP "docker restart $CONTAINER_NAME"

# Example 3: If running manual python script (Kill and Restart)
# This is risky via SSH one-liner without nohup/Start-Process, but here's a pattern:
# ssh $SERVER_USER@$SERVER_IP "stop-process -name python -force; Start-Process python -ArgumentList 'pipeline_v2.py' -WorkingDirectory '$PROJECT_DIR' -WindowStyle Hidden"

Write-Host "[DEPLOY] NOTE: Docker restart command is commented out in script. Please uncomment the one matching your setup." -ForegroundColor Gray

Write-Host "[DEPLOY] Deployment Sequence Complete!" -ForegroundColor Green
