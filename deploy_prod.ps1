
# ==========================================
# PRODUCTION DEPLOYMENT SCRIPT
# ==========================================
# Usage: .\deploy_prod.ps1
# Prerequisites: SSH access configured for the server

# --- CONFIGURATION (UPDATED TO MATCH PRODUCTION) ---
$SERVER_IP = "69.197.145.4"
$SERVER_USER = "administrator"
$PROJECT_DIR = "/nvme0n1-disk/nvme01/ai-document-presentation-v2"
$CONTAINER_NAME = "ai-document-presentation-v2-api-1" # Production container name

# --- SCRIPT ---

Write-Host "[DEPLOY] Starting Production Deployment to $SERVER_IP..." -ForegroundColor Cyan

# 1. Login and Pull Code
Write-Host "[DEPLOY] Connecting to server to pull latest code..." -ForegroundColor Yellow
ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && git pull"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Git pull failed. Please check SSH connection and directory path." -ForegroundColor Red
    exit 1
}

# 2. Restart Docker
Write-Host "[DEPLOY] Restarting Application Container..." -ForegroundColor Yellow
ssh $SERVER_USER@$SERVER_IP "docker restart $CONTAINER_NAME"

# Example 3: If running manual python script (Kill and Restart)
# This is risky via SSH one-liner without nohup/Start-Process, but here's a pattern:
# ssh $SERVER_USER@$SERVER_IP "stop-process -name python -force; Start-Process python -ArgumentList 'pipeline_v2.py' -WorkingDirectory '$PROJECT_DIR' -WindowStyle Hidden"

Write-Host "[DEPLOY] NOTE: Docker restart command is commented out in script. Please uncomment the one matching your setup." -ForegroundColor Gray

Write-Host "[DEPLOY] Deployment Sequence Complete!" -ForegroundColor Green
