<#
  SWE40006 Task 4.2 (Credit): build, run, test and push the Flask image.
  Run `docker login` once before this (use a Docker Hub access token as the password).
  Usage:  .\scripts\task4.2-flask-app.ps1 -DockerHubUser yourname [-Tag 1.0] [-HostPort 8080] [-SkipPush]
#>
param(
    [Parameter(Mandatory)][string]$DockerHubUser,
    [string]$Tag = '1.0',
    [int]$HostPort = 8080,
    [switch]$SkipPush
)
. "$PSScriptRoot\_common.ps1"
$log = Start-TaskLog -Name 'task4.2-flask-app'
$image = "$DockerHubUser/swe40006-flask-app:$Tag"
$appDir = Join-Path $RepoRoot 'task4.2-flask-app'

Write-Step 'Build the image from the custom Dockerfile' $log
Invoke-Logged $log "docker build --progress=plain -t $image -t $DockerHubUser/swe40006-flask-app:latest `"$appDir`""
Invoke-Logged $log "docker image ls $DockerHubUser/swe40006-flask-app"

Write-Step "Run locally: host port $HostPort to container port 5000" $log
Invoke-Logged $log 'docker rm -f flask-app-4-2'
Invoke-Logged $log "docker run -d --name flask-app-4-2 -p ${HostPort}:5000 $image"
Start-Sleep -Seconds 3
Invoke-Logged $log 'docker ps --filter "name=flask-app-4-2" --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"'
Invoke-Logged $log "docker port flask-app-4-2"
Invoke-Logged $log "Invoke-RestMethod http://localhost:$HostPort/api/info | ConvertTo-Json"
Invoke-Logged $log "(Invoke-WebRequest http://localhost:$HostPort/ -UseBasicParsing).StatusCode"
Invoke-Logged $log 'docker logs flask-app-4-2'

if (-not $SkipPush) {
    Write-Step 'Push to Docker Hub' $log
    Invoke-Logged $log "docker push $image"
    Invoke-Logged $log "docker push $DockerHubUser/swe40006-flask-app:latest"
    Write-Host "`nCheck https://hub.docker.com/r/$DockerHubUser/swe40006-flask-app/tags for the screenshot." -ForegroundColor Green
}

Write-Host "Open http://localhost:$HostPort in your browser for the screenshot." -ForegroundColor Green
Write-Host "Log saved to $log" -ForegroundColor Green
