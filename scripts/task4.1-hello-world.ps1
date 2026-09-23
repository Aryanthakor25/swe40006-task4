<#
  SWE40006 Task 4.1 (Pass): check Docker Desktop and run hello-world.
  Docker Desktop needs to be open and signed in first.
  Run from the repo root:  .\scripts\task4.1-hello-world.ps1
#>
. "$PSScriptRoot\_common.ps1"
$log = Start-TaskLog -Name 'task4.1-hello-world'

Write-Step 'WSL 2 backend' $log
Invoke-Logged $log 'wsl --version'

Write-Step 'Docker client + engine' $log
Invoke-Logged $log 'docker --version'
Invoke-Logged $log 'docker version'
Invoke-Logged $log 'docker info --format "Server: {{.ServerVersion}} | OS: {{.OperatingSystem}} | CPUs: {{.NCPU}} | Mem: {{.MemTotal}} | Containers: {{.Containers}} | Images: {{.Images}}"'

Write-Step 'Pull and run hello-world' $log
Invoke-Logged $log 'docker rm -f hello-4-1'
Invoke-Logged $log 'docker pull hello-world'
Invoke-Logged $log 'docker run --name hello-4-1 hello-world'

Write-Step 'Container lifecycle evidence' $log
Invoke-Logged $log 'docker ps -a --filter "name=hello-4-1" --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}"'
Invoke-Logged $log 'docker inspect hello-4-1 --format "ExitCode={{.State.ExitCode}}  StartedAt={{.State.StartedAt}}  FinishedAt={{.State.FinishedAt}}"'
Invoke-Logged $log 'docker images hello-world'

Write-Host "`nLog saved to $log" -ForegroundColor Green
