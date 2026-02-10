
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

# 1. Login and Pull Code (Force Clean)
Write-Host "[DEPLOY] Connecting to server to force clean and pull latest code..." -ForegroundColor Yellow
# FIX: Added 'git reset --hard' to discard local changes (like logs) that block the pull
ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_DIR && git reset --hard HEAD && git pull"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Git pull failed. Please check SSH connection and directory path." -ForegroundColor Red
    exit 1
}

# 2. Restart Docker
Write-Host "[DEPLOY] Restarting Application Container ($CONTAINER_NAME)..." -ForegroundColor Yellow
ssh $SERVER_USER@$SERVER_IP "docker restart $CONTAINER_NAME"

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker restart command failed." -ForegroundColor Red
    exit 1
}

# 3. Verify Restart
Write-Host "[DEPLOY] Verifying container status..." -ForegroundColor Yellow
Start-Sleep -Seconds 2 # Give it a moment to initialize

$STATUS_JSON = ssh $SERVER_USER@$SERVER_IP "docker inspect $CONTAINER_NAME --format '{{json .State}}'"
if ($LASTEXITCODE -eq 0 -and $STATUS_JSON) {
    # Check if Running
    if ($STATUS_JSON -match '"Running":true') {
        $STARTED_AT = ssh $SERVER_USER@$SERVER_IP "docker inspect $CONTAINER_NAME --format '{{.State.StartedAt}}'"
        Write-Host "[SUCCESS] Container is RUNNING. Started at: $STARTED_AT" -ForegroundColor Green
    } else {
        Write-Host "[CRITICAL] Container is NOT running after restart!" -ForegroundColor Red
        Write-Host "[DEBUG] Fetching last 20 lines of logs:" -ForegroundColor Gray
        ssh $SERVER_USER@$SERVER_IP "docker logs --tail 20 $CONTAINER_NAME"
        exit 1
    }
} else {
    Write-Host "[WARNING] Could not verify container status via docker inspect." -ForegroundColor Yellow
}

Write-Host "[DEPLOY] Deployment Sequence Complete!" -ForegroundColor Green
