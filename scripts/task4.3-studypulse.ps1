<#
  SWE40006 Task 4.3 (Distinction): build and run the StudyPulse stack locally
  (web + redis on their own networks, config from env vars), then push the image.
  The public HTTP/HTTPS part is done on EC2 with scripts/ec2/task4.3-deploy.sh.
  Usage:  .\scripts\task4.3-studypulse.ps1 -DockerHubUser yourname [-Version 1.0.0] [-SkipPush]
#>
param(
    [Parameter(Mandatory)][string]$DockerHubUser,
    [string]$Version = '1.0.0',
    [switch]$SkipPush
)
. "$PSScriptRoot\_common.ps1"
$log = Start-TaskLog -Name 'task4.3-studypulse'
$appDir = Join-Path $RepoRoot 'task4.3-studypulse'
$envFile = Join-Path $appDir '.env'
Push-Location $appDir
try {
    if (-not (Test-Path $envFile)) {
        Copy-Item (Join-Path $appDir '.env.example') $envFile
        Write-Host 'Created .env from .env.example' -ForegroundColor Yellow
    }
    # keep DOCKERHUB_USER / APP_VERSION in .env in sync with the parameters
    (Get-Content $envFile) `
        -replace '^DOCKERHUB_USER=.*', "DOCKERHUB_USER=$DockerHubUser" `
        -replace '^APP_VERSION=.*', "APP_VERSION=$Version" | Set-Content $envFile -Encoding ascii

    Write-Step 'Environment configuration (.env)' $log
    Invoke-Logged $log 'Get-Content .env | Select-String -Pattern "^[A-Z]"'
    Invoke-Logged $log 'docker compose config --services'

    Write-Step 'Build the image (multi-stage, non-root, healthcheck)' $log
    Invoke-Logged $log 'docker compose build --progress=plain web'
    Invoke-Logged $log "docker image ls $DockerHubUser/studypulse"
    Invoke-Logged $log "docker history --format `"table {{.CreatedBy}}\t{{.Size}}`" $DockerHubUser/studypulse:$Version"

    Write-Step 'Start the stack' $log
    Invoke-Logged $log 'docker compose up -d'
    Write-Host 'Waiting 15s for health checks...' -ForegroundColor DarkGray
    Start-Sleep -Seconds 15
    Invoke-Logged $log 'docker compose ps'

    Write-Step 'Networking evidence' $log
    Invoke-Logged $log 'docker network ls --filter "name=studypulse"'
    Invoke-Logged $log 'docker network inspect studypulse_backend --format "backend internal={{.Internal}}  containers={{range .Containers}}{{.Name}} {{end}}"'
    Invoke-Logged $log 'docker network inspect studypulse_frontend --format "frontend internal={{.Internal}}  containers={{range .Containers}}{{.Name}} {{end}}"'
    Invoke-Logged $log 'docker port studypulse-web'
    Invoke-Logged $log 'docker exec studypulse-web id'
    Invoke-Logged $log 'docker exec studypulse-web env | Select-String -Pattern "^(APP_|REDIS_|LOG_)"'
    Invoke-Logged $log 'docker inspect studypulse-web --format "Health={{.State.Health.Status}}"'

    Write-Step 'Exercise the API' $log
    $port = ((Get-Content $envFile | Select-String '^HOST_PORT=') -replace 'HOST_PORT=', '').ToString().Trim()
    if (-not $port) { $port = '8000' }
    $base = "http://localhost:$port"
    Invoke-Logged $log "Invoke-RestMethod $base/health | ConvertTo-Json -Compress"
    Invoke-Logged $log "Invoke-RestMethod -Method Post -Uri $base/api/sessions -ContentType 'application/json' -Body '{`"unit_code`":`"SWE40006`",`"minutes`":90,`"note`":`"Task 4 Dockerfiles`"}' | ConvertTo-Json -Compress"
    Invoke-Logged $log "Invoke-RestMethod -Method Post -Uri $base/api/sessions -ContentType 'application/json' -Body '{`"unit_code`":`"COS40005`",`"minutes`":45,`"note`":`"MailGuard testing`"}' | ConvertTo-Json -Compress"
    Invoke-Logged $log "Invoke-RestMethod $base/api/stats | ConvertTo-Json -Compress"
    Invoke-Logged $log "Invoke-RestMethod $base/api/info | ConvertTo-Json -Compress"

    Write-Step 'Persistence check: recreate the containers, data should still be there' $log
    Invoke-Logged $log 'docker compose down'
    Invoke-Logged $log 'docker compose up -d'
    Start-Sleep -Seconds 12
    Invoke-Logged $log "Invoke-RestMethod $base/api/stats | ConvertTo-Json -Compress"
    Invoke-Logged $log 'docker volume ls --filter "name=studypulse"'
    Invoke-Logged $log 'docker compose logs --tail 15 web'

    if (-not $SkipPush) {
        Write-Step 'Push to Docker Hub' $log
        Invoke-Logged $log 'docker compose push web'
    }
    Write-Host "`nOpen $base in your browser for the screenshot." -ForegroundColor Green
}
finally {
    Pop-Location
}
Write-Host "Log saved to $log" -ForegroundColor Green
