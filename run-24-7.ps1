$ErrorActionPreference = 'SilentlyContinue'

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$python = Join-Path $root '.venv\Scripts\python.exe'
$log = Join-Path $env:TEMP 'vk-status-watchdog.log'

function Write-Watchdog($message) {
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message
    Add-Content -Path $log -Value $line -Encoding UTF8
}

Write-Watchdog 'watchdog online'

while ($true) {
    $running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -like "*$root*main.py*" }

    if (-not $running) {
        Write-Watchdog 'server down - starting'
        Start-Process -FilePath $python -ArgumentList 'main.py' -WorkingDirectory $root -WindowStyle Hidden
        Start-Sleep -Seconds 15
    }

    Start-Sleep -Seconds 30
}
