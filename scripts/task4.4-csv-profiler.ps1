<#
  SWE40006 Task 4.4 (High Distinction): containerised CLI tool.
  Covers the build, bind mounts (input read-only, output read-write), the named
  volume for run history, exit codes, the container lifecycle, and the watcher
  shutting down cleanly on SIGTERM.
  Usage:  .\scripts\task4.4-csv-profiler.ps1 -DockerHubUser yourname [-Version 1.0.0] [-SkipPush]
#>
param(
    [Parameter(Mandatory)][string]$DockerHubUser,
    [string]$Version = '1.0.0',
    [switch]$SkipPush
)
. "$PSScriptRoot\_common.ps1"
$log = Start-TaskLog -Name 'task4.4-csv-profiler'
$appDir = Join-Path $RepoRoot 'task4.4-csv-profiler'
$image = "$DockerHubUser/csvprofiler:$Version"
$env:DOCKERHUB_USER = $DockerHubUser
$env:APP_VERSION = $Version
Push-Location $appDir
try {
    $in = [IO.Path]::Combine($appDir, 'data', 'input')
    $out = [IO.Path]::Combine($appDir, 'data', 'output')
    $mounts = "-v `"${in}:/data/input:ro`" -v `"${out}:/data/output`" -v csvprofiler-history:/var/lib/csvprofiler"

    # clean up from any earlier run
    Remove-Item (Join-Path $in 'unit_results.csv') -ErrorAction SilentlyContinue
    Get-ChildItem $out -Filter '*.profile.*' -ErrorAction SilentlyContinue | Remove-Item
    docker rm -f csvprofiler-run1 csvprofiler-watcher 2>$null | Out-Null
    docker volume rm csvprofiler-history 2>$null | Out-Null

    Write-Step 'Build the image' $log
    Invoke-Logged $log "docker build --progress=plain --build-arg APP_VERSION=$Version -t $image ."
    Invoke-Logged $log "docker image ls $DockerHubUser/csvprofiler"
    Invoke-Logged $log "docker image inspect $image --format `"User={{.Config.User}}  Entrypoint={{json .Config.Entrypoint}}  Cmd={{json .Config.Cmd}}  Volumes={{json .Config.Volumes}}`""

    Write-Step 'Default command (--help)' $log
    Invoke-Logged $log "docker run --rm $image"
    Invoke-Logged $log "docker run --rm $image --version"

    Write-Step 'Named volume for persistent run history' $log
    Invoke-Logged $log 'docker volume create csvprofiler-history'
    Invoke-Logged $log 'docker volume inspect csvprofiler-history'

    Write-Step 'Batch run lifecycle: create, start, exit, remove' $log
    Invoke-Logged $log "docker create --name csvprofiler-run1 --network none $mounts $image profile-all"
    Invoke-Logged $log 'docker ps -a --filter "name=csvprofiler-run1" --format "table {{.Names}}\t{{.Status}}"'
    Invoke-Logged $log 'docker start --attach csvprofiler-run1'
    Invoke-Logged $log 'docker ps -a --filter "name=csvprofiler-run1" --format "table {{.Names}}\t{{.Status}}"'
    Invoke-Logged $log 'docker inspect csvprofiler-run1 --format "ExitCode={{.State.ExitCode}}  StartedAt={{.State.StartedAt}}  FinishedAt={{.State.FinishedAt}}"'
    Invoke-Logged $log 'docker logs --timestamps csvprofiler-run1'
    Invoke-Logged $log 'docker rm csvprofiler-run1'
    Invoke-Logged $log "Get-ChildItem `"$out`" -Filter *.profile.* | ForEach-Object { '{0,-34} {1,6} bytes' -f `$_.Name, `$_.Length }"

    Write-Step 'Error handling: missing file should give exit code 3' $log
    Invoke-Logged $log "docker run --rm --network none $mounts $image profile does_not_exist.csv"

    Write-Step 'History from a new container (same volume)' $log
    Invoke-Logged $log "docker run --rm -v csvprofiler-history:/var/lib/csvprofiler $image history"

    Write-Step 'Watcher with docker compose, then stop it (SIGTERM)' $log
    Invoke-Logged $log 'docker compose up -d watcher'
    Start-Sleep -Seconds 4
    Invoke-Logged $log 'docker compose ps watcher'
    Invoke-Logged $log "Copy-Item samples/unit_results.csv data/input/ -PassThru | ForEach-Object Name"
    Write-Host 'Waiting 8s for the watcher to pick up the new file...' -ForegroundColor DarkGray
    Start-Sleep -Seconds 8
    Invoke-Logged $log 'docker compose stop watcher'
    Invoke-Logged $log 'docker compose logs --timestamps watcher'
    Invoke-Logged $log 'docker inspect csvprofiler-watcher --format "ExitCode={{.State.ExitCode}}  Status={{.State.Status}}"'
    Invoke-Logged $log 'docker compose run --rm profiler history'
    Invoke-Logged $log 'docker compose rm -f watcher'

    if (-not $SkipPush) {
        Write-Step 'Push to Docker Hub' $log
        Invoke-Logged $log "docker push $image"
    }
    Write-Host "`nReports are in $out" -ForegroundColor Green
}
finally {
    Pop-Location
}
Write-Host "Log saved to $log" -ForegroundColor Green
