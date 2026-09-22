$ErrorActionPreference = 'Stop'
$start = Get-Date
$timeout = 300  # 5 minutes max
$script = 'c:\Users\K1 Center\Desktop\vibe-print\test_slice_run.py'
$outFile = 'c:\Users\K1 Center\Desktop\vibe-print\slice_result_raw.json'
$errFile = 'c:\Users\K1 Center\Desktop\vibe-print\slice_err.txt'

# Remove old result
if (Test-Path $outFile) { Remove-Item $outFile -Force }

# Start process in background
$p = Start-Process -FilePath python -ArgumentList $script -NoNewWindow -PassThru -RedirectStandardError $errFile

# Poll
while (-not (Test-Path $outFile) -and $p.HasExited -eq $false) {
    $elapsed = (Get-Date) - $start
    if ($elapsed.TotalSeconds -gt $timeout) {
        $p.Kill()
        Write-Host "TIMEOUT after $timeout seconds"
        exit 1
    }
    Start-Sleep -Seconds 5
    Write-Host "waiting... ($([int]$elapsed.TotalSeconds)s)" -ForegroundColor DarkGray
}

if ($p.HasExited) {
    Write-Host "Process exited with code $($p.ExitCode)"
    if (Test-Path $errFile) {
        Write-Host "STDERR:"
        Get-Content $errFile
    }
}

if (Test-Path $outFile) {
    Write-Host "RESULT_FILE_FOUND"
    Get-Content $outFile
} else {
    Write-Host "RESULT_FILE_NOT_FOUND"
}