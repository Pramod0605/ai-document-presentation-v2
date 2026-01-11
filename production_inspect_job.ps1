param (
    [Parameter(Mandatory = $true)]
    [string]$JobId,
    
    [Parameter(Mandatory = $false)]
    [string]$Path = ""
)

$ServerIP = "69.197.145.4"
$BaseDir = "/nvme0n1-disk/nvme01/ai-document-presentation-v2/player/jobs/$JobId"

if ([string]::IsNullOrWhiteSpace($Path)) {
    Write-Host "Listing files for Job: $JobId" -ForegroundColor Cyan
    ssh administrator@$ServerIP "sudo bash -c 'ls -F $BaseDir'"
}
else {
    Write-Host "Reading file: $Path for Job: $JobId" -ForegroundColor Cyan
    ssh administrator@$ServerIP "sudo bash -c 'cat $BaseDir/$Path'"
}
