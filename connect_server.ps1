$SERVER_IP = "69.197.145.4"
$SERVER_USER = "administrator"
Write-Host "Launching SSH session to $SERVER_IP..."
Start-Process powershell -ArgumentList "-NoExit", "-Command ssh $SERVER_USER@$SERVER_IP"
