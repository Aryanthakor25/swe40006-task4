# helpers used by the task scripts
# each command is printed before it runs (good for screenshots) and saved
# with its output to logs\<task>.log

$ErrorActionPreference = 'Continue'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $RepoRoot 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Start-TaskLog {
    param([Parameter(Mandatory)][string]$Name)
    $path = Join-Path $LogDir "$Name.log"
    $header = @(
        "==================================================================",
        " SWE40006 Deployment Task 4: $Name",
        " Student : Aryan Thakor (105061154)",
        " Host    : $env:COMPUTERNAME",
        " Date    : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')",
        "=================================================================="
    )
    Set-Content -Path $path -Value $header -Encoding utf8
    $header | ForEach-Object { Write-Host $_ -ForegroundColor DarkGray }
    return $path
}

function Invoke-Logged {
    param(
        [Parameter(Mandatory)][string]$Log,
        [Parameter(Mandatory)][string]$Command
    )
    $prompt = "PS> $Command"
    Write-Host ""
    Write-Host $prompt -ForegroundColor Cyan
    Add-Content -Path $Log -Value @("", $prompt) -Encoding utf8

    # 2>&1 so docker build progress and warnings (stderr) also go in the log
    $global:LASTEXITCODE = 0
    $output = Invoke-Expression "$Command 2>&1" | ForEach-Object { "$_" }
    $code = $LASTEXITCODE

    $output | ForEach-Object { Write-Host $_ }
    if ($output) { Add-Content -Path $Log -Value $output -Encoding utf8 }
    if ($null -ne $code -and $code -ne 0) {
        $msg = "[exit code $code]"
        Write-Host $msg -ForegroundColor Yellow
        Add-Content -Path $Log -Value $msg -Encoding utf8
    }
}

function Write-Step {
    param([string]$Text, [string]$Log)
    $line = "---- $Text ----"
    Write-Host ""
    Write-Host $line -ForegroundColor Green
    if ($Log) { Add-Content -Path $Log -Value @("", $line) -Encoding utf8 }
}
