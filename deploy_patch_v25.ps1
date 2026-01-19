# Deploy V2.5 Surgical Patch (SUDO VERSION)

# 1. Configuration
$SERVER_IP = "69.197.145.4"
$SERVER_USER = "administrator"
$PROJECT_DIR = "/nvme0n1-disk/nvme01/ai-document-presentation-v2"
$CONTAINER_NAME = "ai-document-presentation-v2-api-1"

Write-Host "[DEPLOY] Connecting to $SERVER_IP (Retrying with SUDO)..." -ForegroundColor Cyan

# 2. Construct the compound remote command
#    Using sudo for the copy loop to overcome permission denied errors
$REMOTE_CMD = "cd $PROJECT_DIR && " +
"echo '--- RESETTING LOCAL CHANGES ---' && " +
"git reset --hard && " +
"git clean -fd && " +
"echo '--- GIT PULL ---' && " +
"git pull origin main && " +
"echo '--- PROPAGATING PATCH (sudo) ---' && " +
"count=0; for dir in player/jobs/*/; do sudo cp player/player_v2.js `"`$dir`"`; ((count++)); done; echo `"Patched `$count job folders.`" && " +
"echo '--- RESTARTING DOCKER ---' && " +
"docker restart $CONTAINER_NAME"

# 3. Execute SSH
ssh $SERVER_USER@$SERVER_IP $REMOTE_CMD

if ($LASTEXITCODE -eq 0) {
    Write-Host "[SUCCESS] Server updated and patched successfully." -ForegroundColor Green
}
else {
    Write-Host "[ERROR] SSH Command Failed. Exit Code: $LASTEXITCODE" -ForegroundColor Red
}
