# SWE40006 Deployment Task 4: Container Deployment with Docker

Aryan Thakor (105061154), SWE40006 Software Deployment and Evolution, Semester 2 2026

Target level: 4.4 High Distinction (4.1 to 4.3 done as prerequisites)

| Level | Folder | What it is | Image |
|---|---|---|---|
| 4.1 Pass | `task4.1-hello-world/` | Docker Desktop (WSL 2), Docker Hub account, `hello-world` check | `hello-world` |
| 4.2 Credit | `task4.2-flask-app/` | Basic Flask app on port 5000, pushed to Docker Hub and pulled/run on EC2 | `<user>/swe40006-flask-app:1.0` |
| 4.3 Distinction | `task4.3-studypulse/` | StudyPulse, a FastAPI study tracker with Redis. Multi-stage non-root image, health check, env var config, two compose networks (backend is internal), named volume, public on EC2 over HTTP and HTTPS (Caddy) | `<user>/studypulse:1.0.0` |
| 4.4 High Distinction | `task4.4-csv-profiler/` | csvprofiler, a CLI that profiles CSV files. Bind mounts for input/output, named volume for the SQLite run history, exit codes, watcher that shuts down cleanly on SIGTERM | `<user>/csvprofiler:1.0.0` |

## Folder layout

```
task4.1-hello-world/      commands only
task4.2-flask-app/        app.py, Dockerfile, requirements.txt, .dockerignore
task4.3-studypulse/       app/, tests/, Dockerfile, docker-compose.yml, .env.example, caddy/Caddyfile
task4.4-csv-profiler/     csvprofiler/, tests/, Dockerfile, docker-compose.yml, data/input, samples/
scripts/                  PowerShell script for each level (prints and logs every command)
scripts/ec2/              user-data.sh, task4.2-pull-run.sh, task4.3-deploy.sh
docs/diagrams/            draw.io diagrams used in the report
logs/                     output logs from the scripts
.github/workflows/ci.yml  tests, hadolint and image builds
```

## Running it on Windows (Docker Desktop)

Clone it into a normal Windows folder like Documents (not inside WSL), then from the repo root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass    # lets the scripts run in this window only
docker login                                 # Docker Hub username + access token

.\scripts\task4.1-hello-world.ps1
.\scripts\task4.2-flask-app.ps1    -DockerHubUser <you>     # http://localhost:8080
.\scripts\task4.3-studypulse.ps1   -DockerHubUser <you>     # http://localhost:8000
.\scripts\task4.4-csv-profiler.ps1 -DockerHubUser <you>     # reports go to task4.4-csv-profiler\data\output
```

Every script prints each command before running it and saves the output to `logs\<task>.log`.

## EC2 (secondary host and public deployment)

1. Launch a t3.micro with Amazon Linux 2023 in ap-southeast-2 with a public IP. Security group inbound: 80, 443 and 8080 from 0.0.0.0/0. Port 22 isn't needed if you use Session Manager.
2. Paste `scripts/ec2/user-data.sh` into Advanced details, User data. It installs Docker, Compose v2 and git.
3. Connect with Session Manager, switch user with `sudo su - ec2-user`, then run:

```bash
git clone https://github.com/Aryanthakor25/swe40006-task4.git && cd swe40006-task4
bash scripts/ec2/task4.2-pull-run.sh <you> 1.0 8080     # 4.2: http://<public-ip>:8080
bash scripts/ec2/task4.3-deploy.sh   <you> --https       # 4.3: https://<ip-with-dashes>.sslip.io
```

Leave out `--https` for plain HTTP on port 80. Keep the instance running until the task is marked, then terminate it.

## Tests (no Docker needed)

```bash
cd task4.3-studypulse && pip install -r requirements-dev.txt && pytest -q
cd task4.4-csv-profiler && pip install pytest && pytest -q
```

## Manual commands

```powershell
# 4.3 stack
cd task4.3-studypulse; Copy-Item .env.example .env    # then set DOCKERHUB_USER
docker compose up -d --build; docker compose ps; docker compose logs -f web
docker compose down         # keeps the redis-data volume
docker compose down -v      # deletes it as well

# 4.4 CLI
cd task4.4-csv-profiler
docker volume create csvprofiler-history
docker compose run --rm profiler profile-all
docker compose run --rm profiler history
docker compose up -d watcher; docker compose logs -f watcher; docker compose stop watcher
```

| csvprofiler exit code | Meaning |
|---|---|
| 0 | success |
| 2 | bad arguments |
| 3 | input file or folder not found |
| 4 | no CSV files, or a file couldn't be parsed |
| 5 | output folder not writable (on Linux: `sudo chown -R 10001:10001 data/output`) |
