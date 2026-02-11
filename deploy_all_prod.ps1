
# ==========================================
# MULTI-SERVER PRODUCTION DEPLOYMENT SCRIPT
# ==========================================
# Usage: .\deploy_all_prod.ps1
# Prerequisites: SSH access configured for the servers (SSH Keys recommended to avoid password prompts)

# --- CONFIGURATION ---
$SERVERS = @(
    @{ IP = "38.247.187.26";  Role = "Science";        User = "administrator"; Dir = "/nvme0n1-disk/nvme01/ai-document-presentation-v2" },
    @{ IP = "38.247.185.28";  Role = "Science";        User = "administrator"; Dir = "/nvme0n1-disk/nvme01/ai-document-presentation-v2" },
    @{ IP = "173.208.218.77"; Role = "Social Science"; User = "administrator"; Dir = "/nvme0n1-disk/nvme01/ai-document-presentation-v2" },
    @{ IP = "63.141.249.82";  Role = "Social Science"; User = "administrator"; Dir = "/nvme0n1-disk/nvme01/ai-document-presentation-v2" },
    @{ IP = "69.197.145.4";   Role = "Math (Main)";    User = "administrator"; Dir = "/nvme0n1-disk/nvme01/ai-document-presentation-v2" },
    @{ IP = "38.247.187.18";  Role = "Math";           User = "administrator"; Dir = "/nvme0n1-disk/nvme01/ai-document-presentation-v2" }
)

$CONTAINER_NAME = "ai-document-presentation-v2-api-1"

# --- SCRIPT ---

foreach ($server in $SERVERS) {
    $IP = $server.IP
    $USER = $server.User
    $ROLE = $server.Role
    $DIR = $server.Dir
    
    Write-Host "`n========================================================" -ForegroundColor Cyan
    Write-Host "[DEPLOY] Target: $IP ($ROLE)" -ForegroundColor Cyan
    Write-Host "========================================================"

    # 1. Pull Code
    Write-Host "[Step 1] Pulling latest code..." -ForegroundColor Yellow
    # Reset hard to ensure clean pull
    ssh -o Start_Process=No -o BatchMode=no "$USER@$IP" "cd $DIR && git reset --hard HEAD && git pull"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Git pull failed on $IP. Skipping to next server." -ForegroundColor Red
        continue
    }

    # 2. Restart Docker
    Write-Host "[Step 2] Restarting Container ($CONTAINER_NAME)..." -ForegroundColor Yellow
    ssh -o Start_Process=No -o BatchMode=no "$USER@$IP" "docker restart $CONTAINER_NAME"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Docker restart failed on $IP." -ForegroundColor Red
        continue
    }

    # 3. Wait 10 Seconds
    Write-Host "[Step 3] Waiting 10 seconds for container to initialize..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

    # 4. Check Status
    Write-Host "[Step 4] Checking Docker Status..." -ForegroundColor Yellow
    $STATUS_CMD = "docker inspect $CONTAINER_NAME --format '{{.State.Status}}'"
    $STATUS = ssh -o Start_Process=No -o BatchMode=no "$USER@$IP" $STATUS_CMD
    
    if ($STATUS -match "running") {
        Write-Host "[SUCCESS] $IP ($ROLE) is RUNNING." -ForegroundColor Green
    } else {
        Write-Host "[WARNING] $IP ($ROLE) status is '$STATUS'. Check logs manually." -ForegroundColor Red
        ssh -o Start_Process=No -o BatchMode=no "$USER@$IP" "docker logs --tail 10 $CONTAINER_NAME"
    }

    Write-Host "[DONE] Finished deployment for $IP" -ForegroundColor Gray
}

Write-Host "`nAll servers processed." -ForegroundColor Green
